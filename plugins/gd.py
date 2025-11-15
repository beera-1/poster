from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import re
import json
from bs4 import BeautifulSoup
import urllib.parse
import time

# Allowed Groups
OFFICIAL_GROUPS = ["-1002311378229"]

HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.text, r.url
    except:
        return "", url

def scan(text, pattern):
    m = re.search(pattern, text)
    return m.group(0) if m else None

def scan_all(text, pattern):
    return re.findall(pattern, text)

def try_zfile_fallback(final_url):
    file_id = final_url.split("/file/")[-1]
    if not file_id:
        return None

    folders = [
        "2870627993","8213224819","7017347792","5011320428",
        "5069651375","3279909168","9065812244","1234567890","1111111111"
    ]

    for folder in folders:
        url = f"https://new7.gdflix.net/zfile/{folder}/{file_id}"
        html, _ = fetch_html(url)
        wz = scan(html, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
        if wz:
            return wz
    return None


def scrape_gdflix(url):
    html, final_url = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = html

    pix = scan(text, r"https://pixeldrain\.dev/[^\"]+")
    if pix:
        pix = pix.replace("?embed", "")

    # Telegram links
    tg_filesgram = scan(text, r"https://filesgram\.site/\?start=[A-Za-z0-9_]+&bot=gdflix[0-9_]*bot")
    tg_bot = scan(text, r"https://t\.me/gdflix[0-9_]*bot\?start=[A-Za-z0-9_=]+")
    tg_old = scan(text, r"https://t\.me/[A-Za-z0-9_/?=]+")

    telegram_link = tg_filesgram or tg_bot or tg_old

    result = {
        "title": soup.find("title").text.strip() if soup.find("title") else "Unknown",
        "size": scan(text, r"[\d\.]+\s*(GB|MB)") or "Unknown",
        "links": {
            "instantdl": None,
            "cloud_resume": None,
            "pixeldrain": pix,
            "telegram": telegram_link,
            "drivebot": scan(text, r"https://drivebot\.sbs/download\?id=[^\"]+"),
            "zfile": [],
            "gofile": None
        },
        "final_url": final_url
    }

    # InstantDL new
    google = scan(text, r"https://fastcdn-dl\.pages\.dev/\?url=[^\"']+")
    if google:
        encoded = google.split("url=")[1]
        result["links"]["cloud_resume"] = urllib.parse.unquote(encoded)

    # InstantDL old
    old = scan(text, r"https://instant\.busycdn\.cfd/[A-Za-z0-9:]+")
    if old:
        result["links"]["instantdl"] = old

    # ZFILE
    direct = scan(text, r"https://[^\"']+/zfile/[0-9]+/[A-Za-z0-9]+")
    if direct:
        html2, _ = fetch_html(direct)
        wz = scan(html2, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
        if wz:
            result["links"]["zfile"].append(wz)

    if not result["links"]["zfile"]:
        fb = try_zfile_fallback(final_url)
        if fb:
            result["links"]["zfile"].append(fb)

    # Gofile
    valid = scan(text, r"https://validate\.mulitup\.workers\.dev/[A-Za-z0-9]+")
    if valid:
        vh = requests.get(valid, headers=HEADERS).text
        result["links"]["gofile"] = scan(vh, r"https://gofile\.io/d/[A-Za-z0-9]+")

    return result


def esc(t):
    """Escape markdown_v2 characters"""
    if not t:
        return "Not Found"
    for ch in r"_*[]()~`>#+-=|{}.!" :
        t = t.replace(ch, f"\\{ch}")
    return t


@Client.on_message(filters.command(["gd", "gdflix"]))
async def gdflix_command(client: Client, message: Message):

    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in our official group.")

    parts = message.text.split()
    if len(parts) < 2:
        return await message.reply("⚠️ Usage: /gd <gdflix-url>")

    url = parts[1]

    start = time.time()
    await message.reply("⏳ Scraping GDFlix…")

    data = scrape_gdflix(url)
    t = data["title"]
    s = data["size"]
    L = data["links"]

    text = (
        "✅ *GDFlix Extracted Links:*\n\n"
        f"┎ *📚 Title:* {esc(t)}\n"
        f"┠ *💾 Size:* {esc(s)}\n"
        f"┠ *🔗 Instant DL:* [{ 'Click Here' if L['instantdl'] else 'Not Found' }]({esc(L['instantdl'])})\n"
        f"┠ *🔗 Cloud Download:* [{ 'Click Here' if L['cloud_resume'] else 'Not Found' }]({esc(L['cloud_resume'])})\n"
        f"┠ *🔗 Telegram File:* [{ 'Click Here' if L['telegram'] else 'Not Found' }]({esc(L['telegram'])})\n"
        f"┠ *🔗 GoFile:* [{ 'Click Here' if L['gofile'] else 'Not Found' }]({esc(L['gofile'])})\n"
        f"┠ *🔗 Pixeldrain:* [{ 'Click Here' if L['pixeldrain'] else 'Not Found' }]({esc(L['pixeldrain'])})\n"
        f"┠ *🔗 Drivebot:* [{ 'Click Here' if L['drivebot'] else 'Not Found' }]({esc(L['drivebot'])})\n"
        f"┖ *🔗 ZFile:* {esc(str(L['zfile']))}\n\n"
        "━━━━━━━✦✗✦━━━━━━━\n\n"
        f"⏱️ *Bypassed in:* `{round(time.time()-start,2)}s`\n\n"
        f"🙋 *Requested By:* {esc(message.from_user.first_name)}\n"
        f"(`ID_{message.from_user.id}`)"
    )

    await message.reply(text, parse_mode="markdown_v2")
