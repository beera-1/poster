from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import re

API_URL = "https://hub-fawn.vercel.app/api/bypaas/hubcloud.php"
OFFICIAL_GROUPS = ["-1002311378229"]

MAX_LEN = 4000  # Telegram safe limit


# ---------- SAFE SEND / EDIT ----------
async def safe_edit_or_send(msg, text, **kwargs):
    if len(text) <= MAX_LEN:
        await msg.edit(text, **kwargs)
        return

    parts = [text[i:i + MAX_LEN] for i in range(0, len(text), MAX_LEN)]
    await msg.edit(parts[0], **kwargs)
    for part in parts[1:]:
        await msg.reply(part, **kwargs)


# ---------- LINK FORMATTER ----------
def href(url: str):
    return f"[𝗟𝗜𝗡𝗞]({url})"


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

    final_text = "✅ **HubCloud Extracted Links**\n\n"

    try:
        async with aiohttp.ClientSession() as session:
            for idx, url in enumerate(hubcloud_urls, 1):

                async with session.get(API_URL, params={"url": url}, timeout=90) as resp:
                    data = await resp.json()

                if "title" not in data:
                    final_text += f"❌ Failed:\n`{url}`\n\n"
                    continue

                final_text += (
                    f"🎬 **{data.get('title', 'Unknown')}**\n"
                    f"💾 **Size:** {data.get('size', 'Unknown')}\n"
                    f"🔗 **Source:** {href(data.get('source'))}\n"
                )

                # Google Video
                if data.get("google_video"):
                    final_text += f"▶️ **Google Video:** {href(data['google_video'])}\n"

                final_text += "\n"

                # Links (Zip / FSL / Pixel / R2 / etc)
                if data.get("links"):
                    final_text += "🔁 **Download Links:**\n"
                    for l in data["links"]:
                        final_text += f"🔹 **{l['type']}** → {href(l['url'])}\n"
                    final_text += "\n"

                final_text += "━━━━━━━━━━━━━━\n\n"

        await safe_edit_or_send(
            wait_msg,
            final_text,
            disable_web_page_preview=True
        )

    except Exception as e:
        await wait_msg.edit(f"⚠️ Error:\n`{e}`")
