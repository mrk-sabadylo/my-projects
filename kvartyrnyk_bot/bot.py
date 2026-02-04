"""
Головний файл Telegram-бота для реєстрації на подію "Квартирник"
"""

import asyncio
import logging

import dp
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers_user import user_router
from handlers_admin import admin_router


# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from database import db
print("DB METHODS:", dir(db))

async def main():
    """
    Головна функція запуску бота
    """
    logger.info("Запуск бота...")

    # Ініціалізація бота та диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Реєстрація роутерів
    # Важливо: admin_router має бути першим для пріоритету адмін-команд
    dp.include_router(admin_router)
    dp.include_router(user_router)

    logger.info("Бот успішно запущено!")
    logger.info("Натисніть Ctrl+C для зупинки бота")

    try:
        # Видалення вебхуків (якщо були)
        await bot.delete_webhook(drop_pending_updates=True)

        # Запуск polling
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}")


from aiogram.types import Message

@dp.message()
async def unknown(message: Message):
    await message.answer("Команду не розпізнано.")




