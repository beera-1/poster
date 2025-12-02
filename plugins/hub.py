# hub_plugin.py

import asyncio
import re
import time
import traceback
from urllib.parse import quote, unquote, urljoin

from pyrogram import Client, filters
from pyrogram.types import Message

import aiohttp
from playwright.async_api import async_playwright

OFFICIAL_GROUPS = ["-1002311378229"]
OWNER_ID = 6390511215
UA = {"User-Agent": "Mozilla/5.0"}

# ============================================
# UTILITIES
# ============================================
def clean_url(url: str) -> str:
    try:
        return quote(url, safe=":/?=&%.-_A-Za-z0-9")
    except:
        return url

def normalize_hubcloud(url: str) -> str:
    return re.sub(r"hubcloud\.(one|fyi)", "hubcloud.foo", url)

URL_RE = re.compile(r"https?://[^\s]+")

def extract_urls(text: str):
    return URL_RE.findall(text or "")

# ============================================
# DETECTORS
# ============================================
def is_zipdisk(url: str, html: str) -> bool:
    u = url.lower()
    if any(x in u for x in ["workers.dev", "zipdisk", "cloudserver", "ddl"]):
        return True
    if "zipdisk" in html.lower():
        return True
    if re.search(r"ddl\d+\.", u):
        return True
    if re.search(r"/[0-9a-f]{40,}/", u):
        return True
    return False

# ============================================
# AIOHTTP LINK RESOLVERS
# ============================================
async def resolve_trs(session, url: str):
    try:
        async with session.get(url, headers=UA, allow_redirects=True) as r:
            return str(r.url)
    except:
        return url

async def resolve_10gbps_chain(session, url: str):
    try:
        async with session.get(url, headers=UA, allow_redirects=True) as r:
            final = str(r.url)
        m = re.search(r"link=([^&]+)", final)
        if m:
            return unquote(m.group(1))
    except:
        pass
    return None

