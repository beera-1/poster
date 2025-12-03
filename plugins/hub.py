import logging
import aiohttp
import re
import asyncio
from urllib.parse import urljoin, quote, unquote
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Real user agents for better compatibility
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

def get_headers():
    """Return headers with rotating user agent"""
    import random
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }


# --------------------------------------------------------
# UTILITIES
# --------------------------------------------------------
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


def extract_trs_links(html):
    """Extract TRS redirect links"""
    trs = set()
    trs.update(re.findall(r"window\.location\.href\s*=\s*'([^']*trs\.php[^']*)'", html))
    trs.update(re.findall(r'href=[\'"]([^\'"]*trs\.php[^\'"]*)[\'"]', html))
    trs.update(re.findall(r"(https?://[^\s\"']*trs\.php[^\s\"']*)", html))
    
    xs_matches = re.findall(r"trs\.php\?xs=[A-Za-z0-9=]+", html)
    for x in xs_matches:
        trs.add("https://hubcloud.foo/re/" + x)
    
    return list(trs)


def extract_special_links(html):
    """Extract special mirror patterns"""
    patterns = {
        "fsl_v2": r"https://cdn\.fsl-buckets\.life/[^\s\"']+\?token=[A-Za-z0-9_]+",
        "fsl_r2": r"https://[A-Za-z0-9\.\-]+\.r2\.dev/[^\s\"']+\?token=[A-Za-z0-9_]+",
        "pixel_alt": r"https://pixel\.hubcdn\.fans/\?id=[A-Za-z0-9:]+",
        "pixeldrain": r"https://pixeldrain\.dev/u/[A-Za-z0-9]+",
        "zipdisk": r"https://[A-Za-z0-9\.\-]+workers\.dev/[^\s\"']+\.zip",
        "megaserver": r"https://mega\.blockxpiracy\.net/cs/g\?[^\s\"']+",
        "gpdl": r"https://gpdl\.hubcdn\.fans/[^\s\"']+",
        "stranger": r"https://love\.stranger-things\.buzz[^\s\"']+",
    }
    
    found = []
    for name, pattern in patterns.items():
        for link in re.findall(pattern, html):
            found.append((name, link))
    
    return found


# --------------------------------------------------------
# ASYNC RESOLVERS
# --------------------------------------------------------
async def resolve_10gbps_chain(session, url):
    """Resolve 10Gbps chain to get Google Drive direct link"""
    try:
        async with session.get(url, headers=get_headers(), allow_redirects=True, timeout=15) as r:
            final = str(r.url)
        
        m = re.search(r"link=([^&]+)", final)
        if m:
            return unquote(m.group(1))
    except Exception as e:
        logger.warning(f"10Gbps resolve error: {e}")
    return None


async def resolve_trs(session, url):
    """Follow TRS redirect to get final Mega link"""
    try:
        async with session.get(url, headers=get_headers(), allow_redirects=True, timeout=15) as r:
            return str(r.url)
    except Exception as e:
        logger.warning(f"TRS resolve error: {e}")
    return url


