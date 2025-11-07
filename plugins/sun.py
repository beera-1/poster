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

        # 🧹 Remove any unwanted duplicate block (like “Portrait:” links at bottom)
        cleaned = []
        for line in raw_text.splitlines():
            # skip repeated lines containing "Portrait:" "Cover:" etc.
            if re.search(r"^(Portrait|Cover|Square|Logo):\s*https?://", line.strip()):
                continue
            cleaned.append(line)
        raw_text = "\n".join(cleaned).strip()

        # ---------------- SWAP LOGIC ----------------
        poster_match = re.search(r"Sun NXT Posters:\s*(https?://[^\s]+)", raw_text)
        cover_match = re.search(r"Cover:\s*(https?://[^\s]+)", raw_text)
        poster_url = poster_match.group(1) if poster_match else None
        cover_url = cover_match.group(1) if cover_match else None

        # 🔄 Swap Poster ↔ Cover
        if poster_url and cover_url:
            raw_text = raw_text.replace(poster_url, "TEMP_SWAP")
            raw_text = raw_text.replace(cover_url, poster_url)
            raw_text = raw_text.replace("TEMP_SWAP", cover_url)

        # ---------------- EXTRACT LINKS ----------------
        def extract(label):
            match = re.search(fr"{label}:\s*(https?://[^\s]+)", raw_text)
            return match.group(1) if match else None

        poster = extract("Sun NXT Posters")
        portrait = extract("Portrait")
        cover = extract("Cover")
        square = extract("Square")
        logo = extract("Logo")

        # ---------------- EXTRACT TITLE ----------------
        title_match = re.search(r"\n\n(.+?) Full Movie Online", raw_text, re.S)
        title = title_match.group(1).strip() if title_match else "Sun NXT Movie"

        # ---------------- BUILD FINAL MESSAGE ----------------
        text = (
            f"**Sun NXT Posters:**\n{poster}\n\n"
            f"**Portrait:** [Link]({portrait})\n\n"
            f"**Cover:** [Link]({cover})\n\n"
            f"**Square:** [Link]({square})\n\n"
            f"**Logo:** [Link]({logo})\n\n"
            f"**{title}**\n\n"
            f"**Powered by @AddaFile**"
        )

        # ---------------- SEND CLEAN OUTPUT ----------------
        await message.reply_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False
        )

    except Exception as e:
        await message.reply_text(f"⚠️ Error fetching Sun NXT poster:\n`{e}`")
