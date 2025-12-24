import aiohttp
from aiohttp import web
from config import *  # API_ID, API_HASH, BOT_TOKEN
from pyrogram import Client
import asyncio
import logging

# ================= LOGGER =================
logging.basicConfig(
    format="[%(asctime)s] [%(levelname)s] - %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger("poster")

# ================= BOT INSTANCE =================
class ShortnerBot(Client):
    def __init__(self):
        super().__init__(
            "Scrapper",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="plugins"),
            workers=100,
        )

# 🔥 GLOBAL BOT INSTANCE (IMPORTANT FOR PLUGINS)
bot = ShortnerBot()

# ================= HEALTH CHECK =================
async def health_handler(request):
    return web.Response(text="✅ Bot is running on Koyeb")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", health_handler)  # Koyeb health ping
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    LOGGER.info("🌐 Health check server running on port 8080")

# ================= MAIN =================
async def main():
    await bot.start()
    LOGGER.info("🤖 Bot started successfully!")

    # Run health check server in parallel
    await start_webserver()

    # Keep running until Ctrl+C / Koyeb stop
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