# --------------------------------------------------------
# MAIN SCRAPER WITH ENHANCED EXTRACTION
# --------------------------------------------------------
async def extract_hubcloud_links(session, target):
    target = normalize_hubcloud(target)
    
    try:
        async with session.get(target, headers=get_headers(), timeout=20) as r:
            html = await r.text()
            final_url = str(r.url)
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return {
            "title": "Error",
            "size": "Unknown",
            "main_link": target,
            "mirrors": [],
            "error": str(e)
        }
    
    # Enhanced title extraction
    title = re.search(r"<title>(.*?)</title>", html, re.I)
    title = title.group(1).strip() if title else "Unknown"
    
    # Enhanced size extraction
    size = "Unknown"
    size_match = re.search(r"File Size<i[^>]*>(.*?)</i>", html, re.I)
    if size_match:
        size = re.sub(r"<.*?>", "", size_match.group(1)).strip()
    else:
        size_match = re.search(r"([\d\.]+\s*(?:GB|MB|TB))", html, re.I)
        if size_match:
            size = size_match.group(1)
    
    # Follow token links
    token = re.search(r'href=[\'"]([^\'"]+token=[^\'"]+)[\'"]', html)
    if token and "token=" not in final_url:
        turl = token.group(1)
        if not turl.startswith("http"):
            turl = urljoin(target, turl)
        try:
            async with session.get(turl, headers=get_headers(), timeout=15) as r2:
                html += await r2.text()
        except:
            pass
    
    hrefs = extract_links(html)
    
    # Extract special patterns
    special_patterns = [
        r'(https://love\.stranger-things\.buzz[^"]+)',
        r'(https://gpdl\.hubcdn\.fans[^"]+)',
        r'https://pixeldrain\.dev/u/[A-Za-z0-9]+'
    ]
    
    for pattern in special_patterns:
        m = re.search(pattern, html)
        if m:
            hrefs.append(m.group(0))
    
    # Add TRS and special links
    trs_links = extract_trs_links(html)
    hrefs.extend(trs_links)
    
    special_links = extract_special_links(html)
    for name, link in special_links:
        hrefs.append(link)
    
    mirrors = []
    pending_resolves = []
    
    for link in hrefs:
        if not link.startswith("http"):
            continue
        
        # Skip irrelevant links
        if any(skip in link.lower() for skip in ["javascript:", "mailto:", ".css", ".js", ".png", ".jpg"]):
            continue
        
        link = clean_url(link)
        
        if is_zipdisk(link, html):
            mirrors.append({"label": "ZipDisk", "url": link})
            continue
        
        if "pixeldrain.dev/u" in link:
            mirrors.append({"label": "PixelDrain", "url": link})
            continue
        
        if "fsl-buckets" in link or "fsl-buckets.life" in link:
            mirrors.append({"label": "FSL-V2", "url": link})
            continue
        
        if "r2.dev" in link and "token=" in link:
            mirrors.append({"label": "FSL-R2", "url": link})
            continue
        
        if "pixel.hubcdn.fans" in link:
            mirrors.append({"label": "Pixel-Alt", "url": link})
            continue
        
        if "blockxpiracy" in link or "mega.blockxpiracy" in link:
            mirrors.append({"label": "MegaServer", "url": link})
            continue
        
        if "stranger-things.buzz" in link:
            mirrors.append({"label": "FSL", "url": link})
            continue
        
        if "gpdl.hubcdn.fans" in link:
            mirrors.append({"label": "10Gbps", "url": link})
            pending_resolves.append(("10gbps", link))
            continue
        
        if "trs.php" in link:
            mirrors.append({"label": "TRS", "url": link})
            pending_resolves.append(("trs", link))
            continue
    
    # Resolve redirects asynchronously
    if pending_resolves:
        tasks = []
        for resolve_type, url in pending_resolves:
            if resolve_type == "10gbps":
                tasks.append(resolve_10gbps_chain(session, url))
            elif resolve_type == "trs":
                tasks.append(resolve_trs(session, url))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for (resolve_type, original_url), result in zip(pending_resolves, results):
            if result and not isinstance(result, Exception) and result != original_url:
                if resolve_type == "10gbps":
                    mirrors.append({"label": "10Gbps-Direct", "url": result})
                elif resolve_type == "trs":
                    mirrors.append({"label": "TRS-Direct", "url": result})
    
    # Dedupe
    out = []
    seen = set()
    for m in mirrors:
        if m["url"] not in seen:
            seen.add(m["url"])
            out.append(m)
    
    return {
        "title": title,
        "size": size,
        "main_link": target,
        "mirrors": out
    }


# --------------------------------------------------------
# OUTPUT FORMATTERS
# --------------------------------------------------------
def format_mirrors_basic(data):
    """Basic text formatting"""
    lines = []
    lines.append(f"📁 <b>{data['title']}</b>")
    lines.append(f"💾 Size: {data['size']}")
    lines.append(f"🔗 Original: <a href=\"{data['main_link']}\">Link</a>\n")
    
    if not data["mirrors"]:
        lines.append("⚠️ No mirrors found!")
    else:
        lines.append(f"📥 <b>Available Mirrors ({len(data['mirrors'])}):</b>\n")
        for idx, mirror in enumerate(data["mirrors"], 1):
            lines.append(f"{idx}. <b>{mirror['label']}</b>")
            lines.append(f"<code>{mirror['url']}</code>\n")
    
    return "\n".join(lines)


def format_mirrors_detailed(data):
    """Detailed formatting with emojis"""
    emoji_map = {
        "10Gbps": "⚡",
        "10Gbps-Direct": "🎯",
        "FSL-V2": "🚀",
        "FSL-R2": "💫",
        "Pixel-Alt": "🖼",
        "PixelDrain": "☁️",
        "ZipDisk": "📦",
        "MegaServer": "🔴",
        "FSL": "🌟",
        "TRS": "🔄",
        "TRS-Direct": "✅"
    }
    
    lines = []
    lines.append(f"📁 <b>{data['title']}</b>")
    lines.append(f"💾 Size: <code>{data['size']}</code>")
    lines.append(f"🔗 Source: <a href=\"{data['main_link']}\">HubCloud</a>\n")
    
    if not data["mirrors"]:
        lines.append("❌ No mirrors found!")
    else:
        lines.append(f"<b>📥 {len(data['mirrors'])} Mirror(s) Available:</b>\n")
        
        for idx, mirror in enumerate(data["mirrors"], 1):
            emoji = emoji_map.get(mirror['label'], "🔗")
            lines.append(f"{emoji} <b>{mirror['label']}</b>")
            lines.append(f"<code>{mirror['url']}</code>\n")
    
    return "\n".join(lines)


