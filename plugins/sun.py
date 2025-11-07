from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import aiohttp
import re

WORKER_URL = "https://sun.botzs.workers.dev/"  # 🌐 your SunNXT Worker URL

@Client.on_message(filters.command(["sun", "sunnxt"]))
async def sunnxt_poster(client: Client, message: Message):
    OFFICIAL_GROUPS = ["-1002311378229"]
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return

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
        # 🔹 1. Fetch Worker output
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={movie_url}") as resp:
                raw_text = await resp.text()

        # 🔹 2. Extract URLs
        def extract(label):
            match = re.search(fr"{label}:\s*(https?://[^\s]+)", raw_text)
            return match.group(1) if match else None

        poster = extract("Sun NXT Posters")
        cover = extract("Cover")
        portrait = extract("Portrait")
        square = extract("Square")
        logo = extract("Logo")

        # 🔹 3. SWAP Poster ↔ Cover
        if poster and cover:
            poster, cover = cover, poster  # swap values cleanly

        # 🔹 4. Extract title
        title_match = re.search(r"\n\n(.+?) Full Movie Online", raw_text, re.S)
        title = title_match.group(1).strip() if title_match else "Sun NXT Movie"

        # 🔹 5. Format message (poster visible, all others hidden)
        text = (
            f"**Sun NXT Posters:** {poster}\n\n"
            f"**Portrait:** [**LINK**]({portrait})\n"
            f"**Cover:** [**LINK**]({cover})\n"
            f"**Square:** [**LINK**]({square})\n"
            f"**Logo:** [**LINK**]({logo})\n\n"
            f"🎬 **{title}**\n\n"
            f"**Powered by @AddaFile**"
        )

        # 🔹 6. Send final message (main poster visible)
        await message.reply_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False
        )

    except Exception as e:
        await message.reply_text(f"⚠️ Error fetching Sun NXT poster:\n`{e}`")
