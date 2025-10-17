from pyrogram import Client, filters
import aiohttp
import json

app = Client("bms_bot")  # uses your existing API_ID, API_HASH, BOT_TOKEN from config
WORKER_API = "https://book.botzs.workers.dev/?url="

@app.on_message(filters.command(["bms", "bookmyshow"]) & filters.private)
async def bms_handler(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "Send a BookMyShow URL:\n`/bms https://in.bookmyshow.com/movies/<slug>/ET00000000`",
            parse_mode="markdown"
        )
        return

    url = message.command[1]
    waiting = await message.reply_text("Fetching HQ posters... ⏳")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WORKER_API + url) as resp:
                if resp.status != 200:
                    await waiting.edit_text(f"❌ Worker returned status {resp.status}")
                    return
                data = await resp.json()

        if not data.get("ok"):
            await waiting.edit_text("❌ Invalid response from worker.")
            return

        posters = data.get("posters", [])
        if not posters:
            await waiting.edit_text("😭 No HQ images found.")
            return

        await waiting.delete()

        text_lines = [f"🎬 <b>BookMyShow Posters</b>\n<a href='{url}'>🎟 Click Here (Source)</a>\n"]
        
        # Send each image with clickable “Click Here” link
        for i, poster in enumerate(posters[:4], start=1):
            try:
                await message.reply_photo(
                    photo=poster,
                    caption=f"<b>{i}️⃣ Poster</b>\n👉 <a href='{poster}'>Click Here</a>",
                    parse_mode="html",
                    disable_web_page_preview=True
                )
                text_lines.append(f"{i}️⃣ 👉 <a href='{poster}'>Click Here</a>")
            except Exception:
                pass

        # Send final summary message
        text_output = "\n".join(text_lines)
        await message.reply_text(text_output, parse_mode="html", disable_web_page_preview=True)

    except Exception as e:
        await waiting.edit_text(f"⚠️ Error: {e}")

if __name__ == "__main__":
    app.run()
