# hub_plugin.py
from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import asyncio
import re
from urllib.parse import quote
import time

OFFICIAL_GROUPS = ["-1002311378229"]
OWNER_ID = 6390511215
UA = {"User-Agent": "Mozilla/5.0"}


# ================================================================
# UTILITIES
# ================================================================
def clean_url(url):
    try:
        return quote(url, safe=":/?=&%.-_A-Za-z0-9")
    except:
        return url


def normalize_hubcloud(url):
    return re.sub(r"hubcloud\.(one|fyi)", "hubcloud.foo", url)


def extract_links(html):
    return re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)


def is_zipdisk(url, html):
    u = url.lower()
    if any(x in u for x in ["workers.dev", "ddl", "cloudserver", "zipdisk"]):
        return True
    if re.search(r"ddl\d+\.", u):
        return True
    if re.search(r"/[0-9a-f]{40,}/", u):
        return True
    return False


async def resolve_trs(session, url):
    try:
        async with session.get(url, headers=UA, allow_redirects=True) as r:
            return str(r.url)
    except:
        return url


async def resolve_10gbps_chain(session, url):
    try:
        async with session.get(url, headers=UA, allow_redirects=True) as r:
            final = str(r.url)
        m = re.search(r"link=([^&]+)", final)
        return m.group(1) if m else None
    except:
        return None


def extract_trs_links(html):
    trs = set()
    trs.update(re.findall(r"trs\.php[^\"']+", html))
    xs = re.findall(r"trs\.php\?xs=[A-Za-z0-9=]+", html)
    for x in xs:
        trs.add("https://hubcloud.foo/re/" + x)
    return list(trs)


def extract_special_links(html):
    patterns = {
        "fsl_v2": r"https://cdn\.fsl-buckets\.life/[^\s\"']+",
        "fsl_r2": r"https://[A-Za-z0-9\.\-]+\.r2\.dev/[^\s\"']+",
        "pixel_alt": r"https://pixel\.hubcdn\.fans/[^\s\"']+",
        "pixeldrain": r"https://pixeldrain\.dev/u/[A-Za-z0-9]+",
        "zipdisk": r"https://[A-Za-z0-9\.\-]+workers\.dev/[^\s\"']+",
        "megaserver": r"https://mega\.blockxpiracy\.net/cs/[^\s\"']+",
    }

    out = []
    for name, pattern in patterns.items():
        for v in re.findall(pattern, html):
            out.append((name, v))
    return out


# ================================================================
# MAIN EXTRACT FUNCTION
# ================================================================
async def extract_hubcloud_links(session, url):
    url = normalize_hubcloud(url)

    async with session.get(url, headers=UA) as r:
        html = await r.text()

    title = re.search(r"<title>(.*?)</title>", html)
    title = title.group(1) if title else "Unknown"

    size = re.search(r"[\d\.]+\s*(GB|MB)", html)
    size = size.group(0) if size else "Unknown"

    hrefs = extract_links(html)
    hrefs.extend(extract_trs_links(html))

    special_links = extract_special_links(html)
    for _, v in special_links:
        hrefs.append(v)

    mirrors = []

    for link in hrefs:
        if not link.startswith("http"):
            continue
        link = clean_url(link)

        if is_zipdisk(link, html):
            mirrors.append(("ZIPDISK", link))
            continue

        if "pixeldrain.dev/u" in link:
            mirrors.append(("PIXELDRAIN", link))
            continue

        if "fsl-buckets" in link:
            mirrors.append(("FSLV2", link))
            continue

        if "r2.dev" in link:
            mirrors.append(("FSLR2", link))
            continue

        if "pixel.hubcdn.fans" in link:
            mirrors.append(("PIXEL ALT", link))
            continue

        if "blockxpiracy" in link:
            mirrors.append(("MEGA", link))
            continue

        if "stranger-things" in link:
            mirrors.append(("FSL", link))
            continue

        if "gpdl.hubcdn.fans" in link:
            mirrors.append(("10GBPS", link))
            direct = await resolve_10gbps_chain(session, link)
            if direct:
                mirrors.append(("10GBPS DIRECT", direct))
            continue

        if "trs.php" in link:
            final = await resolve_trs(session, link)
            mirrors.append(("TRS SERVER", final))
            continue

    # ---------- Deduplicate ----------
    clean = {}
    for label, link in mirrors:
        clean[link] = label

    final_list = [{"label": lbl, "url": url} for url, lbl in clean.items()]

    return {
        "title": title,
        "size": size,
        "mirrors": final_list
    }


# ================================================================
# MULTI-LINK PROCESSOR
# ================================================================
async def process_links(urls):
    async with aiohttp.ClientSession() as session:
        out = []
        for url in urls:
            out.append(await extract_hubcloud_links(session, url))
        return out


# ================================================================
# MESSAGE FORMATTER (GDFlix Style)
# ================================================================
def format_hub_message(d, message, elapsed):

    text = (
        f"┎ 📚 <b>Title :-</b> {d['title']}\n\n"
        f"┠ 💾 <b>Size :-</b> {d['size']}\n"
        f"┃\n"
    )

    for m in d["mirrors"]:
        link_hidden = f'<a href="{m["url"]}">𝗟𝗜𝗡𝗞</a>'
        text += f"┠ 🔗 <b>{m['label']}</b> :- {link_hidden}\n┃\n"

    # Replace last ┠ with ┖
    lines = text.split("\n")
    for i in range(len(lines)-1, -1, -1):
        if lines[i].startswith("┠"):
            lines[i] = lines[i].replace("┠", "┖", 1)
            break
    text = "\n".join(lines)

    text += (
        "\n━━━━━━━✦✗✦━━━━━━━\n\n"
        f"⏱️ <b>Bypassed in {elapsed} seconds</b>\n\n"
        f"🙋 Requested By :- {message.from_user.mention} (#ID_{message.from_user.id})"
    )

    return text


# ================================================================
# URL FINDER
# ================================================================
URL_RE = re.compile(r"https?://[^\s]+")

def extract_urls(text):
    return URL_RE.findall(text or "")


# ================================================================
# MAIN COMMAND HANDLER
# ================================================================
@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hub_handler(client: Client, message: Message):

    if message.from_user.id != OWNER_ID:
        if str(message.chat.id) not in OFFICIAL_GROUPS:
            return await message.reply("❌ This command only works in our official group.")

    urls = extract_urls(message.text)

    if not urls and message.reply_to_message:
        urls = extract_urls(message.reply_to_message.text)

    if not urls:
        return await message.reply("⚠️ Usage: /hub <url> or reply with link(s).")

    urls = urls[:8]

    for i, url in enumerate(urls, 1):
        temp = await message.reply(f"⏳ ({i}/{len(urls)}) Extracting: {url}")

        start = time.time()
        data = await process_links([url])
        elapsed = round(time.time() - start, 2)

        formatted = format_hub_message(data[0], message, elapsed)
        await temp.edit(formatted, parse_mode="html")
