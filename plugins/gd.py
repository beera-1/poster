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

# ========================= GOOGLE =========================

def clean_google_link(link):
    if not link:
        return None
    return re.sub(r"https://fastcdn-dl\.pages\.dev/\?url=", "", link)

def format_href(link):
    if not link:
        return "Not Found"
    return f'<a href="{link}">Link</a>'

def get_instantdl(gd_url):
    try:
        r = requests.get(gd_url, headers=HEADERS, timeout=15)
    except:
        return None
    return scan(r.text, r"https://instant\.busycdn\.cfd/[A-Za-z0-9:]+")

def get_google_from_instant(instant_url):
    if not instant_url:
        return None
    try:
        r = requests.get(instant_url, headers=HEADERS, allow_redirects=True, timeout=20)
    except:
        return None

    final = r.url
    if "video-downloads.googleusercontent.com" in final:
        return clean_google_link(final)

    if "fastcdn-dl.pages.dev" in final and "url=" in final:
        pure = final.split("url=")[-1]
        if "video-downloads.googleusercontent.com" in pure:
            return clean_google_link(pure)

    return None

# ========================= HELPERS =========================

def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.text, r.url
    except:
        return "", url

def scan(text, pattern):
    m = re.search(pattern, text)
    return m.group(0) if m else None

def try_zfile_fallback(final_url):
    file_id = final_url.split("/file/")[-1]
    folders = [
        "2870627993","8213224819","7017347792","5011320428",
        "5069651375","3279909168","9065812244","1234567890",
        "1111111111","8841111600"
    ]
    for folder in folders:
        html, _ = fetch_html(f"https://new7.gdflix.net/zfile/{folder}/{file_id}")
        found = scan(html, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
        if found:
            return found
    return None

# ========================= SCRAPER =========================

def scrape_gdflix(url):
    html, final_url = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = html

    instantdl = get_instantdl(url)
    google_video = get_google_from_instant(instantdl)

    pix = scan(text, r"https://pixeldrain\.dev/[^\"]+")
    if pix:
        pix = pix.replace("?embed", "")

    tg = (
        scan(text, r"https://filesgram\.site/\?start=[^\"']+") or
        scan(text, r"https://t\.me/gdflix[^\"]+")
    )

    cloud_raw = scan(text, r"https://fastcdn-dl\.pages\.dev/\?url=[^\"']+")
    cloud = urllib.parse.unquote(clean_google_link(cloud_raw)) if cloud_raw else None

    direct = scan(text, r"https://[^\"']+/zfile/[0-9]+/[A-Za-z0-9]+")
    zfile = None
    if direct:
        zhtml, _ = fetch_html(direct)
        zfile = scan(zhtml, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
    else:
        zfile = try_zfile_fallback(final_url)

    # -------- GOFILE (3 STEP) --------
    gf_final = None
    multiup = scan(text, r"https://new\d+\.gdflix\.net/realtime/multiup\.php\?upload=[A-Za-z0-9]+")
    if multiup:
        m1_html, _ = fetch_html(multiup)
        mirror = scan(m1_html, r"https://goflix\.sbs/en/mirror/[A-Za-z0-9]+")
        if mirror:
            m2_html, _ = fetch_html(mirror)
            gf_final = scan(m2_html, r"https://gofile\.io/d/[A-Za-z0-9]+")

    return {
        "title": soup.find("title").text.strip() if soup.find("title") else "Unknown",
        "size": scan(text, r"[\d\.]+\s*(GB|MB)") or "Unknown",
        "google": format_href(google_video),
        "cloud": format_href(cloud),
        "gofile": format_href(gf_final),
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
        return await message.reply("⚠️ Usage: /gd <link>")

    for url in links[:8]:
        msg = await message.reply("⏳ Processing...")
        start = time.time()
        data = scrape_gdflix(url)
        await msg.edit(format_bypass_message(data, message, round(time.time() - start, 2)))
