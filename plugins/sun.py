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
        # Fetch Worker Output
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={movie_url}") as resp:
                raw_text = await resp.text()

        # Extract the main poster
        main_poster_match = re.search(r"Sun NXT Posters:\s*(https?://[^\s]+)", raw_text)
        main_poster = main_poster_match.group(1) if main_poster_match else None

        # 🔄 Swap Poster ↔ Cover (you asked this earlier)
        cover_match = re.search(r"Cover:\s*(https?://[^\s]+)", raw_text)
        if main_poster and cover_match:
            cover_url = cover_match.group(1)
            raw_text = raw_text.replace(main_poster, "TEMP_SWAP")
            raw_text = raw_text.replace(cover_url, main_poster)
            raw_text = raw_text.replace("TEMP_SWAP", cover_url)

        # Replace all URLs except main poster with [**LINK**]
        def hide_urls_except_main(text, keep_url):
            urls = re.findall(r"https?://[^\s]+", text)
            for url in urls:
                if url != keep_url:
                    text = text.replace(url, "[**LINK**](" + url + ")")
            return text

        final_text = hide_urls_except_main(raw_text, main_poster)

        # Make sure bold formatting works
        final_text = re.sub(r"(?<=:)\s*\[", " [", final_text)
        final_text = f"**{final_text.strip()}**"

        # Send formatted message
        await message.reply_text(
            text=final_text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False  # show main poster preview
        )

    except Exception as e:
        await message.reply_text(f"⚠️ Error fetching Sun NXT poster:\n`{e}`")