# --------------------------------------------------------
# TELEGRAM BOT HANDLERS
# --------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    keyboard = [
        [InlineKeyboardButton("📚 Help", callback_data="help"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '👋 <b>Welcome to Enhanced HubCloud Link Extractor Bot!</b>\n\n'
        '🔍 Extract download mirrors from HubCloud links with advanced features.\n\n'
        '<b>Quick Start:</b>\n'
        '• Send any HubCloud link\n'
        '• Get all mirrors instantly\n'
        '• Direct links resolved automatically\n\n'
        'Click buttons below for more info 👇',
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        '📖 <b>Available Commands:</b>\n\n'
        '<b>/start</b> - Show welcome message\n'
        '<b>/help</b> - Show this help message\n'
        '<b>/extract [url]</b> - Extract mirrors (basic format)\n'
        '<b>/extractf [url]</b> - Extract mirrors (detailed format)\n'
        '<b>/batch [urls]</b> - Process multiple URLs (max 5)\n'
        '<b>/stats</b> - Show bot statistics\n\n'
        '<b>🔍 How to Use:</b>\n'
        '1️⃣ Send a HubCloud link directly\n'
        '2️⃣ Or use /extract command\n'
        '3️⃣ Wait for extraction\n'
        '4️⃣ Get all available mirrors\n\n'
        '<b>✨ Features:</b>\n'
        '• Auto-resolves 10Gbps → Google Drive\n'
        '• Auto-resolves TRS → Mega links\n'
        '• Supports multiple mirror types\n'
        '• Batch processing support\n'
        '• Fast and reliable\n\n'
        '<b>Supported Domains:</b>\n'
        '• hubcloud.foo\n'
        '• hubcloud.one\n'
        '• hubcloud.fyi'
    )
    
    await update.message.reply_text(help_text, parse_mode='HTML')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics."""
    stats_text = (
        '📊 <b>Bot Statistics</b>\n\n'
        '✅ Status: <code>Online</code>\n'
        '🚀 Version: <code>2.0 Enhanced</code>\n'
        '⚡ Speed: <code>Fast</code>\n\n'
        '<b>Supported Mirrors:</b>\n'
        '⚡ 10Gbps (+ Direct)\n'
        '🚀 FSL V2 & R2\n'
        '☁️ PixelDrain\n'
        '📦 ZipDisk\n'
        '🔴 MegaServer\n'
        '✅ TRS (+ Direct)\n'
        '🌟 FSL Standard\n'
        '🖼 Pixel Alt'
    )
    
    await update.message.reply_text(stats_text, parse_mode='HTML')


async def extract_basic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extract with basic formatting."""
    await extract_handler(update, context, detailed=False)


async def extract_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extract with detailed formatting."""
    await extract_handler(update, context, detailed=True)


async def extract_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, detailed=False):
    """Main extraction handler."""
    message_text = ' '.join(context.args) if context.args else ''
    
    if not message_text:
        await update.message.reply_text(
            '❌ Please provide a HubCloud link!\n\n'
            '<b>Usage:</b>\n'
            f'<code>/{update.message.text.split()[0]} https://hubcloud.foo/xxxxx</code>',
            parse_mode='HTML'
        )
        return
    
    # Extract URL
    url_match = re.search(r'https?://[^\s]+', message_text)
    if not url_match:
        await update.message.reply_text('❌ No valid URL found!')
        return
    
    url = url_match.group(0)
    
    # Validate HubCloud URL
    if not re.search(r'hubcloud\.(foo|one|fyi)', url, re.IGNORECASE):
        await update.message.reply_text('❌ Please provide a valid HubCloud link!')
        return
    
    processing_msg = await update.message.reply_text('🔄 <b>Processing your link...</b>', parse_mode='HTML')
    
    try:
        async with aiohttp.ClientSession() as session:
            result = await extract_hubcloud_links(session, url)
        
        if "error" in result:
            await processing_msg.edit_text(f'❌ <b>Error:</b> {result["error"]}', parse_mode='HTML')
            return
        
        # Format response
        if detailed:
            response = format_mirrors_detailed(result)
        else:
            response = format_mirrors_basic(result)
        
        # Split if too long
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            await processing_msg.edit_text(parts[0], parse_mode='HTML', disable_web_page_preview=True)
            for part in parts[1:]:
                await update.message.reply_text(part, parse_mode='HTML', disable_web_page_preview=True)
        else:
            await processing_msg.edit_text(response, parse_mode='HTML', disable_web_page_preview=True)
    
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        await processing_msg.edit_text(f'❌ <b>Error:</b> {str(e)}', parse_mode='HTML')


async def batch_extract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process multiple URLs."""
    if not context.args:
        await update.message.reply_text(
            '❌ Please provide HubCloud links!\n\n'
            '<b>Usage:</b>\n'
            '<code>/batch url1 url2 url3</code>\n\n'
            '<i>Maximum 5 URLs per batch</i>',
            parse_mode='HTML'
        )
        return
    
    urls = []
    for arg in context.args:
        if re.search(r'hubcloud\.(foo|one|fyi)', arg, re.IGNORECASE):
            urls.append(arg)
    
    if not urls:
        await update.message.reply_text('❌ No valid HubCloud URLs found!')
        return
    
    urls = urls[:5]  # Limit to 5
    
    await update.message.reply_text(
        f'🔄 <b>Processing {len(urls)} URL(s)...</b>\n'
        f'<i>This may take a moment...</i>',
        parse_mode='HTML'
    )
    
    async with aiohttp.ClientSession() as session:
        for idx, url in enumerate(urls, 1):
            status_msg = await update.message.reply_text(
                f'⏳ <b>Extracting {idx}/{len(urls)}...</b>',
                parse_mode='HTML'
            )
            
            try:
                result = await extract_hubcloud_links(session, url)
                response = format_mirrors_basic(result)
                
                await status_msg.edit_text(response, parse_mode='HTML', disable_web_page_preview=True)
            except Exception as e:
                await status_msg.edit_text(f'❌ Error processing URL {idx}: {str(e)}', parse_mode='HTML')
            
            # Small delay between requests
            if idx < len(urls):
                await asyncio.sleep(2)
    
    await update.message.reply_text('✅ <b>Batch processing complete!</b>', parse_mode='HTML')


async def process_direct_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process HubCloud links sent directly."""
    message_text = update.message.text.strip()
    
    # Check if message contains hubcloud link
    if not re.search(r'hubcloud\.(foo|one|fyi)', message_text, re.IGNORECASE):
        return
    
    url_match = re.search(r'https?://[^\s]+', message_text)
    if not url_match:
        return
    
    url = url_match.group(0)
    
    processing_msg = await update.message.reply_text('🔄 <b>Extracting mirrors...</b>', parse_mode='HTML')
    
    try:
        async with aiohttp.ClientSession() as session:
            result = await extract_hubcloud_links(session, url)
        
        if "error" in result:
            await processing_msg.edit_text(f'❌ <b>Error:</b> {result["error"]}', parse_mode='HTML')
            return
        
        response = format_mirrors_detailed(result)
        
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            await processing_msg.edit_text(parts[0], parse_mode='HTML', disable_web_page_preview=True)
            for part in parts[1:]:
                await update.message.reply_text(part, parse_mode='HTML', disable_web_page_preview=True)
        else:
            await processing_msg.edit_text(response, parse_mode='HTML', disable_web_page_preview=True)
    
    except Exception as e:
        logger.error(f"Direct link processing error: {e}")
        await processing_msg.edit_text(f'❌ <b>Error:</b> {str(e)}', parse_mode='HTML')


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "help":
        help_text = (
            '📖 <b>Quick Help</b>\n\n'
            'Simply send me any HubCloud link and I\'ll extract all mirrors!\n\n'
            '<b>Commands:</b>\n'
            '/extract - Basic extraction\n'
            '/extractf - Detailed extraction\n'
            '/batch - Multiple URLs\n'
            '/stats - Bot info\n\n'
            'Use /help for detailed information.'
        )
        await query.edit_message_text(help_text, parse_mode='HTML')
    
    elif query.data == "about":
        about_text = (
            'ℹ️ <b>About This Bot</b>\n\n'
            '🤖 Enhanced HubCloud Link Extractor\n'
            '📦 Version: 2.0\n'
            '⚡ Fast & Reliable\n\n'
            '<b>Features:</b>\n'
            '• Auto-resolve direct links\n'
            '• Multiple mirror support\n'
            '• Batch processing\n'
            '• Clean interface\n\n'
            '💡 Tip: Just paste any HubCloud link!'
        )
        await query.edit_message_text(about_text, parse_mode='HTML')


def main():
    """Start the bot."""
    print("🤖 Enhanced HubCloud Telegram Bot v2")
    print("=" * 50)
    token = input("Enter your Telegram Bot Token: ").strip()
    
    if not token:
        print("❌ Token cannot be empty!")
        return
    
    application = Application.builder().token(token).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("extract", extract_basic))
    application.add_handler(CommandHandler("extractf", extract_detailed))
    application.add_handler(CommandHandler("batch", batch_extract))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Direct link handler (must be last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_direct_link))
    
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("=" * 50)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
