#!/usr/bin/env python3
import os
import re
import asyncio
from shlex import split as ssplit

from aiohttp import ClientSession
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, mkdir
from os import path as ospath

from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG =================
OFFICIAL_GROUPS = ["-1002311378229"]   # your group ID
MAX_LEN = 4000


# ================= SAFE SEND =================
async def safe_edit_or_send(msg, text, **kwargs):
    if len(text) <= MAX_LEN:
        return await msg.edit(text, **kwargs)

    parts = [text[i:i + MAX_LEN] for i in range(0, len(text), MAX_LEN)]
    await msg.edit(parts[0], **kwargs)
    for part in parts[1:]:
        await msg.reply(part, **kwargs)


# ================= MEDIAINFO FORMAT =================
SECTION_EMOJI = {
    "General": "🗒",
    "Video": "🎞",
    "Audio": "🔊",
    "Text": "🔠",
    "Menu": "🗃",
}

def parseinfo(out: str):
    html = ""
    for line in out.splitlines():
        for sec, emo in SECTION_EMOJI.items():
            if line.startswith(sec):
                if html:
                    html += "</pre>\n"
                html += f"<b>{emo} {line.replace('Text','Subtitle')}</b>\n<pre>"
                break
        else:
            html += line + "\n"
    return html + "</pre>"


# ================= COMMAND =================
@Client.on_message(filters.command(["mediainfo", "mi"]))
async def mediainfo_handler(client: Client, message: Message):

    # -------- GROUP ONLY --------
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command works only in our official group.")

    reply = message.reply_to_message
    wait = await message.reply("📊 Generating MediaInfo...")

    base = "Mediainfo"
    if not await aiopath.isdir(base):
        await mkdir(base)

    file_path = None

    try:
        # ========== CASE 1: /mi <link> ==========
        if len(message.command) > 1:
            url = message.command[1]

        # ========== CASE 2: reply to TEXT (HubCloud) ==========
        elif reply and (reply.text or reply.caption):
            text = reply.text or reply.caption
            urls = re.findall(r"https?://\S+", text)
            if not urls:
                return await wait.edit("❌ No downloadable link found in message.")
            url = urls[0]

        # ========== CASE 3: reply to MEDIA ==========
        elif reply:
            media = reply.document or reply.video or reply.audio
            if not media:
                return await wait.edit("❌ Reply to a media file or link post.")

            file_path = ospath.join(base, media.file_name)

            if media.file_size <= 50 * 1024 * 1024:
                await reply.download(file_path)
            else:
                async for chunk in client.stream_media(media, limit=5):
                    async with aiopen(file_path, "ab") as f:
                        await f.write(chunk)

        else:
            return await wait.edit("❌ Usage:\n/mi reply to media or link")

        # ========== DOWNLOAD FROM LINK ==========
        if not file_path:
            fname = re.search(r"/([^/?#]+)", url).group(1)
            file_path = ospath.join(base, fname)

            async with ClientSession() as session:
                async with session.get(url, timeout=120) as r:
                    async with aiopen(file_path, "wb") as f:
                        async for chunk in r.content.iter_chunked(10_000_000):
                            await f.write(chunk)
                            break

        # ========== MEDIAINFO ==========
        proc = await asyncio.create_subprocess_exec(
            *ssplit(f'mediainfo "{file_path}"'),
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        info = stdout.decode(errors="ignore").strip()

        if not info:
            return await wait.edit("❌ MediaInfo failed.")

        output = f"<b>📌 {os.path.basename(file_path)}</b>\n\n"
        output += parseinfo(info)

        await safe_edit_or_send(
            wait,
            output,
            parse_mode="html",
            disable_web_page_preview=True
        )

    except Exception as e:
        await wait.edit(f"⚠️ Error:\n`{e}`")

    finally:
        if file_path and await aiopath.exists(file_path):
            await aioremove(file_path)
