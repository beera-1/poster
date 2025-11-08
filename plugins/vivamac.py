import re
import asyncio
import aiohttp

# VivaMax poster types (known CDN patterns)
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

async def get_vivamax_posters(page_url):
    # Extract content ID and title slug
    match = re.search(r"/(movie|series)/([A-Za-z0-9]+)", page_url)
    if not match:
        return "❌ Invalid VivaMax URL!"

    content_id = match.group(2)

    # Title cleanup: if user knows the title (optional)
    # For now we’ll just mark title placeholder
    title_slug = "MOVIE"

    # Try each pattern
    async with aiohttp.ClientSession() as session:
        found_links = []
        for name, tag in POSTER_PATTERNS.items():
            test_url = BASE_URL.format(id=content_id, type=tag, title=title_slug)
            ok = await check_url(session, test_url)
            if ok:
                found_links.append((name, test_url))

    if not found_links:
        return f"😢 No public poster URLs found for ID `{content_id}`"

    result = [f"**VivaMax Posters:**"]
    for name, link in found_links:
        result.append(f"{name}: {link}")
    result.append(f"\nID: {content_id}")

    return "\n".join(result)

# Run standalone
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python vivamax_poster_finder.py <VivaMax_URL>")
        sys.exit(1)
    url = sys.argv[1]
    text = asyncio.run(get_vivamax_posters(url))
    print(text)
