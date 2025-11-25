from pyrogram import Client, filters
from pyrogram.types import Message
import aiohttp
import re
from urllib.parse import urlparse, urljoin


# -------------------------
# Normalize to hubcloud.foo
# -------------------------
def normalize_to_foo(url: str):
    if "hubcloud.foo" in url:
        return url
    return re.sub(r"hubcloud\.(one|fyi)", "hubcloud.foo", url)


# -------------------------
# SAFE HUBCLOUD LINK EXTRACTOR
# -------------------------
def extract_hubcloud_links(text: str):
    if not text:
        return []

    pattern = r"https?://hubcloud\.(one|fyi|foo)/drive/[A-Za-z0-9]+"
    fixed = [m.group(0) for m in re.finditer(pattern, text)]
    return list(set(fixed))


# --------------------------------------------------------
# Extract Google direct CDN link from GamerXyt HTML
# --------------------------------------------------------
async def extract_google_from_gamer(session, url):
    try:
        async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as r:
            html = await r.text()

        m = re.search(r'id="vd" href=[\'"]([^\'"]+)[\'"]', html)
        if m:
            return m.group(1)
    except:
        pass
    return None


@Client.on_message(filters.command(["hub", "hubcloud"]))
async def hubcloud_handler(client: Client, message: Message):

    OFFICIAL_GROUPS = ["-1002311378229"]
    if str(message.chat.id) not in OFFICIAL_GROUPS:
        return await message.reply("❌ This command only works in the official group.")

    hub_links = []

    # Command extract
    if len(message.command) > 1:
        hub_links.extend(extract_hubcloud_links(" ".join(message.command[1:])))

    # Reply extract
    if message.reply_to_message:
        tx = message.reply_to_message.text or message.reply_to_message.caption or ""
        hub_links.extend(extract_hubcloud_links(tx))

    hub_links = list(set(hub_links))

    if not hub_links:
        return await message.reply(
            "❌ No HubCloud links found.\n\nUse `/hub <link>` or reply with /hub"
        )

    # Convert all → hubcloud.foo
    hub_links = [normalize_to_foo(u) for u in hub_links]

    msg = await message.reply_text("🔍 Fetching all links...")

    # ------------------------------------------------
    # CONTACT WORKER BUT WITH EXTRA 10GB DIRECT FIX
    # ------------------------------------------------
    async with aiohttp.ClientSession() as session:
        try:
            params = {"url": ",".join(hub_links)}
            async with session.get("https://hub-v2.botzs.workers.dev/", params=params, timeout=120) as resp:
                result_text = await resp.text()

        except Exception as e:
            return await msg.edit(f"⚠️ Error contacting Worker:\n`{e}`")

    final = "🟢 **HubCloud Multi-Extract Result**\n\n"
    blocks = result_text.strip().split("--------------------------------------")

    for block in blocks:
        b = block.strip()
        if not b:
            continue

        lines = b.split("\n")
        # First 3 lines = Title, Size, Original Link
        final += "\n".join(lines[:3]) + "\n\n"

        label = None

        for ln in lines[3:]:
            ln = ln.strip()
            if not ln:
                continue

            # -------------------------
            # LABEL LINE
            # -------------------------
            if not ln.startswith("http"):
                label = ln.lower()
                icon = (
                    "🔵" if "fsl" in label else
                    "🟠" if "10gb" in label else
                    "🟢" if "pixel" in label else
                    "🟥" if "mega" in label else
                    "🟣" if "zip" in label else
                    "⚪"
                )
                continue

            # -------------------------
            # DIRECT GOOGLE LINK FIX FOR 10GB TITLE
            # -------------------------
            if "10gb" in label:
                # Step 1 → visit pixel.hubcdn → redirect → gamerxyt
                try:
                    async with aiohttp.ClientSession() as session2:
                        async with session2.get(ln, allow_redirects=True,
                                                headers={"User-Agent": "Mozilla/5.0"}) as r:
                            gamer_url = str(r.url)

                        # Step 2 → extract Google direct link
                        direct = await extract_google_from_gamer(session2, gamer_url)

                        if direct:
                            final += f"**🟠 10gb title**\n{direct}\n\n"
                            continue
                except:
                    pass

            # normal mirror
            final += f"**{icon} {label}**\n{ln}\n\n"

        final += "\n"

    # -------------------------
    # SPLIT TOO LONG MESSAGES
    # -------------------------
    MAX_LEN = 4000
    if len(final) <= MAX_LEN:
        return await msg.edit(final, disable_web_page_preview=True)

    parts = [final[i:i + MAX_LEN] for i in range(0, len(final), MAX_LEN)]
    await msg.edit(parts[0], disable_web_page_preview=True)

    for p in parts[1:]:
        await message.reply(p, disable_web_page_preview=True)
