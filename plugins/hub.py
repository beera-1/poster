# hub_plugin.py
import nest_asyncio
nest_asyncio.apply()

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
    trs.update(re.findall(r"window\.location\.href\s*=\s*'([^']*trs\.php[^']*)'", html))
    trs.update(re.findall(r'href=[\'"]([^\'"]*trs\.php[^\'"]*)[\'"]', html))
    trs.update(re.findall(r"(https?://[^\s\"']*trs\.php[^\s\"']*)", html))
    xs_matches = re.findall(r"trs\.php\?xs=[A-Za-z0-9=]+", html)
    for x in xs_matches:
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
        for v in re.findall(pattern, html):
            found.append((name, v))
    return found


# PixelDrain JSON extractor (returns folder + episodes list)
async def extract_pixeldrain_zip(session: aiohttp.ClientSession, pixel_url: str):
    try:
        m = re.search(r"/u/([A-Za-z0-9]+)", pixel_url)
        if not m:
            return None, []
        fid = m.group(1)
        api = f"https://pixeldrain.dev/api/file/{fid}/info/zip"
        async with session.get(api, headers=UA, timeout=20) as r:
            if r.status != 200:
                return None, []
            data = await r.json()

        episodes = []
        base = f"https://pixeldrain.dev/u/{fid}"
        # walk children to collect files (simple DFS)
        def walk(path, tree):
            for item in tree:
                if item["type"] == "file":
                    episodes.append((path + item['name'], f"{base}/{quote(path + item['name'])}"))
                else:
                    walk(path + item["name"] + "/", item["children"])
        if "children" in data and isinstance(data["children"], list):
            walk("", data["children"])
        return (f"https://pixeldrain.dev/u/{fid}", episodes)
    except:
        return None, []


# -----------------------
# Main scrape for one HubCloud URL
# -----------------------
async def extract_hubcloud_links(session: aiohttp.ClientSession, target: str):
    target = normalize_hubcloud(target)
    try:
        async with session.get(target, headers=UA, timeout=20) as r:
            html = await r.text()
            final_url = str(r.url)
    except Exception:
        return {"title": "Unknown", "size": "Unknown", "mirrors": [], "main_link": target}

    title_m = re.search(r"<title>(.*?)</title>", html, re.I|re.S)
    title = title_m.group(1).strip() if title_m else "Unknown"

    size_m = re.search(r"File Size<i[^>]*>(.*?)</i>", html, re.I|re.S)
    if size_m:
        size = re.sub(r"<.*?>", "", size_m.group(1)).strip()
    else:
        sm = re.search(r"[\d\.]+\s*(GB|MB)", html, re.I)
        size = sm.group(0) if sm else "Unknown"

    # token-load second page if present
    token = re.search(r'href=[\'"]([^\'"]+token=[^\'"]+)[\'"]', html)
    if token and "token=" not in final_url:
        turl = token.group(1)
        if not turl.startswith("http"):
            turl = urljoin(target, turl)
        try:
            async with session.get(turl, headers=UA, timeout=20) as r2:
                html += await r2.text()
        except:
            pass

    hrefs = extract_links_from_html(html)

    # add some special matches
    m = re.search(r'(https://love\.stranger-things\.buzz[^"]+)', html)
    if m: hrefs.append(m.group(1))
    m = re.search(r'(https://gpdl\.hubcdn\.fans[^"]+)', html)
    if m: hrefs.append(m.group(1))
    m = re.search(r'https://pixeldrain\.dev/u/[A-Za-z0-9]+', html)
    if m: hrefs.append(m.group(0))

    # trs and special
    hrefs.extend(extract_trs_links(html))
    for _, v in extract_special_links(html):
        hrefs.append(v)

    mirrors = []
    # will collect Pixeldrain for later expansion
    pixeldrain_candidates = []

    for link in hrefs:
        if not link or not link.startswith("http"):
            continue
        link = clean_url(link)

        if is_zipdisk(link, html):
            mirrors.append({"label": "ZIPDISK", "url": link})
            continue
        if "pixeldrain.dev/u" in link:
            pixeldrain_candidates.append(link)
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
        if "stranger-things" in link:
            mirrors.append({"label": "FSL", "url": link})
            continue
        if "gpdl.hubcdn.fans" in link:
            mirrors.append({"label": "10GBPS", "url": link})
            # attempt direct google extraction
            try:
                direct = await resolve_10gbps_chain(session, link)
                if direct:
                    mirrors.append({"label": "10GBPS DIRECT", "url": direct})
            except:
                pass
            continue
        if "trs.php" in link:
            try:
                final_trs = await resolve_trs(session, link)
                mirrors.append({"label": "TRS SERVER", "url": final_trs})
            except:
                mirrors.append({"label": "TRS SERVER", "url": link})
            continue

    # expand pixel drain episodes (if any)
    expanded = []
    for m in mirrors:
        # copy non-pixeldrain here; pixeldrain will be expanded separately
        if m["label"] != "PIXELDRAIN":
            expanded.append(m)

    # find unique pixeldrain candidates
    unique_pd = []
    for p in pixeldrain_candidates:
        if p not in unique_pd:
            unique_pd.append(p)

    # use session to fetch pixeldrain JSON for each candidate
    for pd in unique_pd:
        try:
            folder_url, episodes = await extract_pixeldrain_zip(session, pd)
            # add folder link first (if not already)
            expanded.append({"label": "PIXELDRAIN FOLDER", "url": pd})
            # add episodes individually
            for name, ep_url in episodes:
                # label episodes as Episode: name (shorten if too long)
                label = name if len(name) <= 40 else name[:37] + "..."
                expanded.append({"label": f"EP: {label}", "url": ep_url})
        except:
            # fallback: keep the pd link only
            expanded.append({"label": "PIXELDRAIN", "url": pd})

    # dedupe preserving first appearance
    out = []
    seen = set()
    for m in expanded:
        if m["url"] not in seen:
            seen.add(m["url"])
            out.append(m)

    return {
        "title": title,
        "size": size,
        "main_link": target,
        "mirrors": out
    }


