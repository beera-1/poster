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


# ========================= INSTANTDL → GOOGLE LINK =========================

def get_instantdl_link(html):
    """Extract InstantDL link from GDFlix page"""
    return scan(html, r"https://instant\.busycdn\.cfd/[A-Za-z0-9:]+")    


def get_final_google_link(instant_url):
    """Follow redirects → return googleusercontent direct link"""
    if not instant_url:
        return None

    try:
        r = requests.get(instant_url, headers=HEADERS, allow_redirects=True, timeout=20)
    except:
        return None

    final = r.url

    # direct Google video link
    if "video-downloads.googleusercontent.com" in final:
        return final

    # sometimes final contains FastCDN wrapper
    if "fastcdn-dl.pages.dev" in final and "url=" in final:
        return final.split("url=")[-1]

    return None



# ========================= ZFILE FALLBACK =========================

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



# ========================= SCRAPER =========================
def scrape_gdflix(url):

    html, final_url = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = html

    # ----------- InstantDL → Google -----------
    instantdl = get_instantdl_link(text)
    google_video = get_final_google_link(instantdl)

    # PixelDrain
    pix = scan(text, r"https://pixeldrain\.dev/[^\"]+")
    if pix:
        pix = pix.replace("?embed", "")

    # Telegram
    tg1 = scan(text, r"https://filesgram\.site/\?start=[A-Za-z0-9_]+&bot=gdflix[0-9_]*bot")
    tg2 = scan(text, r"https://t\.me/gdflix[0-9_]*bot\?start=[A-Za-z0-9_=]+")
    tg3 = scan(text, r"https://t\.me/[A-Za-z0-9_/?=]+")
    telegram_link = tg1 or tg2 or tg3

    data = {
        "title": soup.find("title").text.strip() if soup.find("title") else "Unknown",
        "size": scan(text, r"[\d\.]+\s*(GB|MB)") or "Unknown",

        # REPLACED — show Google link instead of InstantDL
        "instantdl": google_video or "Not Found",

        "cloud_resume": None,
        "pixeldrain": pix,
        "telegram": telegram_link,
        "drivebot": scan(text, r"https://drivebot\.sbs/download\?id=[^\"]+"),
        "zfile": [],
        "gofile": None,
        "final_url": final_url
    }

    # Cloud Download
    fast = scan(text, r"https://fastcdn-dl\.pages\.dev/\?url=[^\"']+")
    if fast:
        data["cloud_resume"] = urllib.parse.unquote(fast.split("url=")[1])

    # Zfile
    direct = scan(text, r"https://[^\"']+/zfile/[0-9]+/[A-Za-z0-9]+")
    if direct:
        zhtml, _ = fetch_html(direct)
        found = scan(zhtml, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
        if found:
            data["zfile"].append(found)

    if not data["zfile"]:
        fb = try_zfile_fallback(final_url)
        if fb:
            data["zfile"].append(fb)

    # GoFile
    validate = scan(text, r"https://validate\.mulitup\.workers\.dev/[A-Za-z0-9]+")
    if validate:
        try:
            vh = requests.get(validate, headers=HEADERS).text
            gf = scan(vh, r"https://gofile\.io/d/[A-Za-z0-9]+")
            data["gofile"] = gf
        except:
            pass

    return data



# ========================= FORMAT MESSAGE =========================

def format_bypass_message(d, name, uid, elapsed):
    text = (
        f"✅ **GDFlix Extracted Links:**\n\n"

        f"┎ 📚 **Title:**\n"
        f"┃ {d['title']}\n\n"

        f"┠ 💾 **Size:**\n"
        f"┃ {d['size']}\n\n"

        f"┠ 🔗 **Google Video Link:**\n"
        f"┃ {d['instantdl']}\n\n"

        f"┠ 🔗 **Cloud Download:**\n"
        f"┃ {d['cloud_resume'] or 'Not Found'}\n\n"

        f"┠ 🔗 **Telegram File:**\n"
        f"┃ {d['telegram'] or 'Not Found'}\n\n"

        f"┠ 🔗 **GoFile:**\n"
        f"┃ {d['gofile'] or 'Not Found'}\n\n"

        f"┠ 🔗 **PixelDrain:**\n"
        f"┃ {d['pixeldrain'] or 'Not Found'}\n\n"

        f"┠ 🔗 **DriveBot:**\n"
        f"┃ {d['drivebot'] or 'Not Found'}\n\n"

        f"┖ 🔗 **ZFile:**\n"
        f"  {(d['zfile'][0] if d['zfile'] else 'Not Found')}\n\n"

        f"━━━━━━━━✦✗✦━━━━━━━━\n\n"
        f"⏱️ **Bypassed in {elapsed} seconds**\n\n"
        f"🙋 **Requested By :- {name} (#ID_{uid})**"
    )
    return text



# ========================= URL EXTRACTOR =========================

URL_RE = re.compile(r"https?://[^\s]+")

def extract_links_from_text(text):
    return URL_RE.findall(text or "")



# ========================= MAIN COMMAND =========================

@Client.on_message(filters.command(["gd", "gdflix"]))
async def gdflix_handler(client: Client, message: Message):

    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in our official group.")

    parts = message.text.split()
    links = extract_links_from_text(" ".join(parts[1:]))

    if not links and message.reply_to_message:
        links = extract_links_from_text(message.reply_to_message.text or "")

    if not links:
        return await message.reply("⚠️ Usage: /gd <link1> <link2> … OR reply to a message containing links.")

    links = links[:8]

    requester_name = message.from_user.first_name
    requester_id = message.from_user.id

    # Process 1-by-1
    for i, url in enumerate(links, 1):
        temp = await message.reply(f"⏳ ({i}/{len(links)}) Bypassing: {url}")

        start = time.time()
        data = scrape_gdflix(url)
        elapsed = round(time.time() - start, 2)

        formatted = format_bypass_message(data, requester_name, requester_id, elapsed)

        await temp.edit(formatted)
