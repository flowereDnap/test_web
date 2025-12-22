import logging
from aiogram import Router, F, types
import asyncio
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.filters import Command, StateFilter
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramAPIError
from aiogram.fsm.context import FSMContext

# Локальные импорты
from init_bot import bot, dp # Импортируем наш объект бота
from db import db_manager
from utils.helpers import (
    is_admin, fetch_bot_stats, create_broadcast, send_broadcast
)
from states.FSM_states import BroadcastStates
from keyboards.inline import admin_keyboard

# Создаем роутер для админ-панели
router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "admin_main")
async def admin_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        return
    await state.clear()
    await callback_query.message.edit_text(
        "🛠 <b>Админ-панель управления</b>\n\nВыберите нужное действие:",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()

# --- СТАТИСТИКА ---

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if not is_admin(user_id):
        await callback_query.answer("У вас нет прав", show_alert=True)
        return
    
    await state.clear()
    # Передаем db_manager в функцию статистики
    stats_text = await fetch_bot_stats(db_manager)
    
    await callback_query.message.edit_text(
        stats_text, 
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )
    await callback_query.answer()

# --- ЗАПУСК СУЩЕСТВУЮЩЕЙ РАССЫЛКИ ---

async def start_broadcast(user_ids, message_text, db_manager, run_id):
    """
    Безопасная рассылка:
    - Помечает заблокировавших пользователей
    - Обрабатывает Flood Limit (Retry-After)
    - Не падает при ошибках
    """
    success_count = 0
    blocked_count = 0
    error_count = 0

    for user_id in user_ids:
        try:
            # Отправляем сообщение
            await bot.send_message(user_id, message_text)
            
            # Логируем успех в базу (для статистики в админке)
            await db_manager.mailing_db.log_stat(run_id, user_id, 'success')
            success_count += 1
            
            # Маленькая пауза, чтобы не триггерить лимиты (30 сообщений в секунду - лимит ТГ)
            await asyncio.sleep(0.05) 

        except TelegramForbiddenError:
            # Юзер заблокировал бота — помечаем его в базе, чтобы больше не слать
            logger.info(f"User {user_id} blocked the bot.")
            await db_manager.users_db.update_user_status(user_id, is_alive=False)
            await db_manager.mailing_db.log_stat(run_id, user_id, 'blocked')
            blocked_count += 1

        except TelegramRetryAfter as e:
            # Если всё же поймали Flood Limit — ждем сколько просит ТГ
            logger.warning(f"Flood limit! Sleeping for {e.retry_after} seconds.")
            await asyncio.sleep(e.retry_after)
            # Повторная попытка после паузы
            await bot.send_message(user_id, message_text)
            success_count += 1

        except TelegramAPIError as e:
            # Любая другая ошибка (неверный ID и т.д.)
            logger.error(f"API Error for {user_id}: {e}")
            await db_manager.mailing_db.log_stat(run_id, user_id, 'error')
            error_count += 1

    return success_count, blocked_count, error_count


@router.callback_query(F.data == "start_broadcast")
async def start_broadcast_menu(callback_query: types.CallbackQuery):
    """
    По нажатию на 'начать рассылку' показываем список сохраненных шаблонов
    """
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("У вас нет прав", show_alert=True)
        return

    # Получаем список всех созданных рассылок из БД
    mailings = await db_manager.mailing_db.get_all_broadcast_names()
    
    if not mailings:
        await callback_query.message.edit_text(
            "❌ У вас еще нет созданных шаблонов рассылок.",
            reply_markup=admin_keyboard()
        )
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for m in mailings:
        # m['name'] - техническое имя рассылки
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"🚀 {m['name']}", callback_data=f"run_broadcast:{m['id']}")
        ])
    
    kb.inline_keyboard.append([InlineKeyboardButton(text="« Назад", callback_data="admin_main")])

    await callback_query.message.edit_text(
        "Выберите шаблон рассылки для запуска:",
        reply_markup=kb
    )
    await callback_query.answer()