# -----------------------
# Process multiple links
# -----------------------
async def process_links(urls: list):
    async with aiohttp.ClientSession() as session:
        results = []
        for url in urls:
            try:
                results.append(await extract_hubcloud_links(session, url))
            except Exception:
                results.append({"title":"Unknown","size":"Unknown","main_link":url,"mirrors":[]})
        return results


# -----------------------
# Formatter & Keyboard builder
# -----------------------
def build_message_text(d: dict, elapsed: float, requester_first: str, requester_id: int) -> str:
    # Plain-text style (no parse mode needed). Buttons carry real links.
    text = []
    text.append("┎ 📚 Title :- " + d.get("title", "Unknown"))
    text.append("")
    text.append("┠ 💾 Size :- " + d.get("size", "Unknown"))
    text.append("┃")
    text.append("")
    for m in d.get("mirrors", []):
        # show label, link will be hidden in button
        text.append(f"┠ 🔗 {m['label']}  :-  LINK")
        text.append("┃")
    # replace last "┠" with "┖"
    # (we already used plain lines; this is cosmetic)
    # remove last trailing "┃"
    if text and text[-1] == "┃":
        text.pop()
    text.append("")
    text.append("━━━━━━━✦✗✦━━━━━━━")
    text.append("")
    text.append(f"⏱️ Processed in {elapsed} seconds")
    text.append("")
    text.append(f"🙋 Requested By :- {requester_first} (#ID_{requester_id})")
    return "\n".join(text)


def build_keyboard(mirrors: list):
    # Build an inline keyboard where each row is a single button labelled 𝗟𝗜𝗡𝗞
    # but we also include the mirror label in the button text optionally:
    buttons = []
    for m in mirrors:
        # try to keep button text compact: label → LINK
        btn_text = "𝗟𝗜𝗡𝗞"
        # Put mirror label as callback text fallback, but we only need visible label "LINK"
        buttons.append([InlineKeyboardButton(f"{m['label']}  •  {btn_text}", url=m['url'])])
    return InlineKeyboardMarkup(buttons) if buttons else None


# -----------------------
# Handler (/hub & /hubcloud)
# -----------------------
@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hub_handler(client: Client, message: Message):
    # owner bypass; owner can use anywhere
    if message.from_user.id != OWNER_ID:
        if str(message.chat.id) not in OFFICIAL_GROUPS:
            await message.reply_text("❌ This command only works in our official group.")
            return

    urls = extract_urls(message.text)
    if not urls and message.reply_to_message:
        # try to extract from replied-to message
        reply = message.reply_to_message
        # check message.text or caption (for media)
        src = getattr(reply, "text", None) or getattr(reply, "caption", None) or ""
        urls = extract_urls(src)

    if not urls:
        await message.reply_text("⚠️ Usage: /hub <url> or reply with link(s).")
        return

    urls = urls[:8]

    for i, url in enumerate(urls, 1):
        temp = await message.reply_text(f"⏳ ({i}/{len(urls)}) Extracting: {url}")

        start = time.time()
        data_list = await process_links([url])
        elapsed = round(time.time() - start, 2)

        data = data_list[0] if data_list else {"title":"Unknown","size":"Unknown","mirrors":[]}
        text = build_message_text(data, elapsed, message.from_user.first_name, message.from_user.id)
        kb = build_keyboard(data.get("mirrors", []))

        # edit the temp message with final text + keyboard (no parse_mode)
        try:
            await temp.edit_text(text, reply_markup=kb)
        except Exception:
            # fallback: send as a new message if editing fails
            await message.reply_text(text, reply_markup=kb)

# End of hub_plugin.py
