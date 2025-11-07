from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
import aiohttp
import re

WORKER_URL = "https://sunnxt-poster-worker.yourdomain.workers.dev/"
OFFICIAL_GROUPS = ["-1002311378229"]  # Replace with your official group ID

@Client.on_message(filters.command(["sunnxt", "sun"]))
async def sunnxt_poster(client: Client, message: Message):
    # ------------------ Authorization Check ------------------
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        await message.reply("❌ This command only works in our official group.")
        return

    # ------------------ Command Validation ------------------
    if len(message.command) < 2:
        await message.reply(
            "Usage:\n`/sunnxt <SunNXT page URL>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    page_url = message.text.split(" ", 1)[1].strip()

    # ------------------ Fetch Data from Worker ------------------
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WORKER_URL}?url={page_url}", timeout=20) as resp:
                if resp.status != 200:
                    await message.reply(f"❌ Worker returned HTTP {resp.status}")
                    return
                text = await resp.text()

        # ------------------ Swap Cover and Sun NXT Poster ------------------
        # Find the main poster (top image) and cover URLs using regex
        pattern = r"(https:\/\/sund-images\.sunnxt\.com\/[^\s]+1920x1080[^\s]+\.jpg)"
        posters = re.findall(pattern, text)

        if len(posters) > 1:
            # Swap the first (main) and second (cover)
            main_poster = posters[1]
            cover = posters[0]

            # Replace in text
            lines = text.splitlines()
            new_lines = []
            swapped = False

            for line in lines:
                if line.startswith("Sun NXT Posters:") and not swapped:
                    new_lines.append("Sun NXT Posters:")
                    new_lines.append(main_poster)
                    swapped = True
                elif line.startswith("Cover:") and cover:
                    new_lines.append(f"Cover: {cover}")
                else:
                    new_lines.append(line)

            text = "\n".join(new_lines)

        # ------------------ Send Result ------------------
        if len(text) > 4096:
            for i in range(0, len(text), 4096):
                await message.reply(text[i:i+4096], disable_web_page_preview=False)
        else:
            await message.reply(text, disable_web_page_preview=False)

    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")
