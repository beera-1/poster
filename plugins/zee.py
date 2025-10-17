from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import aiohttp

WORKER_URL = "https://zee.botzs.workers.dev/"

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
                data = await resp.json()

        movie_name = data.get("movie_name", "Unknown Movie")
        landscape = data.get("landscape", [])

        if not landscape:
            await message.reply_text(f"No poster found for {movie_name}.")
            return

        # Format message with multiple clickable links
        landscape_text = ""
        for i, url in enumerate(landscape, start=1):
            landscape_text += f"{i}. <a href=\"{url}\">Click Here</a>\n"

        text = (
            f"Zee Poster: {landscape[0]}\n\n"
            f"🌄 Landscape:\n{landscape_text}\n"
            f"🎬 {movie_name}\n\n"
            f"⚡ Powered By @AddaFiles"
        )

        await message.reply_text(
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )

    except Exception as e:
        await message.reply_text(f"⚠️ Error fetching poster: {e}")
