from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import aiohttp
import json

CINEVOOD_WORKER = "https://cinvood.botzs.workers.dev/?url="
OFFICIAL_GROUPS = ["-1002311378229"]


@Client.on_message(filters.command(["cv", "cinevood"]))
async def cinevood_scraper(client: Client, message: Message):

    # Authorization Check
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return

    # No link provided
    if len(message.command) < 2:
        await message.reply("❗ Usage:\n`/cv https://1cinevood.world/...`", parse_mode="markdown")
        return

    page_url = message.command[1]
    api_url = CINEVOOD_WORKER + page_url

    # Fetch JSON from worker
    await message.reply("⏳ Fetching CineVood links...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                data = await resp.json()

    except Exception as e:
        await message.reply(f"❌ Error fetching data:\n`{e}`", parse_mode="markdown")
        return

    # Worker error check
    if not data.get("ok"):
        await message.reply("❌ Worker error occurred.")
        return

    # Build Output Message
    title = data.get("title", "Unknown")
    files = data.get("files", [])

    if not files:
        await message.reply("❌ No OxxFile links found.")
        return

    text = f"🎬 **{title}**\n\n"

    for f in files:
        name = f.get("name", "Unknown")
        size = f.get("size", "Unknown")
        oxx = f.get("oxx_link")

        text += f"📁 **{name}**\n"
        text += f"📦 Size: `{size}`\n"
        text += f"🔗 Link: {oxx}\n\n"

    await message.reply(text, parse_mode=ParseMode.MARKDOWN)
