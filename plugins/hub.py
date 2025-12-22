# hubcloud_plugin.py
from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import re
from bs4 import BeautifulSoup
import time
import urllib.parse

OFFICIAL_GROUPS = ["-1002311378229"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Referer": "https://hubcloud.foo/",
}

# ==========================================================
# HELPERS
# ==========================================================

def fetch_html(url, allow_redirects=True):
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
            allow_redirects=allow_redirects
        )
        return r.text, r.url
    except:
        return "", url


def scan(text, pattern):
    m = re.search(pattern, text, re.I)
    return m.group(0) if m else None


def format_href(link):
    if not link:
        return "Not Found"
    return f'<a href="{link}">𝗟𝗜𝗡𝗞</a>'


# ==========================================================
# CLEAN GOOGLE LINK
# ==========================================================

def clean_google_link(link):
    if not link:
        return None
    return re.sub(
        r"https://cryptoinsights\.site/dl\.php\?link=",
        "",
        link
    )


# ==========================================================
# RESOLVERS
# ==========================================================

def resolve_pixel_alt(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        final = clean_google_link(r.url)
        if "googlevideo.com" in final or "googleusercontent.com" in final:
            return final
    except:
        pass
    return None


def resolve_10gbps(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        m = re.search(r"link=([^&]+)", r.url)
        if m:
            return clean_google_link(urllib.parse.unquote(m.group(1)))
    except:
        pass
    return None


def resolve_trs(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if any(x in r.url for x in ["mega.nz", "mega.co", "userstorage.mega"]):
            return r.url
    except:
        pass
    return None


# ==========================================================
# ZIP FILES
# ==========================================================

def extract_zip_files(html):
    files = []

    main = scan(html, r"https://pixeldrain\.dev/u/[A-Za-z0-9]+")
    if main:
        name = scan(html, r'download="([^"]+)"')
        size = scan(html, r"\(([\d\.]+\s*(GB|MB|TB))\)")
        files.append({
            "url": main,
            "name": name or "Zip Archive",
            "size": size or "Unknown"
        })

    for m in re.finditer(
        r"<a href='([^']+\.mkv)'[^>]*>(.*?)</a>\s*\((.*?)\)",
        html,
        re.I
    ):
        files.append({
            "url": m.group(1),
            "name": m.group(2),
            "size": m.group(3)
        })

    return files


# ==========================================================
# MIRRORS
# ==========================================================

def extract_mirrors(html):
    mirrors = []
    google_video = None
    trs_direct = None

    rules = [
        ("Pixel", r"https://pixeldrain\.dev/u/[A-Za-z0-9]+"),
        ("Pixel-Alt", r"https://pixel\.hubcdn\.fans/\?id=[^\"' ]+"),
        ("TRS", r"https://hubcloud\.foo/re/trs\.php[^\"' ]+"),
        ("10Gbps", r"https://gpdl\.hubcdn\.fans[^\"' ]+"),
    ]

    for label, pattern in rules:
        for raw in re.findall(pattern, html, re.I):
            link = raw

            if label == "Pixel-Alt":
                d = resolve_pixel_alt(link)
                if d:
                    google_video = d

            if label == "10Gbps":
                d = resolve_10gbps(link)
                if d:
                    google_video = d

            if label == "TRS":
                d = resolve_trs(link)
                mirrors.append({"label": "TRS", "url": link})
                if d:
                    trs_direct = d
                    mirrors.append({"label": "TRS-Direct", "url": d})
                continue

            mirrors.append({"label": label, "url": link})

    # Deduplicate
    seen = set()
    final = []
    for m in mirrors:
        if m["url"] not in seen:
            seen.add(m["url"])
            final.append(m)

    return final, google_video, trs_direct


# ==========================================================
# MAIN SCRAPER
# ==========================================================

def scrape_hubcloud(url):
    html1, _ = fetch_html(url)

    # Generator link (gamerxyt / carnewz / cryptoinsights)
    generator = scan(
        html1,
        r"https://(gamerxyt\.com|carnewz\.site|cryptoinsights\.site)"
        r"/hubcloud\.php\?host=hubcloud[^\"' ]+"
    )

    if not generator:
        return {
            "title": "TOKEN NOT FOUND",
            "size": "Unknown",
            "main_link": url,
            "mirrors": []
        }

    html2, final_url = fetch_html(generator)

    soup = BeautifulSoup(html2, "html.parser")

    mirrors, google_video, trs_direct = extract_mirrors(html2)

    return {
        "title": soup.title.text.strip() if soup.title else "Unknown",
        "size": scan(html2, r"[\d\.]+\s*(GB|MB)") or "Unknown",
        "google_video": format_href(google_video),
        "trs_direct": format_href(trs_direct),
        "zip_files": extract_zip_files(html2),
        "mirrors": mirrors,
        "final_url": final_url
    }


# ==========================================================
# FORMAT MESSAGE
# ==========================================================

def format_message(d, message, elapsed):
    text = (
        f"✅ <b>HubCloud Extracted</b>\n\n"
        f"┎ 📁 <b>Title</b>\n┃ {d['title']}\n\n"
        f"┠ 💾 <b>Size</b>\n┃ {d['size']}\n\n"
        f"┠ 🎬 <b>Google Video</b>\n┃ {d['google_video']}\n\n"
        f"┠ ☁️ <b>TRS Direct</b>\n┃ {d['trs_direct']}\n\n"
        f"┠ 📦 <b>Zip Files</b>\n┃ {len(d['zip_files'])}\n\n"
        f"┠ 🔗 <b>Mirrors</b>\n"
    )

    for m in d["mirrors"]:
        text += f"┃ • {m['label']} → {format_href(m['url'])}\n"

    text += (
        f"\n━━━━━━━━✦✗✦━━━━━━━━\n"
        f"⏱️ Bypassed in {elapsed} sec\n"
        f"<b>Requested By:</b> {message.from_user.mention}"
    )
    return text


# ==========================================================
# COMMAND
# ==========================================================

URL_RE = re.compile(r"https?://[^\s]+")

def extract_links(text):
    return URL_RE.findall(text or "")


@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hubcloud_handler(client: Client, message: Message):

    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in our official group.")

    links = extract_links(message.text)

    if not links and message.reply_to_message:
        links = extract_links(message.reply_to_message.text or "")

    if not links:
        return await message.reply("⚠️ Usage: /hub <hubcloud link>")

    links = links[:5]

    for i, url in enumerate(links, 1):
        temp = await message.reply(f"⏳ ({i}/{len(links)}) Processing...")

        start = time.time()
        data = scrape_hubcloud(url)
        elapsed = round(time.time() - start, 2)

        await temp.edit(format_message(data, message, elapsed))