@router.callback_query(F.data.startswith("run_broadcast:"))
async def run_broadcast_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    # Используем твою функцию проверки админа
    if not is_admin(user_id):
        await callback_query.answer("У вас нет прав", show_alert=True)
        return
        
    id = int(callback_query.data.split(":")[1])
    await callback_query.message.edit_text(f"⏳ Рассылка  запущена в фоне.\nВы получите отчет сразу по завершении.")

    # Обертка для фоновой задачи, чтобы собрать статистику ПОСЛЕ завершения
    async def background_mailing():
        try:
            run_id = await send_broadcast({"id": id}, bot, db_manager)
            if run_id:
                stats = await db_manager.mailing_db.get_stats(run_id)
                mailing_data = await db_manager.mailing_db.get_mailing_by_run_id(run_id)
                
                title = mailing_data['title'] if mailing_data else "Mailing"
                report = (
                    f"🎉 <b>Рассылка #{run_id} завершена!</b>\n"
                    f"<b>Шаблон:</b> <code>{title}</code>\n"
                    f"—————————————————————\n"
                    f"✅ Успешно: <b>{stats.get('sent', 0)}</b>\n"
                    f"🚫 Блоки: <b>{stats.get('blocked', 0)}</b>\n"
                    f"⚠️ Ошибки: <b>{stats.get('error', 0)}</b>\n"
                    f"🖱 Клики: <b>{stats.get('clicked', 0)}</b>"
                )
                await bot.send_message(user_id, report, parse_mode="HTML")
        except Exception as e:
            logger.exception(f"Критическая ошибка в фоновой рассылке ")
            await bot.send_message(user_id, f"⚠️ Рассылка прервана ошибкой: {e}")

    # Запускаем как независимую задачу
    asyncio.create_task(background_mailing())
    await callback_query.answer()


# --- СОЗДАНИЕ НОВОЙ РАССЫЛКИ (FSM) ---

@router.callback_query(F.data == "create_broadcast")
async def create_broadcast_init(callback_query: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback_query.from_user.id):
        return
    await state.clear()
    await callback_query.message.answer("Введите техническое название рассылки (для списка):")
    await state.set_state(BroadcastStates.waiting_name)
    await callback_query.answer()

@router.message(StateFilter(BroadcastStates.waiting_name))
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Теперь отправьте медиа (фото, видео или гифку):")
    await state.set_state(BroadcastStates.waiting_media)

@router.message(StateFilter(BroadcastStates.waiting_media))
async def process_media(message: Message, state: FSMContext):
    file_id = None
    media_type = None

    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        media_type = 'video'
    elif message.animation:
        file_id = message.animation.file_id
        media_type = 'animation'
    elif message.document:
        file_id = message.document.file_id
        media_type = 'document'
        
    if not file_id:
        await message.answer("⚠️ Пожалуйста, отправьте фото, видео, гифку или документ.")
        return

    await state.update_data(media_file_id=file_id, media_type=media_type)
    await message.answer("Введите заголовок сообщения:")
    await state.set_state(BroadcastStates.waiting_title)

@router.message(StateFilter(BroadcastStates.waiting_title))
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите основной текст сообщения:")
    await state.set_state(BroadcastStates.waiting_text)

@router.message(StateFilter(BroadcastStates.waiting_text))
async def process_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Введите текст для кнопки (или 'нет'):")
    await state.set_state(BroadcastStates.waiting_button)

@router.message(StateFilter(BroadcastStates.waiting_button))
async def process_button(message: Message, state: FSMContext):
    if message.text.lower() == 'нет':
        await state.update_data(button_text=None, button_link=None)
        await finalize_broadcast(message, state)
    else:
        await state.update_data(button_text=message.text)
        await message.answer("Введите ссылку для кнопки:")
        await state.set_state(BroadcastStates.waiting_button_link)

@router.message(StateFilter(BroadcastStates.waiting_button_link))
async def process_button_link(message: Message, state: FSMContext):
    await state.update_data(button_link=message.text)
    await finalize_broadcast(message, state)

async def finalize_broadcast(message: Message, state: FSMContext):
    data = await state.get_data()
    # Передаем db_manager в функцию создания
    await create_broadcast(data, db_manager)
    await message.answer("✅ Шаблон рассылки успешно сохранен!", reply_markup=admin_keyboard())
    await state.clear()