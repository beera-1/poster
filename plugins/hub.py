# hub_plugin.py

import aiohttp
import re
import time
from urllib.parse import quote, unquote, urljoin
from pyrogram import Client, filters
from pyrogram.types import Message

OFFICIAL_GROUPS = ["-1002311378229"]
OWNER_ID = 6390511215
UA = {"User-Agent": "Mozilla/5.0"}

# -----------------------------------------
# Utilities
# -----------------------------------------
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


def extract_links_from_html(html: str):
    return re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)


# -----------------------------------------
# Extractors / Resolvers
# -----------------------------------------
def is_zipdisk(url: str, html: str) -> bool:
    u = url.lower()
    if any(x in u for x in ["workers.dev", "ddl", "cloudserver", "zipdisk"]):
        return True
    if re.search(r"ddl\d+\.", u):
        return True
    if re.search(r"/[0-9a-f]{40,}/", u):
        return True
    return False


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


def extract_trs_links(html):
    trs = set()
    trs.update(re.findall(r'href=[\'"]([^\'"]*trs\.php[^\'"]*)[\'"]', html))
    trs.update(re.findall(r"(https?://[^\s\"']*trs\.php[^\s\"']*)", html))

    xs = re.findall(r"trs\.php\?xs=[A-Za-z0-9=]+", html)
    for x in xs:
        trs.add("https://hubcloud.foo/re/" + x)

    return list(trs)


def extract_special_links(html: str):
    patterns = {
        "FSLV2": r"https://cdn\.fsl-buckets\.life/[^\s\"']+",
        "FSLR2": r"https://[A-Za-z0-9\.\-]+\.r2\.dev/[^\s\"']+",
        "PIXEL ALT": r"https://pixel\.hubcdn\.fans/[^\s\"']+",
        "PIXELDRAIN": r"https://pixeldrain\.dev/u/[A-Za-z0-9]+",
        "ZIPDISK": r"https://[A-Za-z0-9\.\-]+workers\.dev/[^\s\"']+",
        "MEGA": r"https://mega\.blockxpiracy\.net/cs/[^\s\"']+",
    }
    found = []
    for name, pattern in patterns.items():
        for link in re.findall(pattern, html):
            found.append((name, link))
    return found


# -----------------------------------------
# PixelDrain Folder / Episode extractor
# -----------------------------------------
async def extract_pixeldrain_zip(session, url: str):
    try:
        fid = re.search(r"/u/([A-Za-z0-9]+)", url).group(1)
        api = f"https://pixeldrain.dev/api/file/{fid}/info/zip"

        async with session.get(api, headers=UA) as r:
            data = await r.json()

        eps = []
        base = f"https://pixeldrain.dev/u/{fid}"

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


# -----------------------------------------
# Main HubCloud scraper
# -----------------------------------------
async def extract_hubcloud_links(session, url: str):
    url = normalize_hubcloud(url)

    try:
        async with session.get(url, headers=UA) as r:
            html = await r.text()
    except:
        return {"title": "Unknown", "size": "Unknown", "mirrors": []}

    title = re.search(r"<title>(.*?)</title>", html, re.I)
    title = title.group(1).strip() if title else "Unknown"

    sm = re.search(r"[\d\.]+\s*(GB|MB)", html)
    size = sm.group(0) if sm else "Unknown"

    hrefs = extract_links_from_html(html)
    hrefs.extend(extract_trs_links(html))

    for _, link in extract_special_links(html):
        hrefs.append(link)

    mirrors = []
    pix = []

    for link in hrefs:
        if not link.startswith("http"):
            continue
        link = clean_url(link)

        if is_zipdisk(link, html):
            mirrors.append({"label": "ZIPDISK", "url": link}); continue
        if "pixeldrain.dev/u" in link:
            pix.append(link)
            mirrors.append({"label": "PIXELDRAIN", "url": link}); continue
        if "fsl-buckets" in link:
            mirrors.append({"label": "FSLV2", "url": link}); continue
        if "r2.dev" in link:
            mirrors.append({"label": "FSLR2", "url": link}); continue
        if "pixel.hubcdn.fans" in link:
            mirrors.append({"label": "PIXEL ALT", "url": link}); continue
        if "blockxpiracy" in link:
            mirrors.append({"label": "MEGA", "url": link}); continue
        if "gpdl.hubcdn.fans" in link:
            mirrors.append({"label": "10GBPS", "url": link})
            d = await resolve_10gbps_chain(session, link)
            if d:
                mirrors.append({"label": "10GBPS DIRECT", "url": d})
            continue
        if "trs.php" in link:
            final_trs = await resolve_trs(session, link)
            mirrors.append({"label": "TRS SERVER", "url": final_trs})
            continue

    # Expand PixelDrain
    out = []
    seen = set()

    for m in mirrors:
        if m["label"] != "PIXELDRAIN":
            if m["url"] not in seen:
                seen.add(m["url"])
                out.append(m)

    pix_unique = list(set(pix))

    for p in pix_unique:
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


# -----------------------------------------
# Multiple links processor
# -----------------------------------------
async def process_links(urls):
    async with aiohttp.ClientSession() as session:
        return [await extract_hubcloud_links(session, u) for u in urls]


# -----------------------------------------
# Build message (NO buttons)
# -----------------------------------------
def build_message(data, elapsed, user):
    lines = []
    lines.append(f"┎ 📚 Title :- {data['title']}")
    lines.append(f"┠ 💾 Size :- {data['size']}")
    lines.append("┃")

    for m in data["mirrors"]:
        lines.append(f"┠ 🔗 {m['label']} :- {m['url']}")
        lines.append("┃")

    if lines[-1] == "┃":
        lines.pop()

    lines.append("━━━━━━━✦✗✦━━━━━━━")
    lines.append(f"⏱️ Processed in {elapsed} seconds")
    lines.append(f"🙋 Requested By :- {user.first_name} (#ID_{user.id})")

    return "\n".join(lines)


# -----------------------------------------
# /hub Handler
# -----------------------------------------
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
        data = (await process_links([u]))[0]
        elapsed = round(time.time() - start, 2)

        final_text = build_message(data, elapsed, message.from_user)

        # Telegram 4096 char limit
        if len(final_text) <= 3800:
            await temp.edit(final_text)
        else:
            await temp.delete()
            parts = [final_text[i:i+3800] for i in range(0, len(final_text), 3800)]
            for part in parts:
                await message.reply(part)
