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
        "2870627993","8213224819","7017347792","5011320428",
        "5069651375","3279909168","9065812244","1234567890","1111111111","8841111600"
    ]
    for folder in folders:
        zurl = f"https://new7.gdflix.net/zfile/{folder}/{file_id}"
        html, _ = fetch_html(zurl)
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

    tg_filesgram = scan(text, r"https://filesgram\.site/\?start=[A-Za-z0-9_]+&bot=gdflix[0-9_]*bot")
    tg_bot       = scan(text, r"https://t\.me/gdflix[0-9_]*bot\?start=[A-Za-z0-9_=]+")
    tg_old       = scan(text, r"https://t\.me/[A-Za-z0-9_/?=]+")

    telegram_link = tg_filesgram or tg_bot or tg_old

    result = {
        "title": soup.find("title").text.strip() if soup.find("title") else "Unknown",
        "size": scan(text, r"[\d\.]+\s*(GB|MB)") or "Unknown",
        "instantdl": scan(text, r"https://instant\.busycdn\.cfd/[A-Za-z0-9:]+"),
        "cloud_resume": None,
        "pixeldrain": pix,
        "telegram": telegram_link,
        "drivebot": scan(text, r"https://drivebot\.sbs/download\?id=[^\"]+"),
        "zfile": [],
        "gofile": None,
        "final_url": final_url
    }

    google = scan(text, r"https://fastcdn-dl\.pages\.dev/\?url=[^\"']+")
    if google:
        result["cloud_resume"] = urllib.parse.unquote(google.split("url=")[1])

    zfile_direct = scan(text, r"https://[^\"']+/zfile/[0-9]+/[A-Za-z0-9]+")
    if zfile_direct:
        zhtml, _ = fetch_html(zfile_direct)
        wz = scan(zhtml, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
        if wz:
            result["zfile"].append(wz)

    if not result["zfile"]:
        fb = try_zfile_fallback(final_url)
        if fb:
            result["zfile"].append(fb)

    validate = scan(text, r"https://validate\.mulitup\.workers\.dev/[A-Za-z0-9]+")
    if validate:
        vh = requests.get(validate, headers=HEADERS).text
        result["gofile"] = scan(vh, r"https://gofile\.io/d/[A-Za-z0-9]+")

    return result



# -------------------------------------------------------------------
# 🔥 PYROGRAM COMMAND — NO PARSE MODE USED (SAFE)
# -------------------------------------------------------------------
@Client.on_message(filters.command(["gd", "gdflix"]))
async def gdflix_command(client: Client, message: Message):

    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("⚠️ Usage: /gd <gdflix-link>")
        return

    url = parts[1]
    start = time.time()

    await message.reply("⏳ Scraping GDFlix…")

    data = scrape_gdflix(url)

    # Extract values
    title = data["title"]
    size = data["size"]
    instantdl = data["instantdl"] or "Not Found"
    cloud = data["cloud_resume"] or "Not Found"
    tg = data["telegram"] or "Not Found"
    gofile = data["gofile"] or "Not Found"
    pix = data["pixeldrain"] or "Not Found"
    drive = data["drivebot"] or "Not Found"
    zfile = data["zfile"][0] if data["zfile"] else "Not Found"

    # User info
    user = message.from_user.first_name
    uid = message.from_user.id

    end = round(time.time() - start, 2)

    # -------------------------------------------------------------------
    # FINAL TEXT (NO MARKDOWN/HTML → 100% SAFE)
    # -------------------------------------------------------------------
    text = f"""
✅ GDFlix Extracted Links:

┎ 📚 Title:
┃ {title}

┠ 💾 Size:
┃ {size}

┠ 🔗 Instant DL:
┃ {instantdl}

┠ 🔗 Cloud Download:
┃ {cloud}

┠ 🔗 Telegram File:
┃ {tg}

┠ 🔗 GoFile:
┃ {gofile}

┠ 🔗 PixelDrain:
┃ {pix}

┠ 🔗 DriveBot:
┃ {drive}

┖ 🔗 ZFile:
  {zfile}

━━━━━━━━✦✗✦━━━━━━━━

⏱️ Bypassed in {end} seconds

🙋 Requested By: {user} (ID: {uid})
"""

    await message.reply(text)
