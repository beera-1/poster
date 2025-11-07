from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import aiohttp
import re

# 🌞 Your deployed Worker
WORKER_URL = "https://sun.botzs.workers.dev/"

# 🛡️ Allowed groups (replace with yours)
OFFICIAL_GROUPS = ["-1002311378229"]

@Client.on_message(filters.command(["sunnxt", "sun"]))
async def sunnxt_poster(client: Client, message: Message):
    # ------------------ Authorization Check ------------------
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return

    # ------------------ Command Check ------------------
    if len(message.command) < 2:
        await message.reply(
            "Usage:\n`/sunnxt <SunNXT page URL>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    page_url = message.text.split(" ", 1)[1].strip()

    # ------------------ Fetch from Worker ------------------
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={page_url}", timeout=20) as resp:
                if resp.status != 200:
                    await message.reply(f"❌ Worker returned HTTP {resp.status}")
                    return
                text = await resp.text()

        # ------------------ Swap Main Poster and Cover ------------------
        # Capture all 1920x1080 image links
        posters = re.findall(
            r"https:\/\/sund-images\.sunnxt\.com\/[^\s]+1920x1080[^\s]+\.jpg", text
        )

        if len(posters) > 1:
            # swap order: make 2nd image main poster, 1st image cover
            main_poster, cover = posters[1], posters[0]

            # rebuild text line by line
            lines = text.splitlines()
            new_lines = []
            main_done = False
            cover_done = False

            for line in lines:
                if line.startswith("Sun NXT Posters:") and not main_done:
                    new_lines.append("Sun NXT Posters:")
                    new_lines.append(main_poster)
                    main_done = True
                elif line.startswith("Cover:") and not cover_done:
                    new_lines.append(f"Cover: {cover}")
                    cover_done = True
                else:
                    new_lines.append(line)

            text = "\n".join(new_lines)

        # ------------------ Send Response ------------------
        if len(text) > 4096:
            for i in range(0, len(text), 4096):
                await message.reply(text[i:i+4096], disable_web_page_preview=False)
        else:
            await message.reply(text, disable_web_page_preview=False)

    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")
