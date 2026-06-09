import os
import asyncio
from aiohttp import web
from pyrogram import Client
from config import *

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

async def health_handler(request):
    return web.Response(text="Bot running")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8000))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()
    print(f"Health server started on {port}")

async def main():
    bot = ShortnerBot()

    await bot.start()
    print("Bot started")

    await start_webserver()

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
