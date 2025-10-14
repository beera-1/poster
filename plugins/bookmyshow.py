from pyrogram import Client, filters
import aiohttp
import re
import json

app = Client("bms_bot")  # uses your existing API_ID, API_HASH, BOT_TOKEN from config

async def fetch_html(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            return await resp.text()

def extract_bms_images(html):
    urls = set()
    regex = r'https:\/\/assets-in\.bmscdn\.com\/[^\s"\'<>]+(?:\.jpg|\.jpeg|\.png)'
    matches = re.findall(regex, html)
    for url in matches:
        if re.search(r'BMS_logo|artist/images|avatars', url, re.I):
            continue
        url = re.sub(r'tr:w-\d+,h-\d+', 'tr:w-1280,h-1920', url)
        url = url.replace("/small/", "/xlarge/").replace("/medium/", "/xlarge/").replace("/large/", "/xlarge/")
        urls.add(url)

    all_images = list(urls)

    portrait = next((u for u in all_images if "-portrait.jpg" in u), None)
    landscape = next((u for u in all_images if "-landscape.jpg" in u), None)
    xxlarge = next((u for u in all_images if "/listing/xxlarge/" in u), None)
    thumbnail = next((u for u in all_images if "/thumbnail/xlarge/" in u), None)

    fallback = lambda used: next((u for u in all_images if u not in [portrait, landscape, xxlarge, thumbnail]), None)
    if not portrait: portrait = fallback(portrait)
    if not landscape: landscape = fallback(landscape)
    if not xxlarge: xxlarge = fallback(xxlarge)
    if not thumbnail: thumbnail = fallback(thumbnail)

    return [x for x in [portrait, landscape, xxlarge, thumbnail] if x]

@app.on_message(filters.command(["bms", "bookmyshow"]) & filters.private)
async def bms_handler(client, message):
    if len(message.command) < 2:
        await message.reply_text("Send a BookMyShow URL:\n`/bms https://in.bookmyshow.com/movies/<slug>/ET00000000`", parse_mode="markdown")
        return

    url = message.command[1]
    await message.reply_text("Fetching HQ posters... ⏳")

    try:
        html = await fetch_html(url)
        posters = extract_bms_images(html)

        if not posters:
            await message.reply_text("No HQ images found 😭")
            return

        result_json = json.dumps({
            "ok": True,
            "source": url,
            "count": len(posters),
            "posters": posters
        }, indent=2)

        await message.reply_text(f"<code>{result_json}</code>", parse_mode="html")

    except Exception as e:
        await message.reply_text(f"Error: {e}")

if __name__ == "__main__":
    app.run()
