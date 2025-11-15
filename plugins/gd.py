from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import re
import json
from bs4 import BeautifulSoup
import urllib.parse
import time
import asyncio

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
        "5069651375","3279909168","9065812244","1234567890",
        "1111111111","8841111600"
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
    if pix: pix = pix.replace("?embed", "")

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
# 🔥 PYROGRAM COMMAND — FULL PROGRESS BAR + PERFECT FORMATTING
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

    # INITIAL PROGRESS MESSAGE
    progress_msg = await message.reply("Bypassing :- 0% 「▱▱▱▱▱▱▱▱▱▱」")

    # Animate progress
    for i in range(1, 11):
        bar = "▰" * i + "▱" * (10 - i)
        await asyncio.sleep(0.12)
        await progress_msg.edit(f"Bypassing :- {i*10}% 「{bar}」")

    start = time.time()

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

    # USER INFO
    user = message.from_user.first_name
    uid = message.from_user.id

    end = round(time.time() - start, 2)

    # FINAL MESSAGE — NO PARSE MODE, FULLY SAFE
    final_text = f"""
✅ 𝗚𝗗𝗙𝗹𝗶𝘅 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗟𝗶𝗻𝗸𝘀:

┎ 📚 𝗧𝗶𝘁𝗹𝗲:
┃ {title}

┠ 💾 𝗦𝗶𝘇𝗲:
┃ {size}

┠ 🔗 𝗜𝗻𝘀𝘁𝗮𝗻𝘁 𝗗𝗟:
┃ {instantdl}

┠ 🔗 𝗖𝗹𝗼𝘂𝗱 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱:
┃ {cloud}

┠ 🔗 𝗧𝗲𝗹𝗲𝗴𝗿𝗮𝗺 𝗙𝗶𝗹𝗲:
┃ {tg}

┠ 🔗 𝗚𝗼𝗙𝗶𝗹𝗲:
┃ {gofile}

┠ 🔗 𝗣𝗶𝘅𝗲𝗹𝗗𝗿𝗮𝗶𝗻:
┃ {pix}

┠ 🔗 𝗗𝗿𝗶𝘃𝗲𝗕𝗼𝘁:
┃ {drive}

┖ 🔗 𝗭𝗙𝗶𝗹𝗲:
  {zfile}

━━━━━━━━✦✗✦━━━━━━━━

⏱️ 𝗕𝘆𝗽𝗮𝘀𝘀𝗲𝗱 𝗶𝗻 {end} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀

🙋 **Requested By :-** {user} **(#ID_{uid})**
"""

    await progress_msg.edit(final_text)
