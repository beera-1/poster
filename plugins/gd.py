# gd_plugin.py
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
    if not file_id:
        return None

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

    data = {
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
        data["cloud_resume"] = urllib.parse.unquote(google.split("url=")[1])

    zfile_direct = scan(text, r"https://[^\"']+/zfile/[0-9]+/[A-Za-z0-9]+")
    if zfile_direct:
        zhtml, _ = fetch_html(zfile_direct)
        wz = scan(zhtml, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
        if wz:
            data["zfile"].append(wz)

    if not data["zfile"]:
        fb = try_zfile_fallback(final_url)
        if fb:
            data["zfile"].append(fb)

    validate = scan(text, r"https://validate\.mulitup\.workers\.dev/[A-Za-z0-9]+")
    if validate:
        try:
            vh = requests.get(validate, headers=HEADERS, timeout=10).text
            gf = scan(vh, r"https://gofile\.io/d/[A-Za-z0-9]+")
            data["gofile"] = gf
        except:
            data["gofile"] = None

    return data


# ---------------------------------------------------------
# Format Final Message (bold user + ID like screenshot)
# ---------------------------------------------------------
def format_bypass_message(d, name, uid, elapsed):

    text = (
        "✅ GDFlix Extracted Links:\n\n"
        f"┎ 📚 Title:\n┃ {d['title']}\n\n"
        f"┠ 💾 Size:\n┃ {d['size']}\n\n"
        f"┠ 🔗 Instant DL:\n┃ {d['instantdl'] or 'Not Found'}\n\n"
        f"┠ 🔗 Cloud Download:\n┃ {d['cloud_resume'] or 'Not Found'}\n\n"
        f"┠ 🔗 Telegram File:\n┃ {d['telegram'] or 'Not Found'}\n\n"
        f"┠ 🔗 GoFile:\n┃ {d['gofile'] or 'Not Found'}\n\n"
        f"┠ 🔗 PixelDrain:\n┃ {d['pixeldrain'] or 'Not Found'}\n\n"
        f"┠ 🔗 DriveBot:\n┃ {d['drivebot'] or 'Not Found'}\n\n"
        f"┖ 🔗 ZFile:\n  {(d['zfile'][0] if d['zfile'] else 'Not Found')}\n\n"
        "━━━━━━━━✦✗✦━━━━━━━━\n\n"
        f"⏱️ Bypassed in {elapsed} seconds\n\n"
        f"🙋 Requested By :- {name} (#ID_{uid})"
    )
    return text


# ---------------------------------------------------------
# Extract URLs from message or reply
# ---------------------------------------------------------
URL_RE = re.compile(r"https?://[^\s]+")

def extract_links_from_text(text):
    return URL_RE.findall(text or "")


# ---------------------------------------------------------
# COMMAND — Multiple links + reply-based
# ---------------------------------------------------------
@Client.on_message(filters.command(["gd", "gdflix"]))
async def gdflix_handler(client: Client, message: Message):

    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in our official group.")

    # extract from arguments
    parts = message.text.split()
    links = extract_links_from_text(" ".join(parts[1:]))

    # OR extract from replied message
    if not links and message.reply_to_message:
        links = extract_links_from_text(message.reply_to_message.text or "")

    if not links:
        return await message.reply(
            "⚠️ Usage: /gd <link1> <link2> ...\nOr reply to a message containing links."
        )

    links = links[:8]  # max 8 links

    requester_name = message.from_user.first_name
    requester_id = message.from_user.id

    for i, url in enumerate(links, 1):

        temp = await message.reply(f"⏳ ({i}/{len(links)}) Bypassing: {url}")

        start = time.time()
        data = scrape_gdflix(url)
        elapsed = round(time.time() - start, 2)

        final_text = format_bypass_message(data, requester_name, requester_id, elapsed)

        await temp.edit(final_text)
