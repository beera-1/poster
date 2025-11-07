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
        # 🔹 1. Fetch full raw worker response
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={movie_url}") as resp:
                raw_text = await resp.text()

        # 🔹 2. Extract links from raw text using regex
        def extract(label):
            match = re.search(fr"{label}:\s*(https?://[^\s]+)", raw_text)
            return match.group(1) if match else None

        poster = extract("Sun NXT Posters")
        portrait = extract("Portrait")
        cover = extract("Cover")
        square = extract("Square")
        logo = extract("Logo")

        # 🔹 3. Extract title
        title_match = re.search(r"\n\n(.+?) Full Movie Online", raw_text, re.S)
        title = title_match.group(1).strip() if title_match else "Sun NXT Movie"

        # 🔹 4. Swap Poster ↔ Cover
        if poster and cover:
            poster, cover = cover, poster

        # 🔹 5. Check that poster exists
        if not poster:
            await message.reply_text("⚠️ No images found in Sun NXT page.")
            return

        # 🔹 6. Build clean Markdown message
        text = (
            f"**Sun NXT Posters:**\n{poster}\n\n"
            f"**Portrait:** [Link]({portrait})\n\n"
            f"**Cover:** [Link]({cover})\n\n"
            f"**Square:** [Link]({square})\n\n"
            f"**Logo:** [Link]({logo})\n\n"
            f"**{title}**\n\n"
            f"**Powered by @AddaFile**"
        )

        # 🔹 7. Send message with web preview (no send_photo)
        await message.reply_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False  # <-- this enables image preview
        )

        # ✅ raw_text kept for internal use but not displayed

    except Exception as e:
        await message.reply_text(f"⚠️ Error fetching Sun NXT poster:\n`{e}`")
