from pyrogram import Client, filters
import re
import aiohttp

# VivaMax CDN patterns
POSTER_PATTERNS = {
    "Poster": "MAIN_HORIZ",
    "Portrait": "MAIN_VERT",
    "Cover": "WEBHERO",
    "Square": "HERO"
}

BASE_URL = "https://public.vivamax.net/images/{id}_KA_{type}_LM_{title}.ori.jpg"


async def check_url(session, url):
    try:
        async with session.head(url) as resp:
            return resp.status == 200
    except:
        return False


async def get_vivamax_posters(viva_url):
    match = re.search(r"/(movie|series)/([A-Za-z0-9]+)", viva_url)
    if not match:
        return None, "❌ Invalid VivaMax URL!"

    content_id = match.group(2)
    title_name = "MOVIE"  # fallback if we can’t detect the name

    async with aiohttp.ClientSession() as session:
        found = []
        for label, tag in POSTER_PATTERNS.items():
            test_url = BASE_URL.format(id=content_id, type=tag, title=title_name)
            ok = await check_url(session, test_url)
            if ok:
                found.append((label, test_url))

    if not found:
        return content_id, None

    result = [f"**VivaMax Posters:**"]
    for label, link in found:
        result.append(f"{label}: {link}")
    result.append(f"\nID: `{content_id}`")

    return content_id, "\n".join(result)


@Client.on_message(filters.command(["viva"]))
async def vivamax_poster_cmd(client, message):
    if len(message.command) < 2:
        return await message.reply_text("❗Usage:\n`/viva <VivaMax_URL>`")

    viva_url = message.text.split(None, 1)[1].strip()
    await message.reply_chat_action("typing")
    content_id, result = await get_vivamax_posters(viva_url)

    if not result:
        return await message.reply_text(f"😢 No public poster URLs found for `{content_id}`")

    await message.reply_text(result, disable_web_page_preview=True)
