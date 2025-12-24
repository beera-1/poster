#!/usr/bin/env python3
from aiohttp import ClientSession
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from os import path as ospath, getcwd
from re import search as re_search
from shlex import split as ssplit

from pyrogram.handlers import MessageHandler
from pyrogram.filters import command, create
from pyrogram.enums import ChatType

# ✅ CORRECT IMPORTS
from poster import bot, LOGGER
from bot import user_data, OWNER_ID
from bot.helper.telegram_helper.message_utils import chat_info


# =================================================
# CUSTOM FILTERS (EMBEDDED – FIXED)
# =================================================
class CustomFilters:

    async def owner_filter(self, _, message):
        user = message.from_user or message.sender_chat
        return user.id == OWNER_ID

    owner = create(owner_filter)

    async def authorized_user(self, _, message):
        user = message.from_user or message.sender_chat
        uid = user.id

        if uid == OWNER_ID or (
            uid in user_data and (
                user_data[uid].get("is_auth", False)
                or user_data[uid].get("is_sudo", False)
            )
        ):
            return True

        chat_id = message.chat.id
        if chat_id in user_data and user_data[chat_id].get("is_auth", False):
            topic_ids = user_data[chat_id].get("topic_ids", [])
            if not topic_ids:
                return True

            r = message.reply_to_message
            if r:
                if r.id in topic_ids:
                    return True
                if r.reply_to_top_message_id in topic_ids:
                    return True
                if r.reply_to_message_id in topic_ids:
                    return True

        return False

    authorized = create(authorized_user)

    async def authorized_usetting(self, _, message):
        uid = (message.from_user or message.sender_chat).id
        chat_id = message.chat.id

        if (
            uid == OWNER_ID
            or (uid in user_data and (user_data[uid].get("is_auth") or user_data[uid].get("is_sudo")))
            or (chat_id in user_data and user_data[chat_id].get("is_auth"))
        ):
            return True

        if message.chat.type == ChatType.PRIVATE:
            for cid in user_data:
                if user_data[cid].get("is_auth") and str(cid).startswith("-100"):
                    try:
                        if await (await chat_info(str(cid))).get_member(uid):
                            return True
                    except:
                        continue
        return False

    authorized_uset = create(authorized_usetting)

    async def sudo_user(self, _, message):
        user = message.from_user or message.sender_chat
        return user.id == OWNER_ID or (
            user.id in user_data and user_data[user.id].get("is_sudo")
        )

    sudo = create(sudo_user)

    async def blacklist_user(self, _, message):
        user = message.from_user or message.sender_chat
        return user.id != OWNER_ID and (
            user.id in user_data and user_data[user.id].get("is_blacklist")
        )

    blacklisted = create(blacklist_user)


# =================================================
# MEDIAINFO CORE
# =================================================
async def gen_mediainfo(message, link=None, media=None, mmsg=None):
    temp = await sendMessage(message, "<i>📊 Generating MediaInfo...</i>")
    des_path = None

    try:
        base = "Mediainfo"
        if not await aiopath.isdir(base):
            await mkdir(base)

        if link:
            filename = re_search(r".+/(.+)", link).group(1)
            des_path = ospath.join(base, filename)
            async with ClientSession() as session:
                async with session.get(link) as r:
                    async with aiopen(des_path, "wb") as f:
                        async for chunk in r.content.iter_chunked(10_000_000):
                            await f.write(chunk)
                            break

        elif media:
            des_path = ospath.join(base, media.file_name)
            if media.file_size <= 50 * 1024 * 1024:
                await mmsg.download(ospath.join(getcwd(), des_path))
            else:
                async for chunk in bot.stream_media(media, limit=5):
                    async with aiopen(des_path, "ab") as f:
                        await f.write(chunk)

        stdout, _, _ = await cmd_exec(ssplit(f'mediainfo "{des_path}"'))

        content = f"<h4>📌 {ospath.basename(des_path)}</h4><br>"
        if stdout:
            content += f"<pre>{stdout}</pre>"

        page = await telegraph.create_page("MediaInfo", content)

        await editMessage(
            temp,
            f"<b>📄 MediaInfo:</b>\n\n➲ https://graph.org/{page['path']}",
            disable_web_page_preview=False,
        )

    except Exception as e:
        LOGGER.error(e)
        await editMessage(temp, f"❌ MediaInfo failed\n<code>{e}</code>")

    finally:
        if des_path and await aiopath.exists(des_path):
            await aioremove(des_path)


# =================================================
# COMMAND REGISTER
# =================================================
bot.add_handler(
    MessageHandler(
        mediainfo,
        filters=command(["mediainfo", "mi"])
        & CustomFilters.authorized
        & ~CustomFilters.blacklisted
    )
                )
