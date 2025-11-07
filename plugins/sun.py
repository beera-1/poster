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
        # 1️⃣ Fetch Worker output (plain text)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={movie_url}") as resp:
                raw_text = await resp.text()

        # 2️⃣ Extract image URLs from raw text
        def extract(label):
            match = re.search(fr"{label}:\s*(https?://[^\s]+)", raw_text)
            return match.group(1) if match else None

        main_poster = extract("Sun NXT Posters")
        portrait = extract("Portrait")
        cover = extract("Cover")
        square = extract("Square")
        logo = extract("Logo")

        # 3️⃣ Extract movie title from worker text
        title_match = re.search(r"\n\n(.+?) Full Movie Online", raw_text, re.S)
        title = title_match.group(1).strip() if title_match else "Sun NXT Movie"

        # 4️⃣ Auto-detect language from URL or text
        lang_map = {
            "kannada": "Kannada",
            "tamil": "Tamil",
            "telugu": "Telugu",
            "malayalam": "Malayalam",
            "hindi": "Hindi"
        }
        language = None
        for key, name in lang_map.items():
            if key in movie_url.lower() or key in raw_text.lower():
                language = name
                break

        # 5️⃣ Auto-detect year (from URL or text)
        year_match = re.search(r"\b(19|20)\d{2}\b", movie_url)
        year = year_match.group(0) if year_match else None

        # 6️⃣ Format title like Chakravyuha (2016) (Kannada)
        if year and language:
            title = f"{title} ({year}) ({language})"
        elif year:
            title = f"{title} ({year})"
        elif language:
            title = f"{title} ({language})"

        # 7️⃣ ✅ SWAP main_poster ↔ cover (as per your instruction)
        if main_poster and cover:
            main_poster, cover = cover, main_poster

        # 8️⃣ Build clean message (only one section)
        text = (
            f"**Sun NXT Posters:**\n{main_poster}\n\n"
            f"**Portrait:** [Link]({portrait})\n\n"
            f"**Cover:** [Link]({cover})\n\n"
            f"**Square:** [Link]({square})\n\n"
            f"**Logo:** [Link]({logo})\n\n"
            f"**{title}**\n\n"
            f"**Powered by @AddaFile**"
        )

        # 9️⃣ Send clean message with web preview
        await message.reply_text(
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False  # shows poster preview
        )

    except Exception as e:
        await message.reply_text(f"⚠️ Error fetching Sun NXT poster:\n`{e}`")
