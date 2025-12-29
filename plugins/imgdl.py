# imgdl.py

from pyrogram import Client, filters
from pyrogram.types import Message
import re
import aiohttp

IMAGE_REGEX = re.compile(
    r"(https?://[^\s]+?\.(jpg|jpeg|png|webp))",
    re.IGNORECASE
)

@Client.on_message(filters.command("imgdl"))
async def imgdl_handler(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "❌ **Usage:**\n`/imgdl <jpg/png link>`",
            quote=True
        )

    url = message.command[1].strip()

    # Validate image link
    if not IMAGE_REGEX.match(url):
        return await message.reply_text(
            "❌ **Invalid Image Link**\n\nOnly JPG / PNG / WEBP supported.",
            quote=True
        )

    status = await message.reply_text("⏳ **Fetching Image...**", quote=True)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    return await status.edit("❌ **Failed to fetch image**")

        # Send image directly
        await client.send_photo(
            chat_id=message.chat.id,
            photo=url,
            reply_to_message_id=message.id
        )

        await status.delete()

    except Exception as e:
        await status.edit(f"❌ **Error:** `{str(e)}`")
