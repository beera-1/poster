from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import re

API_URL = "https://hub-eight-ruddy.vercel.app/api/bypaas/hubcloud.php"
OFFICIAL_GROUPS = ["-1002311378229"]

MAX_LEN = 4000  # Telegram safe limit


# ---------- SAFE SEND / EDIT ----------
async def safe_edit_or_send(msg, text, **kwargs):
    if len(text) <= MAX_LEN:
        await msg.edit(text, **kwargs)
        return

    parts = [text[i:i+MAX_LEN] for i in range(0, len(text), MAX_LEN)]

    await msg.edit(parts[0], **kwargs)
    for part in parts[1:]:
        await msg.reply(part, **kwargs)


# ---------- COMMAND ----------
@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hubcloud_old_handler(client: Client, message: Message):

    # ------------------ Authorization Check ------------------
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return
    # ---------------------------------------------------------

    hubcloud_urls = []

    # Case 1: URLs inside command
    if len(message.command) > 1:
        raw = " ".join(message.command[1:])
        hubcloud_urls.extend(
            [u.strip() for u in raw.split() if "hubcloud" in u]
        )

    # Case 2: URLs inside replied message
    if message.reply_to_message:
        txt = message.reply_to_message.text or message.reply_to_message.caption or ""
        found = re.findall(r"https?://hubcloud\.\S+", txt)
        hubcloud_urls.extend(found)

    if not hubcloud_urls:
        await message.reply(
            "❌ No HubCloud links found.\n\n"
            "Usage:\n`/hub <hubcloud_url>`\n"
            "or reply with `/hub` to a message containing HubCloud links."
        )
        return

    wait_msg = await message.reply("🔍 Fetching HubCloud links...")

    final_text = "✅ **HubCloud Extracted Links:**\n\n"

    try:
        async with aiohttp.ClientSession() as session:
            for url in hubcloud_urls:

                params = {"url": url}
                async with session.get(API_URL, params=params, timeout=90) as resp:
                    data = await resp.json()

                if "title" not in data:
                    final_text += f"❌ Failed for:\n`{url}`\n\n"
                    continue

                title = data.get("title", "Unknown Name")
                size = data.get("size", "Unknown Size")
                google = data.get("google_video")
                main_link = data.get("main_link")

                final_text += f"🎬 **{title}**\n"
                final_text += f"💾 **Size:** {size}\n"
                final_text += f"🔗 **Main Link:** {main_link}\n\n"

                # Google Video
                if google:
                    final_text += f"▶️ **Google Video:**\n{google}\n\n"

                # Zipdisk / Pixeldrain
                if data.get("zip_files"):
                    for z in data["zip_files"]:
                        final_text += (
                            f"🟣 **ZipDisk / Pixel**\n"
                            f"📁 {z.get('name', 'File')}\n"
                            f"🔗 {z.get('url')}\n\n"
                        )

                # Mirrors
                if data.get("mirrors"):
                    final_text += "🔁 **Mirrors:**\n"
                    for m in data["mirrors"]:
                        final_text += f"🔹 {m['label']} → {m['url']}\n"
                    final_text += "\n"

        # ✅ SAFE SEND (no MESSAGE_TOO_LONG error)
        await safe_edit_or_send(
            wait_msg,
            final_text,
            disable_web_page_preview=True
        )

    except Exception as e:
        await wait_msg.edit(f"⚠️ Error:\n`{e}`")
