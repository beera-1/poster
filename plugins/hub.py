# plugins/hub.py
from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import re
import asyncio
import time
from urllib.parse import urljoin, quote

OFFICIAL_GROUPS = ["-1002311378229"]
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Helper functions
def is_zipdisk(url, html):
    u = url.lower()
    if any(x in u for x in ["workers.dev", "ddl", "cloudserver", "zipdisk"]):
        return True
    if "zipdisk" in html.lower():
        return True
    if re.search(r"ddl\d+\.", u):
        return True
    if re.search(r"/[0-9a-f]{40,}/", u):
        return True
    if u.endswith(".zip") and "workers.dev" in u:
        return True
    return False

def normalize_hubcloud(url):
    return re.sub(r"hubcloud\.(one|fyi)", "hubcloud.foo", url)

def extract_links(html):
    return re.findall(r'href=[\'"]([^\'"]+)[\'"]', html)

def clean_url(url):
    try:
        return quote(url, safe=":/?=&%.-_A-Za-z0-9")
    except:
        return url

def extract_special_links(html):
    patterns = {
        "fsl_v2": r"https://cdn\.fsl-buckets\.life/[^\s\"']+\?token=[A-Za-z0-9_]+",
        "fsl_r2": r"https://[A-Za-z0-9\.\-]+\.r2\.dev/[^\s\"']+\?token=[A-Za-z0-9_]+",
        "pixel_alt": r"https://pixel\.hubcdn\.fans/\?id=[A-Za-z0-9:]+",
        "pixeldrain": r"https://pixeldrain\.dev/u/[A-Za-z0-9]+",
        "zipdisk": r"https://[A-Za-z0-9\.\-]+workers\.dev/[^\s\"']+\.zip",
        "megaserver": r"https://mega\.blockxpiracy\.net/cs/g\?[^\s\"']+",
    }
    found = []
    for name, pattern in patterns.items():
        for link in re.findall(pattern, html):
            found.append((name, link))
    return found

def extract_trs_links(html):
    trs = set()
    trs.update(re.findall(r"window\.location\.href\s*=\s*'([^']*trs\.php[^']*)'", html))
    trs.update(re.findall(r'href=[\'"]([^\'"]*trs\.php[^\'"]*)[\'"]', html))
    trs.update(re.findall(r"(https?://[^\s\"']*trs\.php[^\s\"']*)", html))
    xs_matches = re.findall(r"trs\.php\?xs=[A-Za-z0-9=]+", html)
    for x in xs_matches:
        trs.add("https://hubcloud.foo/re/" + x)
    return list(trs)

async def resolve_10gbps_chain(session, url):
    try:
        async with session.get(url, headers=HEADERS, allow_redirects=True) as r:
            final = str(r.url)
        m = re.search(r"link=([^&]+)", final)
        if m:
            return m.group(1)
    except:
        return None
    return None

async def resolve_trs(session, url):
    try:
        async with session.get(url, headers=HEADERS, allow_redirects=True) as r:
            return str(r.url)
    except:
        return url

