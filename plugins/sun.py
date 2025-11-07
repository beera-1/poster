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
            "**Usage:**\n**/sunnxt <SunNXT page URL>**",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    page_url = message.text.split(" ", 1)[1].strip()

    # ------------------ Fetch from Worker ------------------
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

        main_poster = posters[1] if len(posters) > 1 else (posters[0] if posters else "")
        cover = posters[0] if len(posters) > 1 else ""

        # Extract image URLs from text
        portrait = re.search(r"Portrait:\s*(https[^\s]+)", text)
        square = re.search(r"Square:\s*(https[^\s]+)", text)
        logo = re.search(r"Logo:\s*(https[^\s]+)", text)

        portrait_url = portrait.group(1) if portrait else ""
        square_url = square.group(1) if square else ""
        logo_url = logo.group(1) if logo else ""

        # Extract movie title, year, and language
        title_match = re.search(r"\n([A-Za-z0-9\s]+)\s*\((\d{4})\)", text)
        if title_match:
            movie_title = title_match.group(1).strip()
            movie_year = title_match.group(2).strip()
        else:
            movie_title = "Unknown"
            movie_year = ""

        lang_match = re.search(r"/([a-z]+)-movie-", page_url)
        language = lang_match.group(1).capitalize() if lang_match else ""

        # ------------------ Build Final Formatted Message ------------------
        out = (
            f"**Sun NXT Posters:**\n"
            f"**{main_poster}**\n\n"
        )

        if portrait_url:
            out += f"**Portrait:** [**LINK**]({portrait_url})\n\n"
        if cover:
            out += f"**Cover:** [**LINK**]({cover})\n\n"
        if square_url:
            out += f"**Square:** [**LINK**]({square_url})\n\n"
        if logo_url:
            out += f"**Logo:** [**LINK**]({logo_url})\n\n"

        # Title + Year + Language (Fully Bold)
        details = f"**{movie_title} ({movie_year})"
        if language:
            details += f" • {language}"
        details += "**\n\n"

        out += details
        out += "**Powered by @AddaFile**"

        # ------------------ Send Response ------------------
        await message.reply(
            out,
            disable_web_page_preview=False,
            parse_mode=ParseMode.MARKDOWN,
        )

    except Exception as e:
        await message.reply(f"⚠️ **Error:** {e}")
