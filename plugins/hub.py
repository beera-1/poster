from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import re

API_URL = "https://hub-xi-hazel.vercel.app/api/bypaas/hubcloud.php"
OFFICIAL_GROUPS = ["-1002311378229"]

MAX_LEN = 4000  # Telegram safe limit


# ---------- SAFE SEND ----------
async def safe_send_links(client, chat_id, text, reply_to_id=None, **kwargs):
    if len(text) <= MAX_LEN:
        await client.send_message(chat_id, text, reply_to_message_id=reply_to_id, **kwargs)
        return

    parts = [text[i:i + MAX_LEN] for i in range(0, len(text), MAX_LEN)]
    for part in parts:
        await client.send_message(chat_id, part, reply_to_message_id=reply_to_id, **kwargs)


# ---------- COMMAND ----------
@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hubcloud_handler(client: Client, message: Message):

    # ------------------ Authorization ------------------
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in our official group.")
    # ---------------------------------------------------

    hubcloud_urls = []

    # Case 1: Detect all URLs in the command line space
    if len(message.command) > 1:
        hubcloud_urls.extend(
            re.findall(r"https?://hubcloud\.\S+", " ".join(message.command[1:]))
        )

    # Case 2: Detect all URLs if replying to another message text/caption
    if message.reply_to_message:
        txt = message.reply_to_message.text or message.reply_to_message.caption or ""
        hubcloud_urls.extend(re.findall(r"https?://hubcloud\.\S+", txt))

    if not hubcloud_urls:
        return await message.reply(
            "❌ No HubCloud links found.\n\n"
            "`/hub <url1> <url2> <url3>`\n"
            "or reply to a list of links with `/hub`"
        )

    wait_msg = await message.reply("🔍 Fetching HubCloud links...")

    try:
        async with aiohttp.ClientSession() as session:
            # Loops 1-by-1 through each discovered URL sequentially
            for idx, url in enumerate(hubcloud_urls, 1):

                async with session.get(API_URL, params={"url": url}, timeout=90) as resp:
                    if resp.status == 200:
                        try:
                            data = await resp.json()
                        except Exception:
                            continue
                    else:
                        continue

                if not data or "links" not in data:
                    continue

                # --- 1. Start Building Message Header ---
                display_text = (
                    f"🎬 **{data.get('title', 'Unknown Title')}**\n"
                    f"💾 **Size:** {data.get('size', 'Unknown Size')}\n\n"
                )

                # --- 2. Extract Google Video URL ---
                if data.get("google_video"):
                    display_text += f"▶️ Google Video:\n{data['google_video']}\n\n"

                # --- 3. Robust URL Structure Recognition Patterns ---
                fsl_links = []
                pixel_zip_links = []
                google_links = []
                pixel_links = []
                buzz_links = []

                for item in data.get("links", []):
                    t = item.get("type", "").lower() 
                    u = item.get("url", "")

                    if not u:
                        continue

                    # Recognise FSL using domain structure signature
                    if "hub.auvps.buzz" in u.lower() or t == "fsl":
                        fsl_links.append(u)

                    # Recognise Buzz Server using domain structure signature
                    elif "bzzhr.co" in u.lower() or "buzz" in t:
                        buzz_links.append(u)

                    # Recognise PIXEL-Zip using data properties 
                    elif t == "pixel-zip" or (t == "zip" and "pixeldrain" in u.lower()):
                        pixel_zip_links.append(u)

                    # Recognise standard Pixel Servers
                    elif t == "pixel" or "pixeldrain" in u.lower():
                        pixel_links.append(u)

                    # Recognise Google Cloud 10GP targets
                    elif t == "google" or "10gp" in t or "gpdl" in u.lower():
                        google_links.append(u)

                # --- 4. Append Link Group Blocks ---
                if fsl_links:
                    display_text += "🟢 FSL Links:\n" + "\n".join(fsl_links) + "\n\n"

                if google_links:
                    display_text += "🚀 10GP OPEN IT:\n" + "\n".join(google_links) + "\n\n"

                if pixel_links:
                    display_text += "🟣 PIXEL:\n" + "\n".join(pixel_links) + "\n\n"

                if buzz_links:
                    display_text += "🔥 BUZZ-SERVER:\n" + "\n".join(buzz_links) + "\n\n"

                if pixel_zip_links:
                    display_text += "📦 PIXEL-Zip Files:\n" + "\n".join(pixel_zip_links) + "\n\n"

                # --- 5. Send Message for This Link Instantly ---
                await safe_send_links(
                    client,
                    message.chat.id,
                    display_text.strip(),
                    reply_to_id=message.id,
                    disable_web_page_preview=True
                )

        # Clean up search status banner once all processing ends
        await wait_msg.delete()

    except Exception:
        pass
