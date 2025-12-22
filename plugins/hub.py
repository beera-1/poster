# hub.py
from pyrogram import Client, filters
from pyrogram.types import Message
import requests, re, time
from bs4 import BeautifulSoup
from urllib.parse import unquote

OFFICIAL_GROUPS = ["-1002311378229"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/"
}

# ======================================================
# BASIC HELPERS
# ======================================================

def fetch_html(url, allow_redirects=True):
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=20,
            allow_redirects=allow_redirects
        )
        return r.text, r.url
    except:
        return "", url


def scan(text, pattern):
    m = re.search(pattern, text)
    return m.group(0) if m else None


def format_href(link):
    if not link:
        return "Not Found"
    return f'<a href="{link}">𝗟𝗜𝗡𝗞</a>'


# ======================================================
# GENERATOR FINDER
# ======================================================

def extract_generator(html):
    return scan(
        html,
        r"https://(gamerxyt\.com|carnewz\.site|cryptoinsights\.site)"
        r"/hubcloud\.php\?host=hubcloud[^\"' ]+"
    )


# ======================================================
# RESOLVERS
# ======================================================

def clean_google_link(url):
    if not url:
        return None
    return re.sub(r"https://cryptoinsights\.site/dl\.php\?link=", "", url)


def resolve_pixel_alt(url):
    try:
        r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=15)
        final = clean_google_link(r.url)
        if "googlevideo" in final or "googleusercontent" in final:
            return final
    except:
        pass
    return None


def resolve_10gbps(url):
    try:
        r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=15)
        m = re.search(r"link=([^&]+)", r.url)
        if m:
            return clean_google_link(unquote(m.group(1)))
    except:
        pass
    return None


def resolve_trs(url):
    try:
        r = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=15)
        if any(x in r.url for x in ["mega.nz", "mega.co", "userstorage.mega"]):
            return r.url
    except:
        pass
    return None


# ======================================================
# ZIP FILE EXTRACTOR
# ======================================================

def extract_zip_files(html):
    out = []

    main = scan(html, r"https://pixeldrain\.dev/u/[A-Za-z0-9]+")
    if main:
        out.append({
            "url": main,
            "name": scan(html, r'download="([^"]+)"') or "Zip Archive",
            "size": scan(html, r"[\d\.]+\s*(GB|MB|TB)") or "Unknown"
        })

    ep = re.findall(
        r"<a href='([^']+\.mkv)'[^>]*>(.*?)</a>\s*\((.*?)\)",
        html
    )
    for url, name, size in ep:
        out.append({"url": url, "name": name, "size": size})

    return out


# ======================================================
# MIRROR EXTRACTOR
# ======================================================

def extract_mirrors(html):
    mirrors = []
    google_video = None
    trs_direct = None

    RULES = [
        ("Pixel", r"https://pixeldrain\.dev/u/[A-Za-z0-9]+"),
        ("Pixel-Alt", r"https://pixel\.hubcdn\.fans/\?id=[^\"' ]+"),
        ("TRS", r"https://hubcloud\.foo/re/trs\.php[^\"' ]+"),
        ("10Gbps", r"https://gpdl\.hubcdn\.fans[^\"' ]+"),
    ]

    for label, rgx in RULES:
        for raw in re.findall(rgx, html):
            mirrors.append({"label": label, "url": raw})

            if label == "Pixel-Alt" and not google_video:
                google_video = resolve_pixel_alt(raw)

            if label == "10Gbps" and not google_video:
                google_video = resolve_10gbps(raw)

            if label == "TRS" and not trs_direct:
                trs_direct = resolve_trs(raw)

    # Dedup
    seen = set()
    mirrors = [m for m in mirrors if not (m["url"] in seen or seen.add(m["url"]))]

    return mirrors, google_video, trs_direct


# ======================================================
# MAIN SCRAPER (CRASH-PROOF)
# ======================================================

def scrape_hubcloud(url):
    html1, _ = fetch_html(url)

    generator = extract_generator(html1)

    # ❌ TOKEN NOT FOUND (SAFE STRUCTURE)
    if not generator:
        return {
            "title": "TOKEN NOT FOUND",
            "size": "Unknown",
            "google_video": None,
            "trs_direct": None,
            "zip_files": [],
            "mirrors": [],
            "final_url": url
        }

    html2, final_url = fetch_html(generator)
    soup = BeautifulSoup(html2, "html.parser")

    mirrors, google_video, trs_direct = extract_mirrors(html2)

    return {
        "title": soup.title.text.strip() if soup.title else "Unknown",
        "size": scan(html2, r"[\d\.]+\s*(GB|MB)") or "Unknown",
        "google_video": google_video,
        "trs_direct": trs_direct,
        "zip_files": extract_zip_files(html2),
        "mirrors": mirrors,
        "final_url": final_url
    }


# ======================================================
# FORMAT MESSAGE (NO KEYERROR)
# ======================================================

def format_message(d, message, elapsed):
    return (
        f"✅ <b>HubCloud Extracted</b>\n\n"
        f"┎ 📂 <b>Title</b>\n┃ {d.get('title')}\n\n"
        f"┠ 💾 <b>Size</b>\n┃ {d.get('size')}\n\n"
        f"┠ 🎬 <b>Google Video</b>\n┃ {format_href(d.get('google_video'))}\n\n"
        f"┠ ☁️ <b>TRS Direct</b>\n┃ {format_href(d.get('trs_direct'))}\n\n"
        f"┠ 📦 <b>Zip Files</b>\n┃ {len(d.get('zip_files', []))} Found\n\n"
        f"┠ 🔗 <b>Mirrors</b>\n┃ {len(d.get('mirrors', []))} Found\n\n"
        f"━━━━━━━━✦✗✦━━━━━━━━\n"
        f"⏱️ {elapsed}s | 👤 {message.from_user.mention}"
    )


# ======================================================
# COMMAND
# ======================================================

@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hubcloud_handler(client: Client, message: Message):

    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ Command restricted.")

    urls = re.findall(r"https?://[^\s]+", message.text)

    if not urls:
        return await message.reply("⚠️ Usage: /hub <hubcloud link>")

    for i, url in enumerate(urls[:5], 1):
        temp = await message.reply(f"⏳ ({i}/{len(urls)}) Processing...")
        start = time.time()

        data = scrape_hubcloud(url)
        elapsed = round(time.time() - start, 2)

        await temp.edit(format_message(data, message, elapsed))
