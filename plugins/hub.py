# plugins/hub.py
from pyrogram import Client, filters
from pyrogram.types import Message
import requests
import re
import time
from urllib.parse import urljoin, quote

OFFICIAL_GROUPS = ["-1002311378229"]

# ========================= REAL BROWSER HEADERS =========================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

# ========================= SIMPLE FETCH FUNCTION =========================
def fetch_page(url):
    """Simple fetch with proper headers"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        
        # Check if we got a valid response
        if response.status_code == 200:
            return response.text, response.url
        elif response.status_code in [403, 429, 503]:
            # Cloudflare or rate limit
            raise Exception(f"Access denied (HTTP {response.status_code}). Try again later.")
        else:
            raise Exception(f"HTTP {response.status_code}: {response.reason}")
            
    except requests.exceptions.Timeout:
        raise Exception("Request timeout. Try again.")
    except Exception as e:
        raise Exception(f"Failed to fetch page: {str(e)}")

# ========================= HELPER FUNCTIONS =========================
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
        "10gbps_gpdl": r"https://gpdl\.hubcdn\.fans/[^\s\"']+",
        "love_st": r"https://love\.stranger-things\.buzz/[^\s\"']+",
        "pixeldrain": r"https://pixeldrain\.dev/u/[A-Za-z0-9]+",
        "fsl_v2": r"https://cdn\.fsl-buckets\.life/[^\s\"']+\?token=[A-Za-z0-9_]+",
        "pixel_alt": r"https://pixel\.hubcdn\.fans/\?id=[A-Za-z0-9:]+",
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

def resolve_link(url):
    """Resolve redirects"""
    try:
        response = requests.get(url, headers=HEADERS, allow_redirects=True, timeout=20)
        return response.url
    except:
        return url

# ========================= MAIN SCRAPER =========================
def extract_hubcloud_links_sync(url):
    """Synchronous extraction"""
    try:
        url = normalize_hubcloud(url)
        print(f"Fetching: {url}")
        
        # Fetch page
        html, final_url = fetch_page(url)
        
        # Check for Cloudflare
        if "Just a moment" in html or "Checking your browser" in html:
            return {
                "success": False,
                "error": "Cloudflare protection detected. Try using a VPN or different network.",
                "title": "Cloudflare Blocked",
                "size": "Unknown",
                "main_link": url,
                "mirrors": []
            }
        
        # Extract title
        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "HubCloud Page"
        
        # Clean title
        title = title.replace(" - HubCloud", "").replace(" | HubCloud", "")
        
        # Extract file size
        size_match = re.search(r"File Size<i[^>]*>(.*?)</i>", html, re.IGNORECASE | re.DOTALL)
        if size_match:
            size = re.sub(r"<.*?>", "", size_match.group(1)).strip()
        else:
            size = "Unknown"
        
        # Get all links
        hrefs = extract_links(html)
        
        # Add direct pattern matches
        patterns_to_find = [
            r'https://gpdl\.hubcdn\.fans[^\s"\']+',
            r'https://love\.stranger-things\.buzz[^\s"\']+',
            r'https://pixeldrain\.dev/u/[A-Za-z0-9]+',
            r'https://cdn\.fsl-buckets\.life[^\s"\']+\?token=[A-Za-z0-9_]+',
            r'https://pixel\.hubcdn\.fans/\?id=[A-Za-z0-9:]+',
            r'https://mega\.blockxpiracy\.net/cs/g\?[^\s"\']+',
        ]
        
        for pattern in patterns_to_find:
            matches = re.findall(pattern, html)
            hrefs.extend(matches)
        
        # Extract TRS links
        trs_links = extract_trs_links(html)
        hrefs.extend(trs_links)
        
        # Extract special links
        special_links = extract_special_links(html)
        for name, link in special_links:
            hrefs.append(link)
        
        mirrors = []
        for link in hrefs:
            if not link.startswith("http"):
                continue
            
            link = clean_url(link)
            
            # Skip duplicates
            if any(m["url"] == link for m in mirrors):
                continue
            
            # Classify links
            if is_zipdisk(link, html):
                mirrors.append({"label": "zipdiskserver", "url": link})
                continue
            
            if "pixeldrain.dev/u" in link:
                mirrors.append({"label": "pixelserver", "url": link})
                continue
            
            if "fsl-buckets.life" in link:
                mirrors.append({"label": "FSL-V2", "url": link})
                continue
            
            if "pixel.hubcdn.fans" in link:
                mirrors.append({"label": "Pixel-Alt", "url": link})
                continue
            
            if "blockxpiracy" in link:
                mirrors.append({"label": "MegaServer", "url": link})
                continue
            
            if "stranger-things.buzz" in link:
                mirrors.append({"label": "FSL", "url": link})
                continue
            
            # 10Gbps links
            if "gpdl.hubcdn.fans" in link:
                mirrors.append({"label": "10Gbps", "url": link})
                # Try to resolve
                resolved = resolve_link(link)
                if resolved != link and "drive.google.com" in resolved:
                    mirrors.append({"label": "Google Drive", "url": resolved})
                continue
            
            # TRS links
            if "trs.php" in link:
                resolved = resolve_link(link)
                mirrors.append({"label": "TRS", "url": resolved})
                continue
        
        # Deduplicate
        unique_mirrors = []
        seen_urls = set()
        for m in mirrors:
            if m["url"] not in seen_urls:
                seen_urls.add(m["url"])
                unique_mirrors.append(m)
        
        return {
            "success": True,
            "title": title,
            "size": size,
            "main_link": url,
            "mirrors": unique_mirrors
        }
        
    except Exception as e:
        print(f"Error extracting links: {e}")
        return {
            "success": False,
            "error": str(e),
            "title": "Error",
            "size": "Unknown",
            "main_link": url,
            "mirrors": []
        }

# ========================= FORMAT HELPERS =========================
def format_href(link):
    """Format link with <a href> and display 𝗟𝗜𝗡𝗞"""
    if not link:
        return "Not Found"
    return f'<a href="{link}">𝗟𝗜𝗡𝗞</a>'

def format_mirror(mirror):
    label = mirror["label"]
    url = mirror["url"]
    return f"┃ {label}: {format_href(url)}"

# ========================= FORMAT MESSAGE =========================
def format_hubcloud_message(data, message, elapsed):
    if not data["success"]:
        return f"❌ **Error:** {data['error']}\n\n🔗 **URL:** {data['main_link']}"
    
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
        for i, mirror in enumerate(data["mirrors"], 1):
            text += f"┃ {i}. {mirror['label']}: {format_href(mirror['url'])}\n"
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

# ========================= URL EXTRACTOR =========================
URL_RE = re.compile(r"https?://[^\s]+")

def extract_links_from_text(text):
    return URL_RE.findall(text or "")

# ========================= MAIN COMMAND =========================
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
    
    links = links[:3]  # Limit to 3 links
    
    for i, url in enumerate(links, 1):
        temp = await message.reply(f"⏳ ({i}/{len(links)}) Fetching from HubCloud...\n🔗 {url}")
        
        start = time.time()
        
        # Extract links (synchronous)
        data = extract_hubcloud_links_sync(url)
        
        elapsed = round(time.time() - start, 2)
        
        formatted = format_hubcloud_message(data, message, elapsed)
        await temp.edit(formatted, disable_web_page_preview=True)
