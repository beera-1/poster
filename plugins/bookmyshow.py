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
    await message.reply_text("Fetching HQ posters... ⏳")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WORKER_API + url) as resp:
                if resp.status != 200:
                    await message.reply_text(f"Worker returned status {resp.status}")
                    return
                data = await resp.json()

        if not data.get("ok"):
            await message.reply_text("❌ Invalid response from worker.")
            return

        posters = data.get("posters", [])
        if not posters:
            await message.reply_text("😭 No HQ images found.")
            return

        # Send top 4 poster images (if available)
        for poster in posters[:4]:
            try:
                await message.reply_photo(poster)
            except Exception:
                pass  # skip broken URLs safely

        # Send JSON summary
        result_json = json.dumps(
            {
                "ok": True,
                "source": url,
                "count": len(posters[:4]),
                "posters": posters[:4]
            },
            indent=2
        )
        await message.reply_text(f"<code>{result_json}</code>", parse_mode="html")

    except Exception as e:
        await message.reply_text(f"⚠️ Error: {e}")

if __name__ == "__main__":
    app.run()
