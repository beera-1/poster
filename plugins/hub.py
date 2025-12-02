# hub_plugin.py

import re
import time
from urllib.parse import quote, unquote

from pyrogram import Client, filters
from pyrogram.types import Message

import aiohttp
from playwright.async_api import async_playwright

OFFICIAL_GROUPS = ["-1002311378229"]
OWNER_ID = 6390511215
UA = {"User-Agent": "Mozilla/5.0"}


# ================================
# UTILITIES
# ================================
def extract_urls(text: str):
    if not text:
        return []
    return re.findall(r"https?://[^\s]+", text)


def clean(url: str):
    try:
        return quote(url, safe=":/?=&%.-_A-Za-z0-9")
    except:
        return url


def normalize(url: str):
    return re.sub(r"hubcloud\.(one|fyi)", "hubcloud.foo", url)


# ================================
# PLAYWRIGHT LOADER (FIXED)
# ================================
async def fetch_html_js(url: str):
    """Full JS load → waits until HubCloud injects all mirrors."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-setuid-sandbox"
                ]
            )

            ctx = await browser.new_context(
                user_agent=UA["User-Agent"],
                viewport={"width": 1366, "height": 3000}
            )

            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded")

            # ⚠ HubCloud loads mirrors via JS after ~6–10 sec
            try:
                await page.wait_for_selector("a[href*='hubcdn']", timeout=10000)
            except:
                pass

            await page.wait_for_timeout(4000)

            html = await page.content()
            await browser.close()
            return html

    except Exception as e:
        print("PLAYWRIGHT ERROR:", e)
        return ""


# ================================
# MAIN HUBCLOUD SCRAPER (FIXED)
# ================================
async def scrape_hubcloud(url: str):
    url = normalize(url)

    html = await fetch_html_js(url)
    if not html:
        return {"title": "Unknown", "size": "Unknown", "mirrors": []}

    # TITLE
    t = re.search(r"<title>(.*?)</title>", html, re.I)
    title = t.group(1).strip() if t else "Unknown"

    # SIZE
    s = re.search(r"[\d\.]+\s*(GB|MB)", html)
    size = s.group(0) if s else "Unknown"

    # ALL LINKS
    links = set(re.findall(r'https?://[^\s"\'<>]+', html))

    mirrors = []

    for link in links:
        link = clean(link)

        if "gpdl.hubcdn" in link:
            mirrors.append({"label": "10GBPS", "url": link})

        elif "fsl-buckets" in link:
            mirrors.append({"label": "FSLV2", "url": link})

        elif ".r2.dev" in link:
            mirrors.append({"label": "FSLR2", "url": link})

        elif "pixel.hubcdn" in link:
            mirrors.append({"label": "PIXEL ALT", "url": link})

        elif "pixeldrain.dev/u" in link:
            mirrors.append({"label": "PIXELDRAIN", "url": link})

        elif "workers.dev" in link or "zipdisk" in link:
            mirrors.append({"label": "ZIPDISK", "url": link})

        elif "mega.blockxpiracy" in link:
            mirrors.append({"label": "MEGA", "url": link})

        elif "trs.php" in link:
            mirrors.append({"label": "TRS", "url": link})

    # REMOVE DUPLICATES
    final = []
    seen = set()
    for m in mirrors:
        if m["url"] not in seen:
            final.append(m)
            seen.add(m["url"])

    return {
        "title": title,
        "size": size,
        "mirrors": final
    }


# ================================
# MESSAGE BUILDER
# ================================
def build_message(data, elapsed, user):
    out = []
    out.append(f"┎ 📚 Title :- {data['title']}")
    out.append(f"┠ 💾 Size :- {data['size']}")
    out.append("┃")

    for m in data["mirrors"]:
        out.append(f"┠ 🔗 {m['label']} :- {m['url']}")
        out.append("┃")

    if out[-1] == "┃":
        out.pop()

    out.append("━━━━━━━✦✗✦━━━━━━━")
    out.append(f"⏱️ Processed in {elapsed} sec")
    out.append(f"🙋 Requested By :- {user.first_name} (#ID_{user.id})")

    return "\n".join(out)


# ================================
# COMMAND HANDLER
# ================================
@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hub_handler(client: Client, message: Message):

    if message.from_user.id != OWNER_ID:
        if str(message.chat.id) not in OFFICIAL_GROUPS:
            return await message.reply("❌ This command only works in our official group.")

    urls = extract_urls(message.text)

    if not urls and message.reply_to_message:
        txt = (
            message.reply_to_message.text
            or message.reply_to_message.caption
            or ""
        )
        urls = extract_urls(txt)

    if not urls:
        return await message.reply("⚠️ Usage: /hub <url> or reply with link(s).")

    urls = urls[:8]

    for i, u in enumerate(urls, 1):
        temp = await message.reply(f"⏳ ({i}/{len(urls)}) Extracting: {u}")

        start = time.time()
        data = await scrape_hubcloud(u)
        elapsed = round(time.time() - start, 2)

        msg = build_message(data, elapsed, message.from_user)

        if len(msg) <= 3800:
            await temp.edit(msg)
        else:
            await temp.delete()
            parts = [msg[i:i+3800] for i in range(0, len(msg), 3800)]
            for p in parts:
                await message.reply(p)
