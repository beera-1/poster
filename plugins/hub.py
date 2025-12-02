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
def clean_url(url: str) -> str:
    try:
        return quote(url, safe=":/?=&%.-_A-Za-z0-9")
    except:
        return url or ""


def normalize_hubcloud(url: str) -> str:
    return re.sub(r"hubcloud\.(one|fyi)", "hubcloud.foo", url)


def extract_links(html: str):
    return re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)


def is_zipdisk(url: str, html: str) -> bool:
    u = (url or "").lower()
    if any(x in u for x in ["workers.dev", "ddl", "cloudserver", "zipdisk"]):
        return True
    if re.search(r"ddl\d+\.", u):
        return True
    if re.search(r"/[0-9a-f]{40,}/", u):
        return True
    return False


async def resolve_trs(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url, headers=UA, allow_redirects=True, timeout=25) as r:
            return str(r.url)
    except:
        return url


async def resolve_10gbps_chain(session: aiohttp.ClientSession, url: str) -> str | None:
    try:
        async with session.get(url, headers=UA, allow_redirects=True, timeout=25) as r:
            final = str(r.url)
        m = re.search(r"link=([^&]+)", final)
        return m.group(1) if m else None
    except:
        return None


def extract_trs_links(html: str):
    trs = set()
    trs.update(re.findall(r"trs\.php[^\"']+", html))
    xs = re.findall(r"trs\.php\?xs=[A-Za-z0-9=]+", html)
    for x in xs:
        trs.add("https://hubcloud.foo/re/" + x)
    return list(trs)


def extract_special_links(html: str):
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
async def extract_hubcloud_links(session: aiohttp.ClientSession, url: str):
    url = normalize_hubcloud(url)

    try:
        async with session.get(url, headers=UA, timeout=25) as r:
            html = await r.text()
    except:
        html = ""

    title = re.search(r"<title>(.*?)</title>", html, re.I)
    title = title.group(1).strip() if title else "Unknown"

    size = re.search(r"[\d\.]+\s*(GB|MB)", html, re.I)
    size = size.group(0) if size else "Unknown"

    hrefs = extract_links(html)
    hrefs.extend(extract_trs_links(html))

    special_links = extract_special_links(html)
    for _, v in special_links:
        hrefs.append(v)

    mirrors = []

    for link in hrefs:
        if not link or not link.startswith("http"):
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

    # dedupe preserving last label seen
    clean = {}
    for label, url in mirrors:
        clean[url] = label

    final_list = [{"label": v, "url": k} for k, v in clean.items()]

    return {
        "title": title,
        "size": size,
        "mirrors": final_list
    }


# ================================================================
# MULTI-LINK PROCESSOR (ensures function exists)
# ================================================================
async def process_links(urls: list):
    async with aiohttp.ClientSession() as session:
        out = []
        for url in urls:
            out.append(await extract_hubcloud_links(session, url))
        return out


# ================================================================
# FORMATTER (MarkdownV2 safe)
# ================================================================
_MDV2_ESCAPE_RE = re.compile(r'([_*\[\]()~`>#+\-=|{}.!])')


def md2_escape(text: str) -> str:
    if text is None:
        return ""
    # escape chars required by Telegram MarkdownV2
    return _MDV2_ESCAPE_RE.sub(r"\\\1", str(text))


def format_hub_message(d: dict, message: Message, elapsed: float) -> str:
    # Build message with MarkdownV2 and hide URLs behind label 𝗟𝗜𝗡𝗞
    text_lines = []
    text_lines.append(f"┎ 📚 *Title :-* {md2_escape(d.get('title','Unknown'))}")
    text_lines.append("")
    text_lines.append(f"┠ 💾 *Size :-* {md2_escape(d.get('size','Unknown'))}")
    text_lines.append("┃")

    for m in d.get("mirrors", []):
        label = md2_escape(m.get("label", "LINK"))
        url = m.get("url", "")
        # MarkdownV2 link: [label](url)
        link_md = f"[𝗟𝗜𝗡𝗞]({url})"
        text_lines.append(f"┠ 🔗 *{label}* :- {link_md}")
        text_lines.append("┃")

    # convert last ┠ to ┖
    # find last line that starts with the '┠' marker and replace
    for i in range(len(text_lines) - 1, -1, -1):
        if text_lines[i].startswith("┠"):
            text_lines[i] = text_lines[i].replace("┠", "┖", 1)
            break

    text_lines.append("")
    text_lines.append("━━━━━━━✦✗✦━━━━━━━")
    text_lines.append("")
    text_lines.append(f"⏱️ *Bypassed in {md2_escape(elapsed)} seconds*")

    user = message.from_user
    mention = f"[{md2_escape(user.first_name or 'User')}] (tg://user?id={user.id})"
    # Note: to make mention as link in MarkdownV2 we need ( ) around url; but parentheses also must be escaped inside md2_escape
    # We'll produce mention using tg://user link without escaping the parentheses around the url part.
    mention = f"[{md2_escape(user.first_name or 'User')}](tg://user?id={user.id})"

    text_lines.append("")
    text_lines.append(f"🙋 *Requested By :-* {mention} *(#ID_{user.id})*")

    return "\n".join(text_lines)


# ================================================================
# URL FINDER
# ================================================================
URL_RE = re.compile(r"https?://[^\s]+")


def extract_urls(text: str):
    return URL_RE.findall(text or "")


# ================================================================
# MAIN COMMAND HANDLER
# ================================================================
@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hub_handler(client: Client, message: Message):
    # owner bypasses group restriction
    if message.from_user.id != OWNER_ID:
        if str(message.chat.id) not in OFFICIAL_GROUPS:
            return await message.reply("❌ This command only works in our official group.")

    # extract urls from command text or reply
    urls = extract_urls(message.text)
    if not urls and message.reply_to_message:
        urls = extract_urls(message.reply_to_message.text or "")

    if not urls:
        return await message.reply("⚠️ Usage: /hub <url> or reply with link(s).")

    urls = urls[:8]

    for i, url in enumerate(urls, 1):
        temp = await message.reply_text(f"⏳ ({i}/{len(urls)}) Extracting: {url}")
        start = time.time()
        data = await process_links([url])
        elapsed = round(time.time() - start, 2)
        formatted = format_hub_message(data[0], message, elapsed)

        # send using MarkdownV2
        try:
            await temp.edit(formatted, parse_mode="markdown_v2")
        except Exception as e:
            # fallback: send plain text if MarkdownV2 fails
            await temp.edit("✅ Extracted (raw output)\n\n" + str(data[0]))
