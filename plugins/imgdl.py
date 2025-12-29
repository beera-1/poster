# imgdl.py

from pyrogram import Client, filters
from pyrogram.types import Message
import re
import aiohttp

OFFICIAL_GROUPS = ["-1002311378229"]

IMAGE_REGEX = re.compile(
    r"(https?://[^\s]+?\.(jpg|jpeg|png|webp))",
    re.IGNORECASE
)

URL_RE = re.compile(r"https?://[^\s]+")


@Client.on_message(filters.command("imgdl"))
async def imgdl_handler(client: Client, message: Message):

    # ------------------ Restriction ------------------
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ Official group only.")

    # ------------------ Extract Links ------------------
    links = URL_RE.findall(message.text or "")
    if not links and message.reply_to_message:
        links = URL_RE.findall(message.reply_to_message.text or "")

    if not links:
        return await message.reply(
            "⚠️ **Usage:**\n`/imgdl <jpg/png link>`"
        )

    # ------------------ Process (max 5 images) ------------------
    for url in links[:5]:

        if not IMAGE_REGEX.match(url):
            await message.reply(
                f"❌ **Invalid Image Link:**\n`{url}`\n\nOnly JPG / PNG / WEBP supported."
            )
            continue

        status = await message.reply("⏳ **Fetching Image...**")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=20) as resp:
                    if resp.status != 200:
                        await status.edit("❌ **Failed to fetch image**")
                        continue

            await client.send_photo(
                chat_id=message.chat.id,
                photo=url,
                reply_to_message_id=message.id
            )

            await status.delete()

        except Exception as e:
            await status.edit(f"❌ **Error:** `{str(e)}`")
