from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import aiohttp
import re

WORKER_URL = "https://sun.botzs.workers.dev/"
OFFICIAL_GROUPS = ["-1002311378229"]

@Client.on_message(filters.command(["sunnxt", "sun"]))
async def sunnxt_poster(client: Client, message: Message):
    # ------------------ Authorization Check ------------------
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return

    # ------------------ Command Check ------------------
    if len(message.command) < 2:
        await message.reply(
            "Usage:\n`/sunnxt <SunNXT page URL>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    page_url = message.text.split(" ", 1)[1].strip()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={page_url}", timeout=20) as resp:
                if resp.status != 200:
                    await message.reply(f"❌ Worker returned HTTP {resp.status}")
                    return
                text = await resp.text()

        # ------------------ Swap Main Poster and Cover ------------------
        posters = re.findall(
            r"https:\/\/sund-images\.sunnxt\.com\/[^\s]+1920x1080[^\s]+\.jpg", text
        )

        if len(posters) > 1:
            main_poster, cover = posters[1], posters[0]
            text = text.replace(posters[0], main_poster).replace(posters[1], cover)

        # ------------------ Extract Movie Title ------------------
        movie_match = re.search(r"([A-Za-z0-9\s]+)\s*\(\d{4}\)", text)
        movie_title = movie_match.group(1).strip() if movie_match else "Unknown"

        # ------------------ Bold Formatting ------------------
        formatted = re.sub(r"^Sun NXT Posters:", r"**Sun NXT Posters:**", text, flags=re.MULTILINE)
        formatted = re.sub(r"^(https:\/\/sund-images[^\s]+)", r"**\1**", formatted, flags=re.MULTILINE)
        formatted = re.sub(r"^Portrait:\s*(https[^\s]+)", r"**Portrait:** [**LINK**](\1)", formatted, flags=re.MULTILINE)
        formatted = re.sub(r"^Cover:\s*(https[^\s]+)", r"**Cover:** [**LINK**](\1)", formatted, flags=re.MULTILINE)
        formatted = re.sub(r"^Square:\s*(https[^\s]+)", r"**Square:** [**LINK**](\1)", formatted, flags=re.MULTILINE)
        formatted = re.sub(r"^Logo:\s*(https[^\s]+)", r"**Logo:** [**LINK**](\1)", formatted, flags=re.MULTILINE)
        formatted = re.sub(r"^Powered by @AddaFile", r"**Powered by @AddaFile**", formatted, flags=re.MULTILINE)

        # If movie title exists, make it bold
        formatted = re.sub(
            rf"({movie_title}\s*\(\d{{4}}\).*)",
            r"**\1**",
            formatted,
            flags=re.MULTILINE
        )

        # ------------------ Send Final Message ------------------
        await message.reply(formatted, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=False)

    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")
