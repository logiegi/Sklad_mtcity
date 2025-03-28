import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers import dp

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

async def on_startup(_):
    logging.info("Bot started")
    asyncio.create_task(refresh_preloaded_data())  # Запуск фоновой задачи

if __name__ == "__main__":
    bot = Bot(token=BOT_TOKEN)
    dp.bot = bot
    asyncio.run(dp.start_polling(on_startup=on_startup))