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

    waiting = await message.reply_text("Fetching HQ posters... ⏳")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={movie_url}") as resp:
                data = await resp.json()

        if not data.get("ok"):
            await waiting.edit_text("❌ Invalid response from worker.")
            return

        posters = data.get("posters", [])
        if not posters:
            await waiting.edit_text("😭 No HQ posters found.")
            return

        await waiting.delete()

        # Send each poster as photo with clickable caption (preview shown automatically)
        for i, url in enumerate(posters, start=1):
            try:
                await message.reply_photo(
                    photo=url,
                    caption=f"<b>{i}️⃣ Poster</b>\n🎉 <a href='{url}'>Click Here</a>",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass

        # Send final summary message with clickable links and web preview
        summary_text = f"🎬 <b>BookMyShow Posters</b>\n🔗 <a href='{movie_url}'>Source Link</a>\n\n"
        for i, url in enumerate(posters, start=1):
            summary_text += f"{i}️⃣ 🎉 <a href='{url}'>{url}</a>\n"
        summary_text += "\n⚡ Powered By @AddaFiles"

        await message.reply_text(
            summary_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False  # ✅ Show web preview
        )

    except Exception as e:
        await waiting.edit_text(f"⚠️ Error fetching posters: {e}")
