from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import aiohttp
import re

WORKER_URL = "https://sun.botzs.workers.dev/"  # 🌐 your working SunNXT Worker

@Client.on_message(filters.command(["sun", "sunnxt"]))
async def sunnxt_poster(client: Client, message: Message):
    # ------------------ Authorization Check ------------------
    OFFICIAL_GROUPS = ["-1002311378229"]  # your official group ID(s)
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return
    # ---------------------------------------------------------

    if len(message.command) < 2:
        await message.reply_text(
            "Send a Sun NXT movie URL like:\n"
            "/sunnxt https://www.sunnxt.com/kannada-movie-chakravyuha-2016-2016/detail/17263"
        )
        return

    movie_url = message.command[1]

    if "sunnxt.com" not in movie_url:
        await message.reply_text("Please provide a valid Sun NXT movie URL.")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={movie_url}") as resp:
                raw_text = await resp.text()

        # ---------------- SWAP LOGIC ----------------
        poster_match = re.search(r"Sun NXT Posters:\s*(https?://[^\s]+)", raw_text)
        cover_match = re.search(r"Cover:\s*(https?://[^\s]+)", raw_text)

        poster_url = poster_match.group(1) if poster_match else None
        cover_url = cover_match.group(1) if cover_match else None

        # Swap Poster ↔ Cover
        if poster_url and cover_url:
            raw_text = raw_text.replace(poster_url, "TEMP_SWAP")
            raw_text = raw_text.replace(cover_url, poster_url)
            raw_text = raw_text.replace("TEMP_SWAP", cover_url)

        # Clean duplicates like "Full Movie Online Full Movie Online"
        raw_text = re.sub(r"(Full Movie Online\s*)+", "Full Movie Online", raw_text)

        # ---------------- MAKE LINKS CLICKABLE ----------------
        def make_clickable(label, url):
            return f"{label} <a href=\"{url}\">Click Here</a>" if url != "N/A" else f"{label} N/A"

        poster_link = re.search(r"Sun NXT Posters:\s*(https?://[^\s]+)", raw_text)
        portrait_link = re.search(r"Portrait:\s*(https?://[^\s]+)", raw_text)
        cover_link = re.search(r"Cover:\s*(https?://[^\s]+)", raw_text)
        square_link = re.search(r"Square:\s*(https?://[^\s]+)", raw_text)
        logo_link = re.search(r"Logo:\s*(https?://[^\s]+)", raw_text)

        poster = make_clickable("Sun NXT Posters:", poster_link.group(1) if poster_link else "N/A")
        portrait = make_clickable("Portrait:", portrait_link.group(1) if portrait_link else "N/A")
        cover = make_clickable("Cover:", cover_link.group(1) if cover_link else "N/A")
        square = make_clickable("Square:", square_link.group(1) if square_link else "N/A")
        logo = make_clickable("Logo:", logo_link.group(1) if logo_link else "N/A")

        # Extract title (first line after logo or end of section)
        title_match = re.search(r"\n\n(.+?) Full Movie Online", raw_text, re.S)
        title = title_match.group(1).strip() if title_match else "Sun NXT Movie"

        # ---------------- BUILD FINAL MESSAGE ----------------
        formatted = (
            f"{poster}\n\n"
            f"{portrait}\n\n"
            f"{cover}\n\n"
            f"{square}\n\n"
            f"{logo}\n\n"
            f"🎬 <b>{title}</b> Full Movie Online\n\n"
            f"⚡ <b>Powered by @AddaFile</b>"
        )

        await message.reply_text(
            text=formatted,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )

    except Exception as e:
        await message.reply_text(f"⚠️ Error fetching Sun NXT poster:\n<code>{e}</code>")
