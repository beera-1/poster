from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import time
import re

OFFICIAL_GROUPS = ["-1002311378229"]
HEADERS = {"User-Agent": "Mozilla/5.0"}

API_ENDPOINT = "https://hub-fawn.vercel.app/api/bypaas/test.php"

URL_RE = re.compile(r"https?://\S+")


@Client.on_message(filters.command("gdpack"))
async def gdpack_handler(client: Client, message: Message):

    # 🔒 OFFICIAL GROUP ONLY
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ Official group only.")

    # 🔗 Extract URL
    links = URL_RE.findall(message.text or "")
    if not links and message.reply_to_message:
        links = URL_RE.findall(message.reply_to_message.text or "")

    if not links:
        return await message.reply(
            "⚠️ Usage:\n<code>/gdpack https://gdflix.dev/pack/XXXX</code>"
        )

    pack_url = links[0]

    msg = await message.reply("⏳ Fetching GDFlix pack links...")
    start = time.time()

    try:
        r = requests.get(
            API_ENDPOINT,
            params={"url": pack_url},
            headers=HEADERS,
            timeout=20
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return await msg.edit(f"❌ API Error:\n<code>{e}</code>")

    files = data.get("files", [])
    count = data.get("count", len(files))

    if not files:
        return await msg.edit("❌ No files found in this pack.")

    text = (
        f"📦 <b>GDFlix Pack Extracted</b>\n"
        f"🔢 <b>Total Files:</b> {count}\n"
        f"⏱ <b>Time:</b> {round(time.time() - start, 2)}s\n\n"
    )

    for i, link in enumerate(files, start=1):
        text += f"{i}. <code>{link}</code>\n"

    # 🧱 TELEGRAM LIMIT SAFE
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        await msg.edit(parts[0])
        for part in parts[1:]:
            await message.reply_text(part)
    else:
        await msg.edit(text)
