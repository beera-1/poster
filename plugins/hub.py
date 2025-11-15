from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import re

# Your Cloudflare Worker API
WORKER_URL = "https://hub-v2.botzs.workers.dev/"

@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hubcloud_handler(client: Client, message: Message):

    OFFICIAL_GROUPS = ["-1002311378229"]
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return

    hubcloud_urls = []

    # Direct links in the command
    if len(message.command) > 1:
        raw = " ".join(message.command[1:])
        hubcloud_urls.extend(
            [u.strip() for u in raw.replace("\n", " ").replace(",", " ").split() if u.strip()]
        )

    # Reply message with HubCloud links
    if message.reply_to_message:
        reply_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        found = re.findall(r"https?://hubcloud\.(one|fyi)/\S+", reply_text)
        hubcloud_urls.extend(found)

    if not hubcloud_urls:
        await message.reply_text(
            "❌ No HubCloud links found.\n\nUsage:\n`/hub <hubcloud_url>`\nOR reply to a message."
        )
        return

    wait = await message.reply_text("🔍 Fetching links from Worker...")

    try:
        async with aiohttp.ClientSession() as session:
            params = {"url": ",".join(hubcloud_urls)}
            async with session.get(WORKER_URL, params=params, timeout=90) as resp:
                worker_text = await resp.text()

        # Worker returns plain text, NOT JSON now
        raw = worker_text.strip().split("\n\n")

        text = "🟢 **HubCloud Extracted Links**\n\n"

        for block in raw:
            if not block.strip():
                continue
            lines = block.split("\n", 1)
            if len(lines) == 2:
                label = lines[0].strip()
                link = lines[1].strip()

                if label.lower() == "fsl":
                    icon = "🔵"
                elif label.lower() == "10gb title":
                    icon = "🟠"
                elif label.lower() == "pixelserver":
                    icon = "🟢"
                elif label.lower() == "mega server":
                    icon = "🟥"
                elif label.lower() == "zipdiskserver":
                    icon = "🟣"
                else:
                    icon = "🔗"

                text += f"**{icon} {label}**\n{link}\n\n"

        await wait.edit_text(text, disable_web_page_preview=True)

    except Exception as e:
        await wait.edit_text(f"⚠️ Error:\n`{e}`")
