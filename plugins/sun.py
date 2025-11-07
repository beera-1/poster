from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import aiohttp
import re

WORKER_URL = "https://sun.botzs.workers.dev/"  # 🌐 your SunNXT Worker URL

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

        # ---------------- CLEAN WORKER TEXT ----------------
        # Remove any previous “Portrait / Cover / Square / Logo” lines from Worker
        raw_text = re.sub(r"(Portrait:.*|Cover:.*|Square:.*|Logo:.*)", "", raw_text)

        # ---------------- EXTRACT LINKS ----------------
        def extract(label):
            match = re.search(fr"{label}:\s*(https?://[^\s]+)", raw_text)
            return match.group(1) if match else None

        poster = extract("Sun NXT Posters")
        portrait = re.search(r"https?://[^\s]+1000x1500[^\s]+", raw_text)
        cover = re.search(r"https?://[^\s]+1920x1080[^\s]+", raw_text)
        square = re.search(r"https?://[^\s]+1000x1000[^\s]+", raw_text)
        logo = re.search(r"https?://[^\s]+\.png", raw_text)

        portrait = portrait.group(0) if portrait else None
        cover = cover.group(0) if cover else None
        square = square.group(0) if square else None
        logo = logo.group(0) if logo else None

        # ---------------- SWAP POSTER ↔ COVER ----------------
        if poster and cover:
            poster, cover = cover, poster

        # ---------------- EXTRACT TITLE ----------------
        title_match = re.search(r"\n\n(.+?) Full Movie Online", raw_text, re.S)
        title = title_match.group(1).strip() if title_match else "Sun NXT Movie"

        # ---------------- FINAL CLEAN MESSAGE ----------------
        text = (
            f"Sun NXT Posters:\n{poster}\n\n"
            f"Portrait: [Link]({portrait})\n\n"
            f"Cover: [Link]({cover})\n\n"
            f"Square: [Link]({square})\n\n"
            f"Logo: [Link]({logo})\n\n"
            f"{title}\n\n"
            f"Powered by @AddaFile"
        )

        # ---------------- SEND MESSAGE ----------------
        await message.reply_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False
        )

    except Exception as e:
        await message.reply_text(f"⚠️ Error fetching Sun NXT poster:\n`{e}`")
