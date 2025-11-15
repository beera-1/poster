# gd_plugin.py
from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import re
import json
from bs4 import BeautifulSoup
import urllib.parse
import time

# ------------------------------------------------------
# 🔐 Allowed Groups
# ------------------------------------------------------
OFFICIAL_GROUPS = ["-1002311378229"]

# ------------------------------------------------------
# 🔥 Scraper + helpers (kept logic from your working code)
# ------------------------------------------------------
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
    """Return dict with extracted links/info (fast HTTP-only scrape)."""
    html, final_url = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = html

    pix = scan(text, r"https://pixeldrain\.dev/[^\"]+")
    if pix:
        pix = pix.replace("?embed", "")

    # TELEGRAM LINK DETECTION (filesgram or gdflix bot links or fallback t.me)
    tg_filesgram = scan(text, r"https://filesgram\.site/\?start=[A-Za-z0-9_]+&bot=gdflix[0-9_]*bot")
    tg_bot = scan(text, r"https://t\.me/gdflix[0-9_]*bot\?start=[A-Za-z0-9_=]+")
    tg_old = scan(text, r"https://t\.me/[A-Za-z0-9_/?=]+")
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

    # New instantdl format (googlevideo via fastcdn-dl)
    google = scan(text, r"https://fastcdn-dl\.pages\.dev/\?url=[^\"']+")
    if google:
        try:
            decoded = urllib.parse.unquote(google.split("url=")[1])
            result["cloud_resume"] = decoded
        except:
            result["cloud_resume"] = None

    # Old instantdl
    old_inst = scan(text, r"https://instant\.busycdn\.cfd/[A-Za-z0-9:]+")
    if old_inst:
        result["instantdl"] = old_inst

    # zfile direct check
    zfile_direct = scan(text, r"https://[^\"']+/zfile/[0-9]+/[A-Za-z0-9]+")
    if zfile_direct:
        zhtml, _ = fetch_html(zfile_direct)
        wz = scan(zhtml, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
        if wz:
            result["zfile"].append(wz)

    # fallback zfile
    if not result["zfile"]:
        fb = try_zfile_fallback(result["final_url"])
        if fb:
            result["zfile"].append(fb)

    # gofile validate
    validate = scan(text, r"https://validate\.mulitup\.workers\.dev/[A-Za-z0-9]+")
    if validate:
        try:
            vh = requests.get(validate, headers=HEADERS, timeout=10).text
            gf = scan(vh, r"https://gofile\.io/d/[A-Za-z0-9]+")
            result["gofile"] = gf
        except:
            result["gofile"] = None

    return result

# ------------------------------------------------------
# Formatting helper
# ------------------------------------------------------
def format_bypass_message(data, requester_name, requester_id, elapsed):
    # choose values and fallback text
    title = data.get("title", "Unknown")
    size = data.get("size", "Unknown")
    instant = data.get("instantdl") or "Not Found"
    cloud = data.get("cloud_resume") or "Not Found"
    tg = data.get("telegram") or "Not Found"
    gofile = data.get("gofile") or "Not Found"
    pix = data.get("pixeldrain") or "Not Found"
    drive = data.get("drivebot") or "Not Found"
    zfile = data.get("zfile")[0] if data.get("zfile") else "Not Found"

    # Build the pretty text (plain text to avoid parse_mode issues)
    text = (
        "✅ GDFlix Extracted Links:\n\n"
        "┎ 📚 Title:\n"
        f"┃ {title}\n\n"
        "┠ 💾 Size:\n"
        f"┃ {size}\n\n"
        "┠ 🔗 Instant DL:\n"
        f"┃ {instant}\n\n"
        "┠ 🔗 Cloud Download:\n"
        f"┃ {cloud}\n\n"
        "┠ 🔗 Telegram File:\n"
        f"┃ {tg}\n\n"
        "┠ 🔗 Gofile:\n"
        f"┃ {gofile}\n\n"
        "┠ 🔗 PixelDrain:\n"
        f"┃ {pix}\n\n"
        "┠ 🔗 Drivebot:\n"
        f"┃ {drive}\n\n"
        "┖ 🔗 ZFile:\n"
        f"  {zfile}\n\n"
        "━━━━━━━━✦✗✦━━━━━━━━\n\n"
        f"⏱️ Bypassed in {elapsed} seconds\n\n"
        f"🙋 Requested By :- {requester_name} (#ID_{requester_id})"
    )
    return text

# ------------------------------------------------------
# URL extraction helper (from text)
# ------------------------------------------------------
URL_RE = re.compile(r"https?://[^\s]+")

def extract_links_from_text(text):
    return URL_RE.findall(text or "")

# ------------------------------------------------------
# 🔥 PYROGRAM COMMAND — supports multiple links & reply
# ------------------------------------------------------
@Client.on_message(filters.command(["gd", "gdflix"]))
async def gdflix_command(client: Client, message: Message):

    # Authorization
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return

    # Gather links from command args
    parts = message.text.split()
    links = []

    # If command had arguments, extract URLs from them
    if len(parts) > 1:
        # join all args (so user can pass many links)
        args_text = " ".join(parts[1:])
        links = extract_links_from_text(args_text)

    # If no links and the message is a reply, extract from replied message
    if not links and message.reply_to_message:
        links = extract_links_from_text(message.reply_to_message.text or message.reply_to_message.caption or "")

    if not links:
        await message.reply("⚠️ Usage: `/gd <gdflix-link>`\nYou can pass multiple links (up to 8) or reply to a message that contains links.")
        return

    # Limit to max 8 links
    links = links[:8]

    requester_name = message.from_user.first_name or "Unknown"
    requester_id = message.from_user.id

    # Process each link and send a separate message
    for idx, url in enumerate(links, start=1):
        try:
            # Send temporary "processing" message
            processing_msg = await message.reply(f"⏳ ({idx}/{len(links)}) Bypassing: {url}")

            start = time.time()
            data = scrape_gdflix(url)
            elapsed = round(time.time() - start, 2)

            # For compatibility: if instantbot/instant server should be shown as zfile,
            # you said 'instantbot replace that to zfile' — map if needed:
            # (If your logic requires replacing some 'instantbot' field, add mapping here.)
            # Keep as-is unless you want specific renames.

            final_text = format_bypass_message(data, requester_name, requester_id, elapsed)

            # Edit the processing message into the final formatted result
            await processing_msg.edit(final_text)

        except Exception as e:
            # If something goes wrong for this link, notify and continue
            try:
                await message.reply(f"❌ Error processing {url}:\n{e}")
            except:
                pass
            continue

# End of file
