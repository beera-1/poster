# hub_plugin.py

import aiohttp
import re
import asyncio
import time
from urllib.parse import urljoin, quote, unquote
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

OFFICIAL_GROUPS = ["-1002311378229"]
OWNER_ID = 6390511215
UA = {"User-Agent": "Mozilla/5.0"}

# -----------------------
# Utilities
# -----------------------
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


# -----------------------
# Extractors / Resolvers
# -----------------------

def is_zipdisk(url: str, html: str) -> bool:
    u = url.lower()
    if any(x in u for x in ["workers.dev", "ddl", "cloudserver", "zipdisk"]):
        return True
    if re.search(r"ddl\d+\.", u):
        return True
    if re.search(r"/[0-9a-f]{40,}/", u):
        return True
    return False


async def resolve_trs(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url, headers=UA, allow_redirects=True, timeout=20) as r:
            return str(r.url)
    except:
        return url


async def resolve_10gbps_chain(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        async with session.get(url, headers=UA, allow_redirects=True, timeout=20) as r:
            final = str(r.url)
        m = re.search(r"link=([^&]+)", final)
        if m:
            return unquote(m.group(1))
    except:
        return None
    return None


def extract_trs_links(html: str):
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
    out = []
    for name, pattern in patterns.items():
        for link in re.findall(pattern, html):
            out.append((name, link))
    return out


# -----------------------
# PixelDrain folder & episodes extractor
# -----------------------
async def extract_pixeldrain_zip(session: aiohttp.ClientSession, url: str):
    try:
        fid = re.search(r"/u/([A-Za-z0-9]+)", url).group(1)
        api = f"https://pixeldrain.dev/api/file/{fid}/info/zip"

        async with session.get(api, headers=UA, timeout=20) as r:
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
        return f"{base}", eps
    except:
        return None, []


# -----------------------
# Main HubCloud extractor
# -----------------------
async def extract_hubcloud_links(session: aiohttp.ClientSession, url: str):
    url = normalize_hubcloud(url)

    try:
        async with session.get(url, headers=UA, timeout=20) as r:
            html = await r.text()
            final_url = str(r.url)
    except:
        return {"title": "Unknown", "size": "Unknown", "mirrors": []}

    # Title
    title_m = re.search(r"<title>(.*?)</title>", html, re.I)
    title = title_m.group(1).strip() if title_m else "Unknown"

    # Size
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
            final_trs = await resolve_trs(session, link)
            mirrors.append({"label": "TRS SERVER", "url": final_trs})
            continue

    # Expand pixeldrain
    expanded = []
    seen = set()
    for m in mirrors:
        if m["label"] != "PIXELDRAIN":
            if m["url"] not in seen:
                seen.add(m["url"])
                expanded.append(m)

    pd_unique = []
    for p in pix:
        if p not in pd_unique:
            pd_unique.append(p)

    for p in pd_unique:
        folder, eps = await extract_pixeldrain_zip(session, p)
        expanded.append({"label": "PIXELDRAIN FOLDER", "url": p})
        for ep in eps:
            lbl = ep["label"] if len(ep["label"]) <= 40 else ep["label"][:37] + "..."
            expanded.append({"label": lbl, "url": ep["url"]})

    # Deduplicate
    out = []
    seen = set()
    for x in expanded:
        if x["url"] not in seen:
            seen.add(x["url"])
            out.append(x)

    return {
        "title": title,
        "size": size,
        "mirrors": out
    }


# -----------------------
# Process multiple URLs
# -----------------------
async def process_links(urls: list):
    async with aiohttp.ClientSession() as session:
        results = []
        for u in urls:
            results.append(await extract_hubcloud_links(session, u))
        return results


# -----------------------
# Message Builder
# -----------------------
def build_message_text(data, elapsed, user):
    lines = []
    lines.append(f"┎ 📚 Title :- {data['title']}")
    lines.append("")
    lines.append(f"┠ 💾 Size :- {data['size']}")
    lines.append("")
    lines.append("┃")
    for m in data["mirrors"]:
        lines.append(f"┠ 🔗 {m['label']} :-  𝗟𝗜𝗡𝗞")
        lines.append("┃")
    if lines[-1] == "┃":
        lines.pop()
    lines.append("")
    lines.append("━━━━━━━✦✗✦━━━━━━━")
    lines.append("")
    lines.append(f"⏱️ Processed in {elapsed} seconds")
    lines.append("")
    lines.append(f"🙋 Requested By :- {user.first_name} (#ID_{user.id})")
    return "\n".join(lines)


def build_keyboard(mirrors):
    kb = []
    for m in mirrors:
        kb.append([InlineKeyboardButton(f"{m['label']} • 𝗟𝗜𝗡𝗞", url=m['url'])])
    return InlineKeyboardMarkup(kb)


# -----------------------
# /hub Command Handler
# -----------------------
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

        text = build_message_text(data, elapsed, message.from_user)
        kb = build_keyboard(data["mirrors"])

        try:
            await temp.edit_text(text, reply_markup=kb)
        except:
            await message.reply(text, reply_markup=kb)
