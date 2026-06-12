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

# Synchronized with your updated Vercel backend deployment instance
GD_API = "https://hub-xi-hazel.vercel.app/api/bypaas/gdflix.php?url="

# ========================= HELPERS =========================

def format_href(link):
    if not link or "instant.busycdn" in str(link):
        return "❌ Not Found"
    return f'<a href="{link}">Link</a>'

def scan(text, pattern):
    m = re.search(pattern, text)
    return m.group(0) if m else None

def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS)
        return r.text, r.url
    except:
        return "", url

# ========================= API FETCH (WITH STRICT ADAPTIVE POLLING) =========================

def fetch_from_api(gd_url):
    # Triggers up to 3 retry loops to let async Vercel redirect tracers catch the google link
    for attempt in range(3):
        try:
            r = requests.get(GD_API + gd_url)
            j = r.json()
            
            # Reads the true/false success state from your Vercel JSON response
            if not j.get("success"):
                return None

            d = j["data"]
            downloads = d.get("downloads", [])

            google_link = None
            cloud_link = None
            gofile_link = None
            zfile_link = None
            pixeldrain_link = None
            telegram_link = None
            direct_mgt_link = None

            # Process layout mirrors from the JSON response list array
            for item in downloads:
                item_type = item.get("type")
                item_url = item.get("url")

                if item_type == "Instant DL":
                    # STRICT ASSIGNMENT: Look exclusively for the deep traced googleUrl
                    google_link = item.get("googleUrl")
                    
                    # Final emergency assignment if we run entirely out of backend execution retries
                    if not google_link and attempt == 2:
                        google_link = item_url
                        
                elif item_type == "Cloud Download (R2)":
                    cloud_link = item_url
                elif item_type == "Fast Cloud / Zipdisk":
                    zfile_link = item_url
                elif "PixelDrain" in item_type:
                    pixeldrain_link = item_url
                elif "Telegram" in item_type:
                    if "bot=" in item_url or not telegram_link:
                        telegram_link = item_url
                elif "GoFile" in item_type:
                    gofile_link = item_url
                elif "Direct Server (MGT)" in item_type:
                    direct_mgt_link = item_url

            # FIXED: If the google_link is missing OR it is still just the busycdn URL, force a wait loop
            if (not google_link or "busycdn" in str(google_link)) and attempt < 2:
                print(f"[Attempt {attempt + 1}] Deep redirect tracking in progress. Retrying in 3.0s...")
                time.sleep(3.0)
                continue

            return {
                "title": d.get("fileName", "Unknown File"),
                "size": "Check Link",  
                "google": format_href(google_link),
                "cloud": format_href(cloud_link),
                "gofile": format_href(gofile_link),
                "zfile": format_href(zfile_link),
                "pixeldrain": format_href(pixeldrain_link),
                "telegram": format_href(telegram_link),
                "direct_mgt": format_href(direct_mgt_link),
                "final_url": gd_url
            }
        except Exception as e:
            print(f"API Extraction trace exception on attempt {attempt + 1}: {e}")
            if attempt < 2:
                time.sleep(3.0)
            else:
                return None
    return None

# ========================= SCRAPER (FALLBACK ENGINE) =========================

def scrape_gdflix(url):
    html, final_url = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    text = html

    title = soup.find("title").text.strip() if soup.find("title") else "Unknown"
    if "GDFlix | " in title:
        title = title.replace("GDFlix | ", "")
        
    size = scan(text, r"[\d\.]+\s*(GB|MB)") or "Unknown"

    google = scan(text, r"https://video-downloads\.googleusercontent\.com/[^\"]+")
    pix = scan(text, r"https://pixeldrain\.dev/[^\"]+")
    tg = scan(text, r"https://t\.me/[^\s\"'<>]+")
    mgt = scan(text, r"https://[A-Za-z0-9\.\-]+\.indexserver\.xyz/[^\"]+")

    cloud_raw = scan(text, r"https://fastcdn-dl\.pages\.dev/\?url=[^\"]+")
    cloud = urllib.parse.unquote(cloud_raw.split("url=")[-1]) if cloud_raw else None

    zfile = scan(text, r"https://[A-Za-z0-9\.\-]+\.workers\.dev/[^\"]+")

    # Universal alignment mapping for fallback multiup/goflix string routing targets
    gf = scan(text, r"https://validate\.multiup2\.workers\.dev/[A-Za-z0-9]+") or scan(text, r"https://goflix\.sbs/en/mirror/[A-Za-z0-9]+")

    return {
        "title": title,
        "size": size,
        "google": format_href(google),
        "cloud": format_href(cloud),
        "gofile": format_href(gf),
        "zfile": format_href(zfile),
        "pixeldrain": format_href(pix),
        "telegram": format_href(tg),
        "direct_mgt": format_href(mgt),
        "final_url": final_url
    }

# ========================= OUTPUT FORMAT =========================

def format_bypass_message(d, message, elapsed):
    return (
        f"☰ **Bypassed File Data**\n\n"
        f"📚 **Title :-** `{d['title']}`\n"
        f"┃\n"
        f"┠ 💾 **Size :-** {d['size']}\n"
        f"┃\n"
        f"┠ 📂 **Google Video :-** {d['google']}\n"
        f"┃\n"
        f"┠ 🗄 **Cloud Download :-** {d['cloud']}\n"
        f"┃\n"
        f"┠ ☁️ **GoFile :-** {d['gofile']}\n"
        f"┃\n"
        f"┠ ⚡️ **ZFile :-** {d['zfile']}\n"
        f"┃\n"
        f"┠ 🖼 **PixelDrain :-** {d['pixeldrain']}\n"
        f"┃\n"
        f"┠ 📥 **Telegram File :-** {d['telegram']}\n"
        f"┃\n"
        f"┖ 🚀 **Direct Server [MGT] :-** {d['direct_mgt']}\n\n"
        f"⏱️ **Bypassed in {elapsed} sec**\n"
        f"<b>Requested By :</b> {message.from_user.mention}"
    )

# ========================= COMMAND =========================

URL_RE = re.compile(r"https?://[^\s]+")

@Client.on_message(filters.command(["gd", "gdflix"]))
async def gdflix_handler(client: Client, message: Message):

    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ Official group only.")

    links = URL_RE.findall(message.text or "")
    if not links and message.reply_to_message:
        links = URL_RE.findall(message.reply_to_message.text or "")

    if not links:
        return await message.reply("⚠️ Usage: /gd <gdflix link>")

    for url in links[:8]:
        msg = await message.reply("⏳ Processing extraction arrays...")
        start = time.time()

        # 🔥 Run API Parsing Flow 
        data = fetch_from_api(url)

        # ♻️ Local RegEx Fallback Parsing
        if not data:
            data = scrape_gdflix(url)

        await msg.edit(
            format_bypass_message(data, message, round(time.time() - start, 2)),
            disable_web_page_preview=True
        )
        
        # Spacing pause prevents crushing serverless runtimes sequentially
        if len(links) > 1:
            time.sleep(3.0)
