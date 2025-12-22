import re
import asyncio
import aiohttp
from urllib.parse import unquote, quote

# -------------------------------------------------
# HEADERS (REAL BROWSER UA)
# -------------------------------------------------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/121.0.0.0 Safari/537.36"
}

# -------------------------------------------------
# SAFE ENCODE
# -------------------------------------------------
def clean(url: str) -> str:
    try:
        return quote(url, safe=":/?&=%")
    except:
        return url

# -------------------------------------------------
# EXTRACT GAMERXYT URL
# -------------------------------------------------
def extract_gamerxyt(html: str):
    m = re.search(
        r"https://gamerxyt\.com/hubcloud\.php\?host=hubcloud[^\"' ]+",
        html,
        re.I
    )
    return m.group(0) if m else None

# -------------------------------------------------
# EXTRACT SIZE
# -------------------------------------------------
def extract_size(html: str):
    m = re.search(r"File Size<i[^>]*>(.*?)</i>", html, re.I)
    return re.sub(r"<.*?>", "", m.group(1)).strip() if m else "Unknown"

# -------------------------------------------------
# EXTRACT TITLE
# -------------------------------------------------
def extract_title(html: str):
    m = re.search(r"<title>(.*?)</title>", html, re.I)
    return m.group(1).strip() if m else "Unknown"

# -------------------------------------------------
# CLEAN GOOGLE LINK
# -------------------------------------------------
def clean_google_link(url: str):
    return re.sub(r"^https://cryptoinsights\.site/dl\.php\?link=", "", url)

# -------------------------------------------------
# RESOLVE PIXEL-ALT
# -------------------------------------------------
async def resolve_pixel_alt(session, url):
    try:
        async with session.get(url, allow_redirects=True) as r:
            final = clean_google_link(str(r.url))
            if "googlevideo.com" in final or "googleusercontent" in final:
                return final
    except:
        pass
    return None

# -------------------------------------------------
# RESOLVE 10GBPS
# -------------------------------------------------
async def resolve_10gbps(session, url):
    try:
        async with session.get(url, allow_redirects=True) as r:
            m = re.search(r"link=([^&]+)", str(r.url))
            if m:
                return clean_google_link(unquote(m.group(1)))
    except:
        pass
    return None

# -------------------------------------------------
# RESOLVE TRS
# -------------------------------------------------
async def resolve_trs(session, url):
    try:
        async with session.get(url, allow_redirects=True) as r:
            final = str(r.url)
            if any(x in final for x in ["mega.nz", "mega.co", "userstorage.mega"]):
                return final
    except:
        pass
    return None

# -------------------------------------------------
# ZIP EXTRACTOR
# -------------------------------------------------
def extract_zip_files(html: str):
    files = []

    main = re.search(r"https://pixeldrain\.dev/u/[A-Za-z0-9]+", html)
    if main:
        name = re.search(r'download="([^"]+)"', html)
        size = re.search(r"\(([\d\.]+\s*(GB|MB|TB))\)", html)
        files.append({
            "url": main.group(0),
            "name": name.group(1) if name else "Zip Archive",
            "size": size.group(1) if size else "Unknown"
        })

    for m in re.finditer(r"<a href='([^']+\.mkv)'[^>]*>(.*?)</a>\s*\((.*?)\)", html, re.I):
        files.append({
            "url": m.group(1),
            "name": m.group(2),
            "size": m.group(3)
        })

    return files

# -------------------------------------------------
# MIRROR EXTRACTOR
# -------------------------------------------------
async def extract_mirrors(session, html, google_store, trs_store):
    mirrors = []

    RULES = [
        ("Pixel", r"https://pixeldrain\.dev/u/[A-Za-z0-9]+"),
        ("Pixel-Alt", r"https://pixel\.hubcdn\.fans/\?id=[^\"' ]+"),
        ("FSL-V2", r"https://cdn\.fsl-buckets\.life/[^\"' ]+"),
        ("FSL-V2", r"https://fsl\.gigabytes\.icu/[^\"' ]+"),
        ("FSL-R2", r"https://[A-Za-z0-9.-]+\.r2\.dev/[^\"' ]+"),
        ("Stranger-FSL", r"https://love\.stranger-things\.buzz/[^\"' ]+"),
        ("MegaServer", r"https://mega\.blockxpiracy\.net/cs/g\?[^\"' ]+"),
        ("TRS", r"https://hubcloud\.foo/re/trs\.php[^\"' ]+"),
        ("10Gbps", r"https://gpdl\.hubcdn\.fans[^\"' ]+"),
    ]

    for label, pattern in RULES:
        for raw in re.findall(pattern, html, re.I):
            link = clean(raw)

            if label == "Pixel-Alt":
                d = await resolve_pixel_alt(session, link)
                if d:
                    google_store["value"] = d

            if label == "10Gbps":
                d = await resolve_10gbps(session, link)
                if d:
                    google_store["value"] = d

            if label == "TRS":
                d = await resolve_trs(session, link)
                mirrors.append({"label": "TRS", "url": link})
                if d:
                    trs_store["value"] = d
                    mirrors.append({"label": "TRS-Direct", "url": d})
                continue

            mirrors.append({"label": label, "url": link})

    # Deduplicate
    seen = set()
    out = []
    for m in mirrors:
        if m["url"] not in seen:
            seen.add(m["url"])
            out.append(m)

    return out

# -------------------------------------------------
# MAIN SCRAPER
# -------------------------------------------------
async def scrape_hubcloud(url: str):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as r1:
            html1 = await r1.text()

        gamer_url = extract_gamerxyt(html1)
        if not gamer_url:
            return {
                "title": "TOKEN NOT FOUND",
                "size": "Unknown",
                "main_link": url,
                "mirrors": []
            }

        async with session.get(gamer_url, allow_redirects=True) as r2:
            final_html = await r2.text()

        google_store = {"value": None}
        trs_store = {"value": None}

        return {
            "title": extract_title(final_html),
            "size": extract_size(final_html),
            "main_link": url,
            "google_video": google_store["value"],
            "trs_direct": trs_store["value"],
            "zip_files": extract_zip_files(final_html),
            "mirrors": await extract_mirrors(session, final_html, google_store, trs_store)
        }

# -------------------------------------------------
# CLI TEST
# -------------------------------------------------
if __name__ == "__main__":
    test_url = "https://hubcloud.foo/drive/XXXXXXXX"
    print(asyncio.run(scrape_hubcloud(test_url)))
