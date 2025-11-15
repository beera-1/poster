from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import re
import json
from bs4 import BeautifulSoup
import urllib.parse
import time

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


def try_zfile_fallback(final_url):
    file_id = final_url.split("/file/")[-1]

    folders = [
        "2870627993", "8213224819", "7017347792",
        "5011320428", "5069651375", "3279909168",
        "9065812244", "1234567890", "1111111111"
    ]

    for folder in folders:
        zurl = f"https://new7.gdflix.net/zfile/{folder}/{file_id}"
        html, _ = fetch_html(zurl)
        wz = scan(html, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
        if wz:
            return wz
    return None


# ----------------------------------------------------
# 🔥 MAIN SCRAPER
# ----------------------------------------------------
def scrape_gdflix(url):
    start = time.time()

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
        "title": soup.find("title").text.strip(),
        "size": scan(text, r"[\d\.]+\s*(GB|MB)") or "Unknown",
        "instantdl": None,
        "cloud_resume": None,
        "pixeldrain": pix,
        "telegram": telegram_link,
        "drivebot": scan(text, r"https://drivebot\.sbs/download\?id=[^\"]+"),
        "zfile": [],
        "gofile": None,
        "final_url": final_url,
        "time": round(time.time() - start, 2)
    }

    # InstantDL new
    google = scan(text, r"https://fastcdn-dl\.pages\.dev/\?url=[^\"']+")
    if google:
        encoded = google.split("url=")[1]
        result["cloud_resume"] = urllib.parse.unquote(encoded)

    # InstantDL old
    old_inst = scan(text, r"https://instant\.busycdn\.cfd/[A-Za-z0-9:]+")
    if old_inst:
        result["instantdl"] = old_inst

    # ZFILE
    zfile_direct = scan(text, r"https://[^\"']+/zfile/[0-9]+/[A-Za-z0-9]+")
    if zfile_direct:
        zhtml, _ = fetch_html(zfile_direct)
        wz = scan(zhtml, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
        if wz:
            result["zfile"].append(wz)

    if not result["zfile"]:
        fz = try_zfile_fallback(final_url)
        if fz:
            result["zfile"].append(fz)

    # Gofile
    validate = scan(text, r"https://validate\.mulitup\.workers\.dev/[A-Za-z0-9]+")
    if validate:
        vh = requests.get(validate, headers=HEADERS).text
        gf = scan(vh, r"https://gofile\.io/d/[A-Za-z0-9]+")
        result["gofile"] = gf

    return result


# ----------------------------------------------------
# 🔥 PYROGRAM COMMAND HANDLER
# ----------------------------------------------------
@Client.on_message(filters.command(["gd", "gdflix"]))
async def gdflix_command(client: Client, message: Message):

    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in the official group.")

    parts = message.text.split()
    if len(parts) < 2:
        return await message.reply("⚠️ Usage:\n/gd <gdflix link>")

    url = parts[1]
    await message.reply("⏳ Scraping GDFlix… Please wait.")

    data = scrape_gdflix(url)

    # ❗ HTML ESCAPE TITLE
    title = data['title'].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Format output (HTML)
    text = f"""
<b>✅ GDFlix Extracted Links:</b>

<b>📚 Title :</b> {title}

<b>💾 Size :</b> {data['size']}

<b>🔗 Instant DL :</b> {"<a href='" + data['instantdl'] + "'>Click Here</a>" if data['instantdl'] else "Not Found"}

<b>🔗 Cloud Resume :</b> {"<a href='" + data['cloud_resume'] + "'>Click Here</a>" if data['cloud_resume'] else "Not Found"}

<b>🔗 Telegram File :</b> {"<a href='" + data['telegram'] + "'>Click Here</a>" if data['telegram'] else "Not Found"}

<b>🔗 Gofile :</b> {"<a href='" + data['gofile'] + "'>Click Here</a>" if data['gofile'] else "Not Found"}

<b>🔗 Pixeldrain :</b> {"<a href='" + data['pixeldrain'] + "'>Click Here</a>" if data['pixeldrain'] else "Not Found"}

<b>🔗 Drivebot :</b> {"<a href='" + data['drivebot'] + "'>Click Here</a>" if data['drivebot'] else "Not Found"}

<b>🔗 ZFile Mirror :</b> {"<a href='" + data['zfile'][0] + "'>Click Here</a>" if data['zfile'] else "Not Found"}

━━━━━━━━━━━━━━

⏱️ Bypassed in <b>{data['time']}s</b>

🙋 Requested By: <b>{message.from_user.first_name}</b>
(#ID_{message.from_user.id})
"""

    await message.reply(text, parse_mode="html")
