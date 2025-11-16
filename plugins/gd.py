# gd_plugin.py
from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import re
from bs4 import BeautifulSoup
import urllib.parse
import time
import asyncio
from pyrogram.errors import RPCError, FloodWait, MessageNotModified

OFFICIAL_GROUPS = ["-1002311378229"]
HEADERS = {"User-Agent": "Mozilla/5.0"}


# ========================= HELPERS =========================

def clean_google_link(link):
    if not link:
        return None
    return re.sub(r"https://fastcdn-dl\.pages\.dev/\?url=", "", link)


def format_href(link):
    if not link:
        return "Not Found"
    return f'<a href="{link}">𝗟𝗜𝗡𝗞</a>'


def scan(text, pattern):
    m = re.search(pattern, text)
    return m.group(0) if m else None


def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.text, r.url
    except:
        return "", url


# ========================= SCRAPER =========================

def get_instantdl(gd_url):
    try:
        r = requests.get(gd_url, headers=HEADERS, timeout=15)
    except:
        return None
    m = re.search(r"https://instant\.busycdn\.cfd/[A-Za-z0-9:]+", r.text)
    return m.group(0) if m else None


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


def try_zfile_fallback(final_url):
    file_id = final_url.split("/file/")[-1]

    folders = [
        "2870627993","8213224819","7017347792","5011320428",
        "5069651375","3279909168","9065812244","1234567890",
        "1111111111","8841111600"
    ]

    for folder in folders:
        url = f"https://new7.gdflix.net/zfile/{folder}/{file_id}"
        html, _ = fetch_html(url)
        found = scan(html, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
        if found:
            return found
    return None


def scrape_gdflix(url):
    html, final_url = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = html

    instantdl = get_instantdl(url)
    google_video = get_google_from_instant(instantdl)

    pix = scan(text, r"https://pixeldrain\.dev/[^\"]+")
    if pix:
        pix = pix.replace("?embed", "")

    telegram_link = (
        scan(text, r"https://filesgram\.site/\?start=[A-Za-z0-9_]+&bot=gdflix[0-9_]*bot")
        or scan(text, r"https://t\.me/gdflix[0-9_]*bot\?start=[A-Za-z0-9_=]+")
        or scan(text, r"https://t\.me/[A-Za-z0-9_/?=]+")
    )

    data = {
        "title": soup.find("title").text.strip() if soup.find("title") else "Unknown",
        "size": scan(text, r"[\d\.]+\s*(GB|MB)") or "Unknown",
        "instantdl": format_href(google_video),
    }

    # 🟢 CLOUD DOWNLOAD FIX (remove fastcdn wrapper)
    cloud_raw = scan(text, r"https://fastcdn-dl\.pages\.dev/\?url=[^\"']+")
    if cloud_raw:
        cleaned = re.sub(r"https://fastcdn-dl\.pages\.dev/\?url=", "", cloud_raw)
        cleaned = urllib.parse.unquote(cleaned)
        data["cloud_resume"] = format_href(cleaned)
    else:
        data["cloud_resume"] = None

    data.update({
        "pixeldrain": format_href(pix),
        "telegram": format_href(telegram_link),
        "drivebot": format_href(scan(text, r"https://drivebot\.sbs/download\?id=[^\"]+")),
        "zfile": [],
        "gofile": format_href(None),
        "final_url": final_url
    })

    # ZFILE
    direct = scan(text, r"https://[^\"']+/zfile/[0-9]+/[A-Za-z0-9]+")
    if direct:
        zhtml, _ = fetch_html(direct)
        found = scan(zhtml, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
        if found:
            data["zfile"].append(format_href(found))

    if not data["zfile"]:
        fb = try_zfile_fallback(final_url)
        if fb:
            data["zfile"].append(format_href(fb))

    # GOFILE
    validate = scan(text, r"https://validate\.mulitup\.workers\.dev/[A-Za-z0-9]+")
    if validate:
        try:
            vh = requests.get(validate, headers=HEADERS, timeout=10).text
            gf = scan(vh, r"https://gofile\.io/d/[A-Za-z0-9]+")
            data["gofile"] = format_href(gf)
        except:
            pass

    return data


# ========================= SAFE EDIT =========================

async def safe_edit(msg: Message, new_text: str):
    # Skip if same message
    old = getattr(msg, "text", None)
    if old == new_text:
        return

    try:
        await msg.edit(new_text, parse_mode="html", disable_web_page_preview=True)
    except MessageNotModified:
        return
    except FloodWait as e:
        await asyncio.sleep(e.x)
        await msg.edit(new_text, parse_mode="html", disable_web_page_preview=True)
    except Exception as e:
        print("EDIT ERROR:", e)
        return


# ========================= FORMATTER =========================

def format_bypass_message(d, message, elapsed):
    return (
        f"<b>✅ GDFlix Extracted Links:</b>\n\n"

        f"<b>📚 Title:</b>\n"
        f"{d['title']}\n\n"

        f"<b>💾 Size:</b>\n"
        f"{d['size']}\n\n"

        f"<b>🔗 Google Video:</b>\n"
        f"{d['instantdl']}\n\n"

        f"<b>🔗 Cloud Download:</b>\n"
        f"{d['cloud_resume'] or 'Not Found'}\n\n"

        f"<b>🔗 Telegram File:</b>\n"
        f"{d['telegram']}\n\n"

        f"<b>🔗 GoFile:</b>\n"
        f"{d['gofile']}\n\n"

        f"<b>🔗 PixelDrain:</b>\n"
        f"{d['pixeldrain']}\n\n"

        f"<b>🔗 DriveBot:</b>\n"
        f"{d['drivebot']}\n\n"

        f"<b>🔗 ZFile:</b>\n"
        f"{(d['zfile'][0] if d['zfile'] else 'Not Found')}\n\n"

        f"⏱️ <b>Bypassed in {elapsed} seconds</b>\n\n"
        f"<b>Requested By:</b> {message.from_user.mention}\n"
        f"<b>(#ID_{message.from_user.id})</b>"
    )


# ========================= URL EXTRACTOR =========================

URL_RE = re.compile(r"https?://[^\s]+")

def extract_links_from_text(text):
    return URL_RE.findall(text or "")


# ========================= MAIN COMMAND =========================

@Client.on_message(filters.command(["gd", "gdflix"]))
async def gdflix_handler(client: Client, message: Message):

    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply(
            "❌ This command only works in our official group.",
            disable_web_page_preview=True
        )

    parts = message.text.split()
    links = extract_links_from_text(" ".join(parts[1:]))

    if not links and message.reply_to_message:
        links = extract_links_from_text(message.reply_to_message.text or "")

    if not links:
        return await message.reply(
            "⚠️ Usage: /gd <link> OR reply to a message containing links.",
            disable_web_page_preview=True
        )

    links = links[:8]

    for i, url in enumerate(links, 1):
        temp = await message.reply(
            f"⏳ ({i}/{len(links)}) Bypassing: {url}",
            disable_web_page_preview=True
        )

        start = time.time()
        data = scrape_gdflix(url)
        elapsed = round(time.time() - start, 2)

        formatted = format_bypass_message(data, message, elapsed)

        await safe_edit(temp, formatted)
