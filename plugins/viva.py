from pyrogram import Client, filters
import aiohttp
import re
import html

# VivaMax poster patterns
POSTER_TYPES = {
    "Poster": "MAIN_HORIZ",
    "Portrait": "MAIN_VERT",
    "Cover": "WEBHERO",
    "Square": "HERO"
}

async def fetch_html(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
            if resp.status == 200:
                return await resp.text()
    return None

async def check_exists(session, url):
    try:
        async with session.head(url) as resp:
            return resp.status == 200
    except:
        return False

async def get_vivamax_posters(viva_url):
    # Extract ID from URL
    match = re.search(r"/(movie|series)/([A-Za-z0-9]+)", viva_url)
    if not match:
        return "❌ Invalid VivaMax URL!"

    content_id = match.group(2)
    html_data = await fetch_html(viva_url)
    if not html_data:
        return f"❌ Failed to fetch page for {content_id}"

    # Extract title
    title_match = re.search(r"<title>(.*?)</title>", html_data, re.IGNORECASE)
    if title_match:
        title_text = title_match.group(1)
        title_text = html.unescape(title_text)
        title_text = re.sub(r"\s*\|.*", "", title_text).strip()
    else:
        title_text = "UNKNOWN"

    # Clean for URL
    title_encoded = title_text.replace(" ", "%20").replace("'", "%27")

    # Build possible poster URLs
    results = []
    async with aiohttp.ClientSession() as session:
        for name, tag in POSTER_TYPES.items():
            test_url = f"https://public.vivamax.net/images/{content_id}_KA_{tag}_LM_{title_encoded}.ori.jpg"
            if await check_exists(session, test_url):
                results.append((name, test_url))

    # Build reply text
    if not results:
        return f"😢 No poster links found for {title_text} ({content_id})"

    msg = ["**VivaMax Posters:**"]
    for label, link in results:
        msg.append(f"{label}: {link}")

    msg.append(f"\n**{title_text}** ({content_id})")
    return "\n".join(msg)


@Client.on_message(filters.command("viva"))
async def viva_command(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/viva <VivaMax_URL>`", quote=True)

    viva_url = message.text.split(None, 1)[1].strip()
    await message.reply_chat_action("typing")

    result = await get_vivamax_posters(viva_url)
    await message.reply_text(result, disable_web_page_preview=True)