async def extract_hubcloud_links(session, target):
    try:
        target = normalize_hubcloud(target)
        async with session.get(target, headers=HEADERS) as r:
            html = await r.text()
            final_url = str(r.url)
        
        title = re.search(r"<title>(.*?)</title>", html)
        title = title.group(1) if title else "Unknown"
        
        size_match = re.search(r"File Size<i[^>]*>(.*?)</i>", html)
        size = re.sub(r"<.*?>", "", size_match.group(1)).strip() if size_match else "Unknown"
        
        token = re.search(r'href=[\'"]([^\'"]+token=[^\'"]+)[\'"]', html)
        if token and "token=" not in final_url:
            turl = token.group(1)
            if not turl.startswith("http"):
                turl = urljoin(target, turl)
            async with session.get(turl) as r2:
                html += await r2.text()
        
        hrefs = extract_links(html)
        m = re.search(r'(https://love\.stranger-things\.buzz[^"]+)', html)
        if m: hrefs.append(m.group(1))
        m = re.search(r'(https://gpdl\.hubcdn\.fans[^"]+)', html)
        if m: hrefs.append(m.group(1))
        m = re.search(r'https://pixeldrain\.dev/u/[A-Za-z0-9]+', html)
        if m: hrefs.append(m.group(0))
        
        trs_links = extract_trs_links(html)
        hrefs.extend(trs_links)
        
        special_links = extract_special_links(html)
        for name, link in special_links:
            hrefs.append(link)
        
        mirrors = []
        for link in hrefs:
            if not link.startswith("http"):
                continue
            link = clean_url(link)
            
            if is_zipdisk(link, html):
                mirrors.append({"label": "zipdiskserver", "url": link})
                continue
            if "pixeldrain.dev/u" in link:
                mirrors.append({"label": "pixelserver", "url": link})
                continue
            if "fsl-buckets" in link:
                mirrors.append({"label": "FSL-V2", "url": link})
                continue
            if "r2.dev" in link:
                mirrors.append({"label": "FSL-R2", "url": link})
                continue
            if "pixel.hubcdn.fans" in link:
                mirrors.append({"label": "Pixel-Alt", "url": link})
                continue
            if "blockxpiracy" in link:
                mirrors.append({"label": "MegaServer", "url": link})
                continue
            if "stranger-things" in link:
                mirrors.append({"label": "FSL", "url": link})
                continue
            if "gpdl.hubcdn.fans" in link:
                mirrors.append({"label": "10Gbps", "url": link})
                direct = await resolve_10gbps_chain(session, link)
                if direct:
                    mirrors.append({"label": "10Gbps-Direct", "url": direct})
                continue
            if "trs.php" in link:
                final_trs = await resolve_trs(session, link)
                mirrors.append({"label": "TRS", "url": final_trs})
                continue
        
        out = []
        seen = set()
        for m in mirrors:
            if m["url"] not in seen:
                seen.add(m["url"])
                out.append(m)
        
        return {
            "success": True,
            "title": title,
            "size": size,
            "main_link": target,
            "mirrors": out
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def format_href(link):
    if not link:
        return "Not Found"
    return f'<a href="{link}">𝗟𝗜𝗡𝗞</a>'

def format_mirror(mirror):
    label = mirror["label"]
    url = mirror["url"]
    return f"┃ {label}: {format_href(url)}"

def format_hubcloud_message(data, message, elapsed):
    if not data["success"]:
        return f"❌ Error: {data['error']}"
    
    text = (
        f"✅ **HubCloud Extracted Links:**\n\n"
        f"┎ 📚 **Title:**\n"
        f"┃ {data['title']}\n\n"
        f"┠ 💾 **Size:**\n"
        f"┃ {data['size']}\n\n"
        f"┠ 🔗 **Source:**\n"
        f"┃ {format_href(data['main_link'])}\n\n"
    )
    
    if data["mirrors"]:
        text += f"┠ ⚡ **Available Mirrors ({len(data['mirrors'])}):**\n"
        for mirror in data["mirrors"]:
            text += format_mirror(mirror) + "\n"
        text += "\n"
    else:
        text += f"┠ ⚡ **Mirrors:**\n┃ No mirrors found\n\n"
    
    text += (
        f"┖ ⏱️ **Extracted in {elapsed} seconds**\n\n"
        f"━━━━━━━━✦✗✦━━━━━━━━\n\n"
        f"<b>Requested By :-</b> {message.from_user.mention}\n"
        f"<b>(#ID_{message.from_user.id})</b>"
    )
    
    return text

URL_RE = re.compile(r"https?://[^\s]+")

def extract_links_from_text(text):
    return URL_RE.findall(text or "")

@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hubcloud_handler(client: Client, message: Message):
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in our official group.")
    
    parts = message.text.split()
    links = extract_links_from_text(" ".join(parts[1:]))
    
    if not links and message.reply_to_message:
        links = extract_links_from_text(message.reply_to_message.text or "")
    
    if not links:
        return await message.reply("⚠️ Usage: /hub <link1> <link2> … OR reply to a message containing links.")
    
    links = links[:5]
    
    for i, url in enumerate(links, 1):
        temp = await message.reply(f"⏳ ({i}/{len(links)}) Fetching from HubCloud: {url}")
        start = time.time()
        async with aiohttp.ClientSession() as session:
            data = await extract_hubcloud_links(session, url)
        elapsed = round(time.time() - start, 2)
        formatted = format_hubcloud_message(data, message, elapsed)
        await temp.edit(formatted, disable_web_page_preview=True)
