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

    loading = await message.reply("⏳ Fetching CineVood links...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                data = await resp.json()

    except Exception as e:
        await loading.edit(f"❌ Error fetching data:\n`{e}`", parse_mode="markdown")
        return

    # Worker error check
    if not data.get("ok"):
        await loading.edit("❌ Worker error occurred.")
        return

    # Build Output Message
    title = data.get("title", "Unknown")
    files = data.get("files", [])

    if not files:
        await loading.edit("❌ No OxxFile links found.")
        return

    # ---------------------------
    # FINAL OUTPUT FORMAT (Screenshot Style)
    # ---------------------------
    text = f"≡ ***{title}***\n\n"

    for i, f in enumerate(files, start=1):
        name = f.get("name", "Unknown")
        size = f.get("size", "Unknown")
        oxx = f.get("oxx_link")

        text += f"**{i}.** {name} `{size}`\n"
        text += f"╰ **Links :** ☁️[**OxxFile**]({oxx})\n\n"

    text += "━━━━━━━━━━━━ ✦ ✧ ✦ ━━━━━━━━━━━━\n\n"

    # ---- ONLY THIS PART ADDED (NO OTHER CHANGES) ----
    text += f"<b>Requested By :-</b> {message.from_user.mention}\n\n"
    text += f"<b>(#ID_{message.from_user.id})</b>"
    # -------------------------------------------------

    await loading.edit(text, parse_mode=ParseMode.HTML)
