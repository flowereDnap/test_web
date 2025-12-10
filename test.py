# Запустите это в отдельном файле
import asyncio
from aiogram import Bot
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

async def check_webhook():
    info = await bot.get_webhook_info()
    print(f"Current Webhook URL: {info.url}")
    print(f"Pending updates: {info.pending_update_count}")
    print(f"Error: {info.last_error_message}") # <-- Сфокусируйтесь на этом
    
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(check_webhook())