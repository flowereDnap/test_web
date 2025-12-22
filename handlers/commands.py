import logging
from aiogram import Router, F, types
from aiogram.types import Message
from aiogram.filters import Command

# Импортируем роутер, а не dp
router = Router()

# Импортируем менеджер базы данных и бота
from db import db_manager
from utils.helpers import is_admin, save_referral, save_user_to_db
from keyboards.inline import admin_keyboard, user_keyboard

logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def start_handler(message: Message):
    """Обработчик команды /start"""
    text = message.text or ""
    parts = text.split(maxsplit=1)
    args = parts[1] if len(parts) > 1 else ""
    
    user = message.from_user
    if not user:
        return

    # 1. Сохраняем пользователя (передаем db_manager в хелпер, как мы договаривались)
    await save_user_to_db(user, db_manager)
    
    # 2. Синхронизируем видео
    try:
        await db_manager.videos_db.sync_videos_from_folder()
    except Exception:
        logger.exception("Failed to sync videos folder")

    # 3. Реферальная система
    if args:
        # Убедись, что в save_referral ты тоже добавил db_manager как аргумент
        await save_referral(new_user_id=user.id, ref_payload=args, db_manager=db_manager)

    # 4. Ответ пользователю
    if is_admin(user.id):
        await message.answer("Привет, админ. Выберите действие:", reply_markup=admin_keyboard())
    else:
        await message.answer("Привет! Нажми кнопку, чтобы открыть мини-апп 👇", reply_markup=user_keyboard())

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Обработчик команды /admin"""
    if not is_admin(message.from_user.id):
        await message.reply("Доступ только для админа.")
        return
    await message.reply("Админ меню:", reply_markup=admin_keyboard())