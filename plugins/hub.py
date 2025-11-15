from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import re

WORKER_URL = "https://hub-v2.botzs.workers.dev/"   # your worker

@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hubcloud_handler(client: Client, message: Message):

    OFFICIAL_GROUPS = ["-1002311378229"]
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in the official group.")
        return

    hub_links = []

    # Get links from command
    if len(message.command) > 1:
        raw = " ".join(message.command[1:])
        hub_links.extend([u.strip() for u in raw.split() if "hubcloud." in u])

    # Get links from reply message
    if message.reply_to_message:
        tx = (message.reply_to_message.text or message.reply_to_message.caption or "")
        reply_links = re.findall(r"https?://hubcloud\.(one|fyi)/drive/\S+", tx)
        hub_links.extend(reply_links)

    if not hub_links:
        return await message.reply(
            "❌ No HubCloud links found.\n\n"
            "Usage: `/hub <hubcloud link>`\n"
            "Or reply to a message containing HubCloud links."
        )

    status = await message.reply_text("🔍 Fetching all links...")

    try:
        async with aiohttp.ClientSession() as session:
            params = {"url": ",".join(hub_links)}
            async with session.get(WORKER_URL, params=params, timeout=120) as resp:
                result_text = await resp.text()

    except Exception as e:
        return await status.edit(f"⚠️ Error contacting Worker:\n`{e}`")

    # ---------------------------
    # FORMAT WORKER TEXT OUTPUT
    # ---------------------------

    final = "🟢 **HubCloud Multi-Extract Result**\n\n"
    blocks = result_text.strip().split("--------------------------------------")

    for block in blocks:
        b = block.strip()
        if not b:
            continue

        lines = b.split("\n")

        # File Info (🎬 Name, 📦 Size, 🔗 Link)
        final += "\n".join(lines[:3]) + "\n\n"

        # All mirrors after file info
        mirror_lines = lines[3:]

        label = None
        for ln in mirror_lines:
            ln = ln.strip()
            if not ln:
                continue

            # Detect label (FSL, pixelserver, mega etc)
            if not ln.startswith("http"):
                label = ln  
                icon = "🔵" if "fsl" in ln.lower() \
                    else "🟠" if "10gb" in ln.lower() \
                    else "🟢" if "pixel" in ln.lower() \
                    else "🟥" if "mega" in ln.lower() \
                    else "🟣" if "zip" in ln.lower() \
                    else "⚪"
                continue

            # URL line
            final += f"**{icon} {label}**\n{ln}\n\n"

        final += "\n"

    await status.edit(final, disable_web_page_preview=True)
