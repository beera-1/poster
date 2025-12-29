from pyrogram import Client, filters
from pyrogram.types import Message


@Client.on_message(filters.command("extract_thumb") & filters.private)
async def pvt_cmd(client, message: Message):
        await message.reply_text(text="<b>This command is only available in specific groups.\nContact Admin @MrSagar_RoBot to get the link.</b>", disable_web_page_preview = False) 

@Client.on_message(filters.command("extract_thumb") & filters.group)
async def extract_telegram_thumb(client: Client, message: Message):
    reply = message.reply_to_message

    # Not a reply? Tell user to reply with media
    if not reply:
        return await message.reply("🖼 Reply with Telegram Video")

    # Not a video? Still guide user
    if not reply.video:
        return await message.reply("🖼 Reply with Telegram Video")

    # Video but no thumbnail
    if not reply.video.thumbs:
        return await message.reply("⚠️ No thumbnail found in this video.")

    # Download and send thumbnail
    thumb_path = await client.download_media(reply.video.thumbs[0])
    await message.reply_photo(photo=thumb_path, caption="✅ <b>Extracted Telegram Video Thumbnail</b>\n\n<b><blockquote>Powered by <a href='https://t.me/MrSagarbots'>MrSagarbots</a></blockquote></b>")
