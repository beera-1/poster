# plugins/hub.py
from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import re
import asyncio
import time
import random
import cloudscraper
from urllib.parse import urljoin, quote

OFFICIAL_GROUPS = ["-1002311378229"]

# ========================= CLOUDSCRAPER SETUP =========================
def create_scraper():
    """Create cloudscraper instance with proper settings"""
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False,
            'desktop': True,
        },
        interpreter='nodejs',
        delay=10,
        debug=False
    )
    
    # Set headers
    scraper.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    })
    
    return scraper

# ========================= SYNC FETCH FUNCTION =========================
def fetch_with_cloudscraper(url):
    """Fetch page using cloudscraper (synchronous)"""
    try:
        scraper = create_scraper()
        response = scraper.get(url, timeout=30)
        
        # Check if Cloudflare challenge passed
        if response.status_code == 200:
            return response.text, response.url
        else:
            raise Exception(f"HTTP {response.status_code}: {response.reason}")
            
    except Exception as e:
        raise Exception(f"Cloudscraper failed: {str(e)}")

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
        "fsl_v2": r"https://cdn\.fsl-buckets\.life/[^\s\"']+\?token=[A-Za-z0-9_]+",
        "fsl_r2": r"https://[A-Za-z0-9\.\-]+\.r2\.dev/[^\s\"']+\?token=[A-Za-z0-9_]+",
        "pixel_alt": r"https://pixel\.hubcdn\.fans/\?id=[A-Za-z0-9:]+",
        "pixeldrain": r"https://pixeldrain\.dev/u/[A-Za-z0-9]+",
        "zipdisk": r"https://[A-Za-z0-9\.\-]+workers\.dev/[^\s\"']+\.zip",
        "megaserver": r"https://mega\.blockxpiracy\.net/cs/g\?[^\s\"']+",
        "10gbps_gpdl": r"https://gpdl\.hubcdn\.fans/[^\s\"']+",
        "love_st": r"https://love\.stranger-things\.buzz/[^\s\"']+",
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
    """Resolve 10Gbps links using cloudscraper"""
    try:
        scraper = create_scraper()
        response = scraper.get(url, timeout=30, allow_redirects=True)
        final_url = response.url
        
        # extract ?link=REAL
        m = re.search(r"link=([^&]+)", final_url)
        if m:
            return m.group(1)
        
        # Also try to get Google Drive link
        if "drive.google.com" in final_url:
            return final_url
            
    except Exception as e:
        print(f"10Gbps resolve error: {e}")
        return None
    
    return None

async def resolve_trs(session, url):
    """Resolve TRS links using cloudscraper"""
    try:
        scraper = create_scraper()
        response = scraper.get(url, timeout=30, allow_redirects=True)
        return str(response.url)
    except Exception as e:
        print(f"TRS resolve error: {e}")
        return url

# ========================= MAIN SCRAPER =========================
async def extract_hubcloud_links(target):
    """Main extraction function"""
    try:
        target = normalize_hubcloud(target)
        print(f"Fetching: {target}")
        
        # Use cloudscraper to fetch page
        html, final_url = fetch_with_cloudscraper(target)
        
        # Check if still blocked by Cloudflare
        if "Just a moment" in html or "Checking your browser" in html or "Cloudflare" in html:
            return {
                "success": False,
                "error": "Cloudflare protection detected. Trying alternative method...",
                "title": "Cloudflare Blocked",
                "size": "Unknown",
                "main_link": target,
                "mirrors": []
            }
        
        # Extract title
        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "Unknown"
        
        # Clean title
        if "Just a moment" in title:
            title = "HubCloud Page"
        
        # Extract file size
        size_match = re.search(r"File Size<i[^>]*>(.*?)</i>", html, re.IGNORECASE | re.DOTALL)
        if size_match:
            size = re.sub(r"<.*?>", "", size_match.group(1)).strip()
        else:
            # Alternative size patterns
            size_patterns = [
                r'size[:\s]*([\d\.]+\s*(GB|MB|KB))',
                r'Size[:\s]*([\d\.]+\s*(GB|MB|KB))',
                r'([\d\.]+\s*(GB|MB|KB))\s*size',
                r'([\d\.]+\s*(GB|MB|KB))\s*Size'
            ]
            size = "Unknown"
            for pattern in size_patterns:
                m = re.search(pattern, html, re.IGNORECASE)
                if m:
                    size = m.group(1)
                    break
        
        # Extract token if exists
        token_match = re.search(r'href=[\'"]([^\'"]+token=[^\'"]+)[\'"]', html)
        if token_match and "token=" not in final_url:
            turl = token_match.group(1)
            if not turl.startswith("http"):
                turl = urljoin(target, turl)
            try:
                scraper = create_scraper()
                token_response = scraper.get(turl, timeout=20)
                html += token_response.text
            except:
                pass
        
        hrefs = extract_links(html)
        
        # Add direct pattern matches
        direct_patterns = [
            r'(https://love\.stranger-things\.buzz[^"\'\s]+)',
            r'(https://gpdl\.hubcdn\.fans[^"\'\s]+)',
            r'(https://pixeldrain\.dev/u/[A-Za-z0-9]+)',
            r'(https://cdn\.fsl-buckets\.life[^"\'\s]+\?token=[A-Za-z0-9_]+)',
            r'(https://[A-Za-z0-9\.\-]+\.r2\.dev[^"\'\s]+\?token=[A-Za-z0-9_]+)',
            r'(https://pixel\.hubcdn\.fans/\?id=[A-Za-z0-9:]+)',
            r'(https://mega\.blockxpiracy\.net/cs/g\?[^"\'\s]+)',
        ]
        
        for pattern in direct_patterns:
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
            
            if "r2.dev" in link and "token=" in link:
                mirrors.append({"label": "FSL-R2", "url": link})
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
                # Resolve direct link
                direct = await resolve_10gbps_chain(None, link)
                if direct and direct not in [m["url"] for m in mirrors]:
                    mirrors.append({"label": "10Gbps-Direct", "url": direct})
                continue
            
            # TRS links
            if "trs.php" in link:
                final_trs = await resolve_trs(None, link)
                if final_trs and final_trs not in [m["url"] for m in mirrors]:
                    mirrors.append({"label": "TRS", "url": final_trs})
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
            "main_link": target,
            "mirrors": unique_mirrors
        }
        
    except Exception as e:
        print(f"Error extracting links: {e}")
        return {
            "success": False,
            "error": str(e),
            "title": "Error",
            "size": "Unknown",
            "main_link": target,
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
        
        # Extract links using cloudscraper
        data = await extract_hubcloud_links(url)
        
        elapsed = round(time.time() - start, 2)
        
        formatted = format_hubcloud_message(data, message, elapsed)
        await temp.edit(formatted, disable_web_page_preview=True)
