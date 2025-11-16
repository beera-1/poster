# ========================= Ultra Fast GDFlix Scraper (aiohttp) =========================
from pyrogram import Client, filters
from pyrogram.types import Message

import aiohttp
import asyncio
import re
import time
from bs4 import BeautifulSoup
import urllib.parse

# ========================= SETTINGS =========================

OFFICIAL_GROUPS = ["-1002311378229"]

HEADERS = {"User-Agent": "Mozilla/5.0"}

URL_RE = re.compile(r"https?://[^\s]+")

# ========================= REGEX PATTERNS =========================

P_GOOGLE = re.compile(r"https://video-downloads\.googleusercontent\.com[^\"]+")
P_INSTANT = re.compile(r"https://instant\.busycdn\.cfd/[A-Za-z0-9:]+")
P_PIX = re.compile(r"https://pixeldrain\.dev/[^\"]+")
P_TG = re.compile(r"https://t\.me/[A-Za-z0-9_/?=]+")
P_ZFILE = re.compile(r"https://[^\"']+/zfile/[0-9]+/[A-Za-z0-9]+")
P_WORKER = re.compile(r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")
P_FASTCDN = re.compile(r"https://fastcdn-dl\.pages\.dev/\?url=[^\"]+")
P_VALIDATE = re.compile(r"https://validate\.mulitup\.workers\.dev/[A-Za-z0-9]+")
P_SIZE = re.compile(r"[\d\.]+\s*(GB|MB)")
P_DRIVEBOT = re.compile(r"https://drivebot\.sbs/download\?id=[^\"]+")

Z_FOLDERS = [
 "2870627993","8213224819","7017347792","5011320428",
 "5069651375","3279909168","9065812244","1234567890",
 "1111111111","8841111600"
]

# ========================= HELPERS =========================

async def fetch(session: aiohttp.ClientSession, url: str, timeout=15):
    try:
        async with session.get(url, timeout=timeout) as resp:
            text = await resp.text()
            return text, str(resp.url)
    except:
        return "", url


# ========================= GOOGLE EXTRACTOR =========================

async def get_google(html, session):
    g = P_GOOGLE.search(html)
    if g:
        return g.group(0)

    instant = P_INSTANT.search(html)
    if not instant:
        return None

    try:
        _, final = await fetch(session, instant.group(0))
        if "video-downloads.googleusercontent.com" in final:
            return final
        if "url=" in final:
            pure = final.split("url=")[-1]
            if "video-downloads.googleusercontent.com" in pure:
                return pure
    except:
        pass

    return None


# ========================= ZFILE EXTRACTOR =========================

async def get_zfile(html, session, final_url):

    direct = P_ZFILE.search(html)
    if direct:
        body, _ = await fetch(session, direct.group(0))
        w = P_WORKER.search(body)
        if w:
            return w.group(0)

    file_id = final_url.split("/")[-1]

    for f in Z_FOLDERS:
        url = f"https://new7.gdflix.net/zfile/{f}/{file_id}"
        body, _ = await fetch(session, url)
        w = P_WORKER.search(body)
        if w:
            return w.group(0)

    return None


# ========================= GOFILE EXTRACTOR =========================

async def get_gofile(html, session):
    v = P_VALIDATE.search(html)
    if not v:
        return None
    try:
        body, _ = await fetch(session, v.group(0))
        gf = re.search(r"https://gofile\.io/d/[A-Za-z0-9]+", body)
        return gf.group(0) if gf else None
    except:
        return None


# ========================= MAIN SCRAPER =========================

async def scrape_gdflix(url, session):
    html, final_url = await fetch(session, url)
    soup = BeautifulSoup(html, "lxml")

    google, zfile, gofile = await asyncio.gather(
        get_google(html, session),
        get_zfile(html, session, final_url),
        get_gofile(html, session)
    )

    pix = P_PIX.search(html)
    tg = P_TG.search(html)
    fast = P_FASTCDN.search(html)
    drive = P_DRIVEBOT.search(html)

    cloud = None
    if fast:
        cloud = urllib.parse.unquote(fast.group(0).split("url=")[1])

    return {
        "title": soup.title.text.strip() if soup.title else "Unknown",
        "size": P_SIZE.search(html).group(0) if P_SIZE.search(html) else "Unknown",
        "instantdl": google or None,
        "cloud_resume": cloud,
        "telegram": tg.group(0) if tg else None,
        "pixeldrain": pix.group(0).replace("?embed", "") if pix else None,
        "drivebot": drive.group(0) if drive else None,
        "zfile": zfile,
        "gofile": gofile,
        "final_url": final_url
    }


# ========================= LINK STYLE (HIDDEN URLs) =========================

def make_link(url):
    if not url:
        return "Not Found"
    return f"<a href=\"{url}\">LINK</a>"


# ========================= FORMAT MESSAGE =========================

def format_msg(d, message, elapsed):
    return (
        f"✅ **GDFlix Extracted Links:**\n\n"

        f"┎ 📚 **Title:**\n"
        f"┃ {d['title']}\n\n"

        f"┠ 💾 **Size:**\n"
        f"┃ {d['size']}\n\n"

        f"┠ 🔗 **Google Video:**\n"
        f"┃ {make_link(d['instantdl'])}\n\n"

        f"┠ 🔗 **Cloud Download:**\n"
        f"┃ {make_link(d['cloud_resume'])}\n\n"

        f"┠ 🔗 **Telegram File:**\n"
        f"┃ {make_link(d['telegram'])}\n\n"

        f"┠ 🔗 **GoFile:**\n"
        f"┃ {make_link(d['gofile'])}\n\n"

        f"┠ 🔗 **PixelDrain:**\n"
        f"┃ {make_link(d['pixeldrain'])}\n\n"

        f"┠ 🔗 **DriveBot:**\n"
        f"┃ {make_link(d['drivebot'])}\n\n"

        f"┖ 🔗 **ZFile:**\n"
        f"  {make_link(d['zfile'])}\n\n"

        f"━━━━━━━━✦✗✦━━━━━━━━\n\n"
        f"⏱️ **Bypassed in:** {elapsed} sec\n"
        f"👤 **Requested By:** {message.from_user.mention}\n"
    )


# ========================= COMMAND HANDLER =========================

@Client.on_message(filters.command(["gd", "gdflix"]))
async def gd_handler(client, message: Message):
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in our official group.")

    text = message.text or ""
    links = URL_RE.findall(text)

    if not links and message.reply_to_message:
        links = URL_RE.findall(message.reply_to_message.text or "")

    if not links:
        return await message.reply("⚠️ Usage: /gd <link>")

    links = links[:8]

    async with aiohttp.ClientSession(headers=HEADERS) as session:

        tasks = [scrape_gdflix(url, session) for url in links]
        results = await asyncio.gather(*tasks)

        for i, d in enumerate(results, 1):
            elapsed = round((time.time() % 1000) / 100, 2)
            await message.reply(f"({i}/{len(results)})\n" + format_msg(d, message, elapsed))