# ============================================
# PLAYWRIGHT → HTML FETCHER (FULL JS)
# ============================================
async def get_full_html(url: str) -> str:
    """Loads page fully with JS like Google Colab Playwright."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(user_agent=UA["User-Agent"])
            page = await context.new_page()

            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(1500)

            html = await page.content()

            await browser.close()
            return html
    except Exception as e:
        print("Playwright error:", e)
        return ""

# ============================================
# PARSE LINKS FROM HTML
# ============================================
def extract_links_from_html(html: str):
    return re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)

def extract_trs_links(html: str):
    trs = set()
    trs.update(re.findall(r'href=[\'"]([^\'"]*trs\.php[^\'"]*)[\'"]', html))
    trs.update(re.findall(r"(https?://[^\s\"']*trs\.php[^\s\"']*)", html))

    xs = re.findall(r"trs\.php\?xs=[A-Za-z0-9=]+", html)
    for x in xs:
        trs.add("https://hubcloud.foo/re/" + x)
    return list(trs)

def extract_special(html: str):
    patterns = {
        "FSLV2": r"https://cdn\.fsl-buckets\.life/[^\s\"']+",
        "FSLR2": r"https://[A-Za-z0-9\.\-]+\.r2\.dev/[^\s\"']+",
        "PIXEL ALT": r"https://pixel\.hubcdn\.fans/[^\s\"']+",
        "PIXELDRAIN": r"https://pixeldrain\.dev/u/[A-Za-z0-9]+",
        "ZIPDISK": r"https://[A-Za-z0-9\.\-]+workers\.dev/[^\s\"']+",
        "MEGA": r"https://mega\.blockxpiracy\.net/cs/[^\s\"']+",
    }
    found = []
    for name, rx in patterns.items():
        for v in re.findall(rx, html):
            found.append((name, v))
    return found

# ============================================
# PIXELDRAIN EPISODE FETCH
# ============================================
async def extract_pixeldrain_zip(session, url: str):
    try:
        fid = re.search(r"/u/([A-Za-z0-9]+)", url).group(1)
        api = f"https://pixeldrain.dev/api/file/{fid}/info/zip"
        async with session.get(api, headers=UA) as r:
            data = await r.json()

        base = f"https://pixeldrain.dev/u/{fid}"
        eps = []

        def walk(path, tree):
            for item in tree:
                if item["type"] == "file":
                    eps.append({
                        "label": path + item["name"],
                        "url": f"{base}/{quote(path + item['name'])}"
                    })
                else:
                    walk(path + item["name"] + "/", item["children"])

        walk("", data["children"])
        return base, eps

    except:
        return None, []

# ============================================
# MAIN SCRAPER (PLAYWRIGHT + AIOHTTP)
# ============================================
async def extract_hubcloud(url: str):
    url = normalize_hubcloud(url)

    html = await get_full_html(url)
    if not html:
        return {"title": "Unknown", "size": "Unknown", "mirrors": []}

    # Title
    title_m = re.search(r"<title>(.*?)</title>", html, re.I)
    title = title_m.group(1).strip() if title_m else "Unknown"

    # Size
    sm = re.search(r"[\d\.]+\s*(GB|MB)", html)
    size = sm.group(0) if sm else "Unknown"

    hrefs = extract_links_from_html(html)
    hrefs.extend(extract_trs_links(html))

    for _, v in extract_special(html):
        hrefs.append(v)

    mirrors = []
    pix = []

    async with aiohttp.ClientSession() as session:
        for link in hrefs:
            if not link.startswith("http"):
                continue
            link = clean_url(link)

            if is_zipdisk(link, html):
                mirrors.append({"label": "ZIPDISK", "url": link})
                continue

            if "pixeldrain.dev/u" in link:
                pix.append(link)
                mirrors.append({"label": "PIXELDRAIN", "url": link})
                continue

            if "fsl-buckets" in link:
                mirrors.append({"label": "FSLV2", "url": link})
                continue

            if "r2.dev" in link:
                mirrors.append({"label": "FSLR2", "url": link})
                continue

            if "pixel.hubcdn.fans" in link:
                mirrors.append({"label": "PIXEL ALT", "url": link})
                continue

            if "blockxpiracy" in link:
                mirrors.append({"label": "MEGA", "url": link})
                continue

            if "gpdl.hubcdn.fans" in link:
                mirrors.append({"label": "10GBPS", "url": link})
                direct = await resolve_10gbps_chain(session, link)
                if direct:
                    mirrors.append({"label": "10GBPS DIRECT", "url": direct})
                continue

            if "trs.php" in link:
                final = await resolve_trs(session, link)
                mirrors.append({"label": "TRS SERVER", "url": final})
                continue

        # Expand pixeldrain
        out = []
        seen = set()
        for m in mirrors:
            if m["label"] != "PIXELDRAIN":
                if m["url"] not in seen:
                    seen.add(m["url"])
                    out.append(m)

        pd_unique = list(set(pix))
        for p in pd_unique:
            folder, eps = await extract_pixeldrain_zip(session, p)
            out.append({"label": "PIXELDRAIN FOLDER", "url": p})
            for ep in eps:
                lbl = ep["label"] if len(ep["label"]) <= 40 else ep["label"][:37] + "..."
                out.append({"label": lbl, "url": ep["url"]})

    return {
        "title": title,
        "size": size,
        "mirrors": out
    }

# ============================================
# MESSAGE BUILDER
# ============================================
def build_message(data, elapsed, user):
    L = []
    L.append(f"┎ 📚 Title :- {data['title']}")
    L.append(f"┠ 💾 Size :- {data['size']}")
    L.append("┃")

    for m in data["mirrors"]:
        L.append(f"┠ 🔗 {m['label']} :- {m['url']}")
        L.append("┃")

    if L[-1] == "┃":
        L.pop()

    L.append("━━━━━━━✦✗✦━━━━━━━")
    L.append(f"⏱️ Processed in {elapsed} seconds")
    L.append(f"🙋 Requested By :- {user.first_name} (#ID_{user.id})")

    return "\n".join(L)

# ============================================
# PYROGRAM HANDLER
# ============================================
@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hub_handler(client: Client, message: Message):

    if message.from_user.id != OWNER_ID:
        if str(message.chat.id) not in OFFICIAL_GROUPS:
            return await message.reply("❌ This command only works in our official group.")

    urls = extract_urls(message.text)
    if not urls and message.reply_to_message:
        txt = message.reply_to_message.text or message.reply_to_message.caption or ""
        urls = extract_urls(txt)

    if not urls:
        return await message.reply("⚠️ Usage: /hub <url> or reply with link(s).")

    urls = urls[:8]

    for i, u in enumerate(urls, 1):
        temp = await message.reply(f"⏳ ({i}/{len(urls)}) Extracting: {u}")

        start = time.time()
        data = await extract_hubcloud(u)
        elapsed = round(time.time() - start, 2)

        final = build_message(data, elapsed, message.from_user)

        if len(final) <= 3800:
            await temp.edit(final)
        else:
            await temp.delete()
            parts = [final[i:i+3800] for i in range(0, len(final), 3800)]
            for p in parts:
                await message.reply(p)
