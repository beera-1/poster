from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import aiohttp
import re

WORKER_URL = "https://zee5v2.botzs.workers.dev/"

@Client.on_message(filters.command("zee5"))
async def zee5_poster(client: Client, message: Message):
    # ------------------ Authorization Check ------------------
    OFFICIAL_GROUPS = ["-1002311378229"]  # your official group ID
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return
    # ---------------------------------------------------------

    if len(message.command) < 2:
        await message.reply_text(
            "Send a ZEE5 movie URL like:\n/zee5 https://www.zee5.com/movies/details/krack/0-0-1z51604"
        )
        return

    movie_url = message.command[1]

    if "zee5.com" not in movie_url:
        await message.reply_text("Please provide a valid ZEE5 movie URL.")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={movie_url}") as resp:
                text_data = await resp.text()

        # Extract info from plain text
        posters = {
            "list": re.search(r"Zee5V2 Posters:\s*(https[^\s]+)", text_data),
            "portrait": re.search(r"Portrait:\s*(https[^\s]+)", text_data),
            "cover": re.search(r"Cover:\s*(https[^\s]+)", text_data),
            "app_cover": re.search(r"App cover:\s*(https[^\s]+)", text_data),
            "logo": re.search(r"Logo:\s*(https[^\s]+)", text_data),
        }

        title_match = re.search(r"\n([^\n]+)\s\(\d{4}\)", text_data)
        title = title_match.group(1).strip() if title_match else "Unknown Movie"
        year_match = re.search(r"\((\d{4})\)", text_data)
        year = year_match.group(1) if year_match else "----"

        def link_text(name, key):
            m = posters.get(key)
            if m and "not found" not in m.group(1):
                return f"🔹 <b>{name}</b>: <a href='{m.group(1)}'>Click Here</a>\n"
            return f"🔹 <b>{name}</b>: Not Found\n"

        # Build message
        result_text = (
            f"🎬 <b>{title}</b> ({year})\n\n"
            f"{link_text('List Poster', 'list')}"
            f"{link_text('Portrait', 'portrait')}"
            f"{link_text('Cover', 'cover')}"
            f"{link_text('App Cover', 'app_cover')}"
            f"{link_text('Logo', 'logo')}\n"
            f"⚡ Powered by <a href='https://t.me/AddaFiles'>@AddaFiles</a>"
        )

        await message.reply_text(
            result_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )

    except Exception as e:
        await message.reply_text(f"⚠️ Error fetching poster: {e}")
