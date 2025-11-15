from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import re
import json
import time
from bs4 import BeautifulSoup
import urllib.parse

# ------------------------------------------------------
# Allowed Groups
# ------------------------------------------------------
OFFICIAL_GROUPS = ["-1002311378229"]

# ------------------------------------------------------
# GDFlix Scraper (Your original scraper unchanged)
# ------------------------------------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

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
    if not file_id:
        return None

    folders = [
        "2870627993","8213224819","7017347792","5011320428",
        "5069651375","3279909168","9065812244","1234567890","1111111111"
    ]

    for folder in folders:
        zurl = f"https://new7.gdflix.net/zfile/{folder}/{file_id}"
        html, _ = fetch_html(zurl)
        w = scan(html, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/\S+")
        if w:
            return w
    return None


def scrape_gdflix(url):
    html, final_url = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = html

    pix = scan(text, r"https://pixeldrain\.dev/\S+")
    if pix:
        pix = pix.replace("?embed", "")

    tg_filesgram = scan(
        text,
        r"https://filesgram\.site/\?start=[A-Za-z0-9_]+&bot=gdflix[0-9_]*bot"
    )
    tg_bot = scan(
        text,
        r"https://t\.me/gdflix[0-9_]*bot\?start=[A-Za-z0-9_=]+"
    )
    tg_old = scan(
        text,
        r"https://t\.me/[A-Za-z0-9_/?=]+"
    )

    telegram_link = tg_filesgram or tg_bot or tg_old

    result = {
        "title": soup.find("title").text.strip(),
        "size": scan(text, r"[\d\.]+\s*(GB|MB)") or "Unknown",
        "links": {
            "instantdl": scan(text, r"https://instant\.busycdn\.cfd/\S+"),
            "cloud_resume": None,
            "telegram": telegram_link,
            "pixeldrain": pix,
            "drivebot": scan(text, r"https://drivebot\.sbs/download\?id=\S+"),
            "zfile": [],
            "gofile": None
        },
        "final_url": final_url
    }

    google = scan(text, r"https://fastcdn-dl\.pages\.dev/\?url=\S+")
    if google:
        result["links"]["cloud_resume"] = urllib.parse.unquote(google.split("url=")[1])

    zfile_direct = scan(text, r"https://\S+/zfile/[0-9]+/\S+")
    if zfile_direct:
        zhtml, _ = fetch_html(zfile_direct)
        worker = scan(zhtml, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/\S+")
        if worker:
            result["links"]["zfile"].append(worker)

    if not result["links"]["zfile"]:
        fb = try_zfile_fallback(final_url)
        if fb:
            result["links"]["zfile"].append(fb)

    validate = scan(text, r"https://validate\.mulitup\.workers\.dev/\S+")
    if validate:
        vhtml = requests.get(validate, headers=HEADERS).text
        result["links"]["gofile"] = scan(vhtml, r"https://gofile\.io/d/\S+")

    return result


# ------------------------------------------------------
# Pyrogram Command
# ------------------------------------------------------
@Client.on_message(filters.command(["gd", "gdflix"]))
async def gdflix_command(client: Client, message: Message):

    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in our official group.")

    parts = message.text.split()
    if len(parts) < 2:
        return await message.reply("⚠️ Usage:\n`/gd <gdflix link>`")

    url = parts[1]

    start = time.time()
    await message.reply("⏳ Scraping GDFlix…")

    data = scrape_gdflix(url)
    end = time.time()
    el = round(end - start, 2)

    l = data["links"]

    # SAFE FORMATTED OUTPUT (NO MARKDOWN ERRORS)
    text = (
f"✅ **GDFlix Extracted Links:**\n\n"
f"┎ **📚 Title :-**\n"
f"┃ {data['title']}\n\n"
f"┠ **💾 Size :-**\n"
f"┃ {data['size']}\n\n"
f"┠ **🔗 Instant DL :-** {'[Click Here](' + l['instantdl'] + ')' if l['instantdl'] else 'Not Found'}\n"
f"┠ **🔗 Cloud Download :-** {'[Click Here](' + l['cloud_resume'] + ')' if l['cloud_resume'] else 'Not Found'}\n"
f"┠ **🔗 Telegram File :-** {'[Click Here](' + l['telegram'] + ')' if l['telegram'] else 'Not Found'}\n"
f"┠ **🔗 Gofile :-** {'[Click Here](' + l['gofile'] + ')' if l['gofile'] else 'Not Found'}\n"
f"┠ **🔗 Pixeldrain :-** {'[Click Here](' + l['pixeldrain'] + ')' if l['pixeldrain'] else 'Not Found'}\n"
f"┠ **🔗 Drivebot :-** {'[Click Here](' + l['drivebot'] + ')' if l['drivebot'] else 'Not Found'}\n"
f"┖ **🔗 ZFile :-** "
f"{'[Click Here](' + l['zfile'][0] + ')' if l['zfile'] else 'Not Found'}\n\n"
f"━━━━━━━✦✗✦━━━━━━━\n\n"
f"⏱️ **Bypassed in:** {el} seconds\n\n"
f"🙋 **Requested By :-** {message.from_user.first_name}\n"
f"(#ID_{message.from_user.id})"
    )

    await message.reply(text, parse_mode="markdown")
