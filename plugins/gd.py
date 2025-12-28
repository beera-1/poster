# gd_plugin.py
from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import re
from bs4 import BeautifulSoup
import urllib.parse
import time

OFFICIAL_GROUPS = ["-1002311378229"]
HEADERS = {"User-Agent": "Mozilla/5.0"}

GD_API = "https://hub-fawn.vercel.app/api/bypaas/gdflix.php?url="

# ========================= HELPERS =========================

def format_href(link):
    if not link:
        return "Not Found"
    return f'<a href="{link}">Link</a>'

def scan(text, pattern):
    m = re.search(pattern, text)
    return m.group(0) if m else None

def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        return r.text, r.url
    except:
        return "", url

# ========================= API FETCH =========================

def fetch_from_api(gd_url):
    try:
        r = requests.get(GD_API + gd_url, timeout=15)
        j = r.json()
        if j.get("status") != "success":
            return None

        d = j["data"]
        return {
            "title": d.get("title", "Unknown"),
            "size": d.get("size", "Unknown"),
            "google": format_href(d.get("google")),
            "cloud": format_href(d.get("cloud")),
            "gofile": format_href(d.get("gofile")),
            "zfile": format_href(d.get("zfile")),
            "pixeldrain": format_href(d.get("pixeldrain")),
            "telegram": format_href(d.get("telegram")),
            "final_url": d.get("final_url")
        }
    except:
        return None

# ========================= SCRAPER (FALLBACK) =========================

def scrape_gdflix(url):
    html, final_url = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = html

    title = soup.find("title").text.strip() if soup.find("title") else "Unknown"
    size = scan(text, r"[\d\.]+\s*(GB|MB)") or "Unknown"

    google = scan(text, r"https://video-downloads\.googleusercontent\.com/[^\"]+")
    pix = scan(text, r"https://pixeldrain\.dev/[^\"]+")
    tg = scan(text, r"https://t\.me/gdflix[^\"]+")

    cloud_raw = scan(text, r"https://fastcdn-dl\.pages\.dev/\?url=[^\"]+")
    cloud = urllib.parse.unquote(cloud_raw.split("url=")[-1]) if cloud_raw else None

    zfile = scan(text, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")

    # GOFILE (API-like method)
    gf = None
    multiup = scan(text, r"https://new\d+\.gdflix\.net/realtime/multiup\.php\?upload=[A-Za-z0-9]+")
    if multiup:
        m1_html, _ = fetch_html(multiup)
        mirror = scan(m1_html, r"https://goflix\.sbs/en/mirror/[A-Za-z0-9]+")
        if mirror:
            m2_html, _ = fetch_html(mirror)
            gf = scan(m2_html, r"https://gofile\.io/d/[A-Za-z0-9]+")

    return {
        "title": title,
        "size": size,
        "google": format_href(google),
        "cloud": format_href(cloud),
        "gofile": format_href(gf),
        "zfile": format_href(zfile),
        "pixeldrain": format_href(pix),
        "telegram": format_href(tg),
        "final_url": final_url
    }

# ========================= OUTPUT FORMAT =========================

def format_bypass_message(d, message, elapsed):
    return (
        f"☰ {d['title']}\n\n"
        f"1. 📚 **Title :-** {d['title']}\n"
        f"┃\n"
        f"┠ 💾 **Size :-** {d['size']}\n"
        f"┃\n"
        f"┠ 📂 **Google Video :-** {d['google']}\n"
        f"┃\n"
        f"┠ 🗄 **Cloud Download :-** {d['cloud']}\n"
        f"┃\n"
        f"┠ ☁️ **GoFile :-** {d['gofile']}\n"
        f"┃\n"
        f"┠ ⚡️ **ZFile :-** {d['zfile']}\n"
        f"┃\n"
        f"┠ 🖼 **PixelDrain :-** {d['pixeldrain']}\n"
        f"┃\n"
        f"┖ 📥 **Telegram File :-** {d['telegram']}\n\n"
        f"⏱️ **Bypassed in {elapsed} sec**\n"
        f"<b>Requested By :</b> {message.from_user.mention}"
    )

# ========================= COMMAND =========================

URL_RE = re.compile(r"https?://[^\s]+")

@Client.on_message(filters.command(["gd", "gdflix"]))
async def gdflix_handler(client: Client, message: Message):

    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ Official group only.")

    links = URL_RE.findall(message.text or "")
    if not links and message.reply_to_message:
        links = URL_RE.findall(message.reply_to_message.text or "")

    if not links:
        return await message.reply("⚠️ Usage: /gd <gdflix link>")

    for url in links[:8]:
        msg = await message.reply("⏳ Processing...")
        start = time.time()

        # 🔥 API FIRST
        data = fetch_from_api(url)

        # ♻️ FALLBACK TO SCRAPER
        if not data:
            data = scrape_gdflix(url)

        await msg.edit(
            format_bypass_message(data, message, round(time.time() - start, 2))
        )
