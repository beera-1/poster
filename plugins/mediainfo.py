#!/usr/bin/env python3
from aiohttp import ClientSession
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from os import path as ospath, getcwd
from re import search as re_search
from shlex import split as ssplit

from pyrogram.handlers import MessageHandler
from pyrogram.filters import command

# ✅ FIXED IMPORT
from poster import bot, LOGGER
from bot.helper.telegram_helper.filters import CustomFilters

# NOTE:
# sendMessage, editMessage, cmd_exec, telegraph
# are already defined in your project
# DO NOT re-import them


# ================= MEDIAINFO CORE =================
async def gen_mediainfo(message, link=None, media=None, mmsg=None):
    temp = await sendMessage(message, "<i>📊 Generating MediaInfo...</i>")
    des_path = None

    try:
        base = "Mediainfo"
        if not await aiopath.isdir(base):
            await mkdir(base)

        # -------- FROM LINK --------
        if link:
            filename = re_search(r".+/(.+)", link).group(1)
            des_path = ospath.join(base, filename)

            async with ClientSession() as session:
                async with session.get(link, headers={"User-Agent": "Mozilla/5.0"}) as r:
                    async with aiopen(des_path, "wb") as f:
                        async for chunk in r.content.iter_chunked(10_000_000):
                            await f.write(chunk)
                            break

        # -------- FROM TELEGRAM MEDIA --------
        elif media:
            des_path = ospath.join(base, media.file_name)
            if media.file_size <= 50 * 1024 * 1024:
                await mmsg.download(ospath.join(getcwd(), des_path))
            else:
                async for chunk in bot.stream_media(media, limit=5):
                    async with aiopen(des_path, "ab") as f:
                        await f.write(chunk)

        # -------- RUN MEDIAINFO --------
        stdout, _, _ = await cmd_exec(ssplit(f'mediainfo "{des_path}"'))

        content = f"<h4>📌 {ospath.basename(des_path)}</h4><br>"
        if stdout:
            content += parseinfo(stdout)

        page = await telegraph.create_page(
            title="MediaInfo",
            content=content
        )

        await editMessage(
            temp,
            f"<b>📄 MediaInfo:</b>\n\n➲ <b>Link :</b> https://graph.org/{page['path']}",
            disable_web_page_preview=False
        )

    except Exception as e:
        LOGGER.error(e)
        await editMessage(temp, f"❌ MediaInfo failed\n<code>{e}</code>")

    finally:
        if des_path and await aiopath.exists(des_path):
            await aioremove(des_path)


# ================= FORMATTER =================
SECTION_EMOJI = {
    "General": "🗒",
    "Video": "🎞",
    "Audio": "🔊",
    "Text": "🔠",
    "Menu": "🗃",
}

def parseinfo(out):
    html = ""
    for line in out.splitlines():
        for sec, emoji in SECTION_EMOJI.items():
            if line.startswith(sec):
                if html:
                    html += "</pre><br>"
                html += f"<h4>{emoji} {line.replace('Text', 'Subtitle')}</h4><pre>"
                break
        else:
            html += line + "\n"
    html += "</pre><br>"
    return html


# ================= COMMAND HANDLER =================
async def mediainfo(_, message):
    rply = message.reply_to_message

    help_msg = (
        "<b>📌 Usage:</b>\n"
        "<code>/mediainfo</code> or <code>/mi</code>\n\n"
        "Reply to a media file\n"
        "OR\n"
        "Send a direct download link"
    )

    if len(message.command) > 1 or (rply and rply.text):
        link = rply.text if rply else message.command[1]
        return await gen_mediainfo(message, link=link)

    if rply:
        media = next(
            (
                i for i in (
                    rply.document,
                    rply.video,
                    rply.audio,
                    rply.voice,
                    rply.animation,
                    rply.video_note,
                ) if i
            ),
            None
        )
        if media:
            return await gen_mediainfo(message, media=media, mmsg=rply)

    return await sendMessage(message, help_msg)


# ================= REGISTER PLUGIN =================
bot.add_handler(
    MessageHandler(
        mediainfo,
        filters=command(["mediainfo", "mi"])
        & CustomFilters.authorized
        & ~CustomFilters.blacklisted
    )
)
