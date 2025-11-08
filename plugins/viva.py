from pyrogram import Client, filters
from pyrogram.enums import ChatAction
import aiohttp
import re
import requests
from bs4 import BeautifulSoup
import html

# VivaMax CDN poster types
POSTER_TYPES = {
    "Poster": "MAIN_HORIZ",
    "Portrait": "MAIN_VERT",
    "Cover": "WEBHERO",
    "Square": "HERO"
}


async def check_url(session, url):
    """Check if a given CDN image URL exists"""
    try:
        async with session.head(url) as resp:
            return resp.status == 200
    except:
        return False


def extract_title_from_page(url):
    """Extract the movie title using BeautifulSoup"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        title_tag = soup.find("title")
        if title_tag:
            title_text = html.unescape(title_tag.text)
            # remove "| VivaMax" etc.
            title_text = re.sub(r"\s*\|.*", "", title_text).strip()
            return title_text
    except Exception:
        pass
    return None


async def get_vivamax_posters(viva_url):
    """Build all poster URLs and return formatted text"""
    match = re.search(r"/(movie|series)/([A-Za-z0-9]+)", viva_url)
    if not match:
        return "❌ Invalid VivaMax URL!"

    content_id = match.group(2)

    # Extract title
    title_text = extract_title_from_page(viva_url)
    if not title_text:
        title_text = "UNKNOWN"

    # Encode for CDN URL
    title_encoded = title_text.replace(" ", "%20").replace("'", "%27")

    results = []
    async with aiohttp.ClientSession() as session:
        for label, tag in POSTER_TYPES.items():
            test_url = f"https://public.vivamax.net/images/{content_id}_KA_{tag}_LM_{title_encoded}.ori.jpg"
            if await check_url(session, test_url):
                results.append((label, test_url))

    # Format reply text (plain, safe for Telegram)
    if not results:
        return f"😢 No posters found for {title_text} ({content_id})"

    msg = ["VivaMax Posters:"]
    for label, link in results:
        msg.append(f"{label}: {link}")

    msg.append(f"\n{title_text} ({content_id})")
    return "\n".join(msg)


@Client.on_message(filters.command("viva"))
async def viva_command(client, message):
    """Telegram command /viva <URL>"""
    if len(message.command) < 2:
        return await message.reply_text(
            "Usage:\n/viva <VivaMax_URL>",
            quote=True,
            disable_web_page_preview=True,
            parse_mode=None,
        )

    viva_url = message.text.split(None, 1)[1].strip()
    await message.reply_chat_action(ChatAction.TYPING)  # ✅ fixed here

    result = await get_vivamax_posters(viva_url)

    await message.reply_text(
        result,
        disable_web_page_preview=True,
        parse_mode=None  # ✅ prevents ENTITY_BOUNDS_INVALID
    )
