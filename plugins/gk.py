from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import re

API_URL = "https://hub-xi-hazel.vercel.app/api/bypaas/gk.php"
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
@Client.on_message(filters.command(["gk", "gkfile"]))
async def gky_handler(client: Client, message: Message):

    # ------------------ Authorization ------------------
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in our official group.")
    # ---------------------------------------------------

    gky_urls = []

    # Case 1: URLs in command
    if len(message.command) > 1:
        gky_urls.extend(
            re.findall(
                r"https?://gkyfilehost\.online/file/\S+",
                " ".join(message.command[1:])
            )
        )

    # Case 2: URLs in replied message
    if message.reply_to_message:
        txt = message.reply_to_message.text or message.reply_to_message.caption or ""
        gky_urls.extend(
            re.findall(r"https?://gkyfilehost\.online/file/\S+", txt)
        )

    if not gky_urls:
        return await message.reply(
            "❌ No GKYFileHost links found.\n\n"
            "`/gk <gkyfilehost_file_url>` or `/gkfile <url>`\n"
            "or reply with `/gk` / `/gkfile`"
        )

    wait_msg = await message.reply("🔍 Fetching GKY download links...")

    final_text = "✅ **GKYFILEHOST LINKS**\n\n"

    try:
        async with aiohttp.ClientSession() as session:
            for url in gky_urls:

                async with session.get(API_URL, params={"url": url}, timeout=90) as resp:
                    data = await resp.json()

                if not data.get("success"):
                    final_text += f"❌ Failed:\n`{url}`\n\n"
                    continue

                file = data.get("file", {})
                links = data.get("links", {})

                # ---------- FILE INFO ----------
                final_text += (
                    f"🎬 **{file.get('name', 'Unknown')}**\n"
                    f"💾 **Size:** {file.get('size', 'Unknown')}\n"
                    f"📁 **Type:** {file.get('type', 'Unknown')}\n"
                    f"🗓 **Date:** {file.get('date', 'Unknown')}\n\n"
                )

                # ---------- LINKS ----------
                if links.get("cloud_10gbps"):
                    final_text += f"☁️ **Cloud DL [10GBPS]:** {href(links['cloud_10gbps'])}\n"

                if links.get("fsl"):
                    final_text += f"⚡ **FSL Server:** {href(links['fsl'])}\n"

                if links.get("ultra"):
                    final_text += f"🔥 **Ultra DL:** {href(links['ultra'])}\n"

                if links.get("pixeldrain"):
                    final_text += f"🟣 **PixelDrain:** {href(links['pixeldrain'])}\n"

                if links.get("gofile"):
                    final_text += f"🟪 **GoFile:** {href(links['gofile'])}\n"

                if links.get("hubcloud_queue"):
                    final_text += f"☁️ **HubCloud Queue:** {href(links['hubcloud_queue'])}\n"

                final_text += "\n━━━━━━━━━━━━━━\n\n"

        await safe_edit_or_send(
            wait_msg,
            final_text,
            disable_web_page_preview=True
        )

    except Exception as e:
        await wait_msg.edit(f"⚠️ Error:\n`{e}`")
