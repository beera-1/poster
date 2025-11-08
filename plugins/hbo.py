from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import aiohttp

# Your Cloudflare Worker URL
WORKER_URL = "https://hbo.botzs.workers.dev/"
OFFICIAL_GROUPS = ["-1002311378229"]  # your official Telegram group ID


@Client.on_message(filters.command("hbo"))
async def hbo_poster(client: Client, message: Message):
    # ------------------ Authorization Check ------------------
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply_text("❌ This command only works in our official group.")
        return

    # ------------------ Input Validation ------------------
    if len(message.command) < 2:
        await message.reply_text(
            "🎬 **Usage:**\n`/hbo <movie_url>`\n\n"
            "🧩 Example:\n`/hbo https://www.hbo.com/content/movies/a-minecraft-movie`"
        )
        return

    movie_url = message.text.split(maxsplit=1)[1].strip()
    await message.reply_chat_action("typing")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={movie_url}") as resp:
                if resp.status != 200:
                    await message.reply_text(f"⚠️ Worker returned error: `{resp.status}`")
                    return

                data = await resp.json()

                if not data.get("ok"):
                    await message.reply_text(f"❌ Error: {data.get('error', 'Unknown error')}")
                    return

                title = data.get("title", "Unknown Title")
                year = data.get("year", "Unknown Year")
                images = data.get("images", [])

                if not images:
                    await message.reply_text("😢 No posters found for that HBO link.")
                    return

                # ------------------ Format the Response ------------------
                text = (
                    f"🎬 **Title:** {title}\n"
                    f"📅 **Year:** {year}\n"
                    f"🖼️ **Posters Found:** `{len(images)}`\n\n"
                )

                for img in images:
                    text += f"🔗 [Poster Link]({img})\n"

                await message.reply_text(
                    text,
                    disable_web_page_preview=False,
                    parse_mode=ParseMode.MARKDOWN,
                )

    except Exception as e:
        await message.reply_text(f"❌ Error: `{e}`")
