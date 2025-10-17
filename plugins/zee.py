from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import aiohttp

WORKER_URL = "https://book.botzs.workers.dev/"

@Client.on_message(filters.command(["bms", "bookmyshow"]))
async def bookmyshow_poster(client: Client, message: Message):
    # ------------------ Authorization Check ------------------
    OFFICIAL_GROUPS = ["-1002311378229"]  # your official group ID
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return
    # ---------------------------------------------------------

    if len(message.command) < 2:
        await message.reply_text(
            "Send a BookMyShow URL like:\n/bms https://in.bookmyshow.com/movies/details/<slug>/ET00000000"
        )
        return

    movie_url = message.command[1]

    if "bookmyshow.com" not in movie_url:
        await message.reply_text("Please provide a valid BookMyShow movie URL.")
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={movie_url}") as resp:
                data = await resp.json()

        posters = data.get("posters", [])
        if not posters:
            await message.reply_text("😭 No HQ posters found.")
            return

        # Format message with multiple clickable links
        poster_links = ""
        for i, url in enumerate(posters, start=1):
            poster_links += f"{i}. <a href=\"{url}\">Click Here</a>\n"

        text = (
            f"🎬 <b>BookMyShow Posters</b>\n"
            f"🔗 <a href=\"{movie_url}\">Source Link</a>\n\n"
            f"{poster_links}\n"
            f"⚡ Powered By @AddaFiles"
        )

        # Send first image with caption
        try:
            await message.reply_photo(
                photo=posters[0],
                caption=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False
            )
        except Exception:
            await message.reply_text(
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False
            )

    except Exception as e:
        await message.reply_text(f"⚠️ Error fetching posters: {e}")
