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


# ---------- LINK FORMATTER (FIXED: SHOWS RAW URL) ----------
def href(url: str):
    return url  # Returns the raw URL text so it is fully visible


# ---------- COMMAND ----------
@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hubcloud_handler(client: Client, message: Message):

    # ------------------ Authorization ------------------
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in our official group.")
    # ---------------------------------------------------

    hubcloud_urls = []

    # Case 1: URLs in command
    if len(message.command) > 1:
        hubcloud_urls.extend(
            re.findall(r"https?://hubcloud\.\S+", " ".join(message.command[1:]))
        )

    # Case 2: URLs in replied message
    if message.reply_to_message:
        txt = message.reply_to_message.text or message.reply_to_message.caption or ""
        hubcloud_urls.extend(re.findall(r"https?://hubcloud\.\S+", txt))

    if not hubcloud_urls:
        return await message.reply(
            "❌ No HubCloud links found.\n\n"
            "`/hub <hubcloud_url>`\n"
            "or reply with `/hub`"
        )

    wait_msg = await message.reply("🔍 Fetching HubCloud links...")

    try:
        async with aiohttp.ClientSession() as session:
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

                # Array to hold purely the formatted links
                link_list = []

                # 1. Grab Google Video URL directly if it exists
                if data.get("google_video"):
                    link_list.append(href(data["google_video"]))

                # 2. Grab all URLs inside the links array
                for item in data.get("links", []):
                    item_url = item.get("url")
                    if item_url:
                        link_list.append(href(item_url))

                if not link_list:
                    continue

                # Combine the links together cleanly using simple newlines
                clean_output = "\n\n".join(link_list)

                # Send the clean lines directly to the chat 1-by-1
                await safe_send_links(
                    client,
                    message.chat.id,
                    clean_output,
                    reply_to_id=message.id,
                    disable_web_page_preview=True
                )

        # Remove searching notification block when done
        await wait_msg.delete()

    except Exception:
        pass
