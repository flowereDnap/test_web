import os
import sys
import logging
import asyncio
import pathlib

import aiohttp
from aiohttp import web
from dotenv import load_dotenv


from config import *
from api.routes import *

# Основные компоненты aiogram
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, 
    CallbackQuery, 
    WebAppInfo, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    Update,
    InputFile
)

# Локальные модули
import db
from db import db_manager

# ----------------- load config -----------------

# ----------------- logging & bot -----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    ADMIN_IDS = []
    for item in admin_ids_raw.split(","):
        item = item.strip()
        if item.isdigit():
            ADMIN_IDS.append(int(item))
except Exception as e:
    logger.error(f"Error parsing ADMIN_IDS: {e}")
    ADMIN_IDS = []



def is_admin(user_id: int) -> bool:
    return int(user_id) in ADMIN_IDS


if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not set in .env")
    sys.exit(1)
if not WEBHOOK_HOST and not WEBHOOK_URL:
    print("ERROR: WEBHOOK_HOST or WEBHOOK_URL must be set in .env")
    sys.exit(1)
if not WEBHOOK_SECRET_TOKEN:
    print("ERROR: WEBHOOK_SECRET_TOKEN not set in .env")
    sys.exit(1)

if not WEBHOOK_URL:
    WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}/{WEBHOOK_SECRET_TOKEN}"

# project root for static files
PROJ_ROOT = pathlib.Path(__file__).parent.resolve()



bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)



# ---------- Helper functions (DB-backed) ----------

async def on_startup(app):
    app['http_session'] = aiohttp.ClientSession()




async def set_main_commands(bot: Bot):
    commands = [
        types.BotCommand(command="start", description="🏠 Главное меню"),
        types.BotCommand(command="admin", description="👑 Меню администратора")
    ]
    await bot.set_my_commands(commands)
    logger.info("Bot commands menu set successfully.")

async def save_referral(new_user_id: int, ref_payload: str):
    if not db_manager.users_db:
        logger.warning("save_referral: users_db not initialized")
        return
    try:
        ref_id = int(ref_payload)
    except Exception:
        # payload не numeric — записываем в logs (можно доработать)
        return
    await db_manager.users_db.add_referral(referrer_id=ref_id, referral_id=new_user_id)





# -------------------- Функция отправки бродкаста --------------------


# -------------------- Функция отправки бродкаста --------------------


# ---------- Webapp endpoints ----------



# ---------- Keyboards ----------
def user_keyboard():
    mini_url = os.getenv("MINIAPP_URL") or WEBHOOK_HOST or ""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Открыть мини-апп",
                web_app=WebAppInfo(url=mini_url)
            )
        ]]
    )
    return kb

def admin_keyboard():
    mini_url = os.getenv("MINIAPP_URL") or WEBHOOK_HOST or ""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Статистика бота", callback_data="admin_stats")],
            [InlineKeyboardButton(text="начать рассылку", callback_data="start_broadcast")],
            [InlineKeyboardButton(text="создать новую рассылку", callback_data="create_broadcast")],
            [
            InlineKeyboardButton(
                text="Открыть мини-апп",
                web_app=WebAppInfo(url=mini_url)
            )
        ]
        ]
    )
    return kb

# -------------------- FSM --------------------
class BroadcastStates(StatesGroup):
    waiting_name = State()
    waiting_media = State()
    waiting_title = State()
    waiting_text = State()
    waiting_button = State()
    waiting_button_link = State()


# ---------- Handlers (Важный порядок: Специфичные -> Общие) ----------

# --- НОВЫЙ ОБРАБОТЧИК: mark_visited_handler ---
async def mark_visited_handler(request: web.Request):
    """
    POST /api/quest/visited
    body: { quest_id: str, telegram_id: int }
    """
    try:
        data = await request.json()
        quest_id = data.get("quest_id")
        telegram_id = data.get("telegram_id")
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if not quest_id or not telegram_id:
        return web.json_response({"error": "Missing fields"}, status=400)
    
    # ИСПОЛЬЗУЕМ НОВЫЙ МЕНЕДЖЕР
    await db_manager.quests_db.set_quest_status(telegram_id, quest_id, 'visited')
    
    return web.json_response({"status": "ok", "message": f"Quest {quest_id} marked as visited"})


# --- НОВЫЙ ОБРАБОТЧИК: get_quests_statuses ---


@dp.message(F.text == "/start")
async def start_handler(message: Message):

 
    text = message.text or ""
    parts = text.split(maxsplit=1)
    args = parts[1] if len(parts) > 1 else ""
    user = message.from_user
    timezone = None  # можно передать реальное значение из WebApp JS
    await save_user_to_db(user, timezone=timezone)
    # синк видео при старте (можно отключить, если дорого) 
    try:
        await db_manager.videos_db.sync_videos_from_folder()
    except Exception:
        logger.exception("Failed to sync videos folder")

    if args:
        await save_referral(new_user_id=user.id, ref_payload=args)
    if is_admin(user.id):
        await message.answer("Привет, админ. Выберите действие:", reply_markup=admin_keyboard())
    else:
        await message.answer("Привет! Нажми кнопку, чтобы открыть мини-апп 👇", reply_markup=user_keyboard())

@dp.message(F.text == "/admin")
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("Доступ только для админа.")
        return
    await message.reply("Админ меню:", reply_markup=admin_keyboard())

# --- ХЕНДЛЕРЫ CALLBACK QUERY ---

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if not is_admin(user_id):
        await callback_query.answer("У вас нет прав", show_alert=True)
        return
    
    # Обязательный ответ на callback, чтобы закрыть "часики"
    await callback_query.answer() 
    await state.clear()
    
    # Очистка состояния на всякий случай, если админ нажмет кнопку во время FSM
    await state.clear()
    
    stats_text = await fetch_bot_stats()
    await callback_query.message.edit_text(f"📊 Статистика:\n\n{stats_text}", reply_markup=admin_keyboard())


@dp.callback_query(F.data == "create_broadcast")
async def broadcast_callback(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    if not is_admin(user_id):
        await callback_query.answer("У вас нет прав", show_alert=True)
        return
    # Запуск FSM
    await callback_query.message.answer("Название рассылки (только для вас)")
    await state.set_state(BroadcastStates.waiting_name)


# bot.py

@dp.callback_query(F.data == "start_broadcast")
async def broadcast_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    if not is_admin(user_id):
        await callback_query.answer("У вас нет прав", show_alert=True)
        return

    await callback_query.answer("Загрузка списка рассылок...")
    
    # 1. Получаем список рассылок
    broadcasts = await db_manager.mailing_db.get_all_broadcast_names()
    
    if not broadcasts:
        await callback_query.message.answer("⚠️ В базе данных нет сохраненных рассылок.")
        # Очищаем сообщение с кнопкой "Запуск рассылки"
        await callback_query.message.edit_reply_markup(reply_markup=None)
        return
        
    # 2. Генерируем Inline-кнопки
    keyboard_rows = []
    for item in broadcasts:
        # Callback Data будет: "run_broadcast:<название_рассылки>"
        callback_data = f"run_broadcast:{item['name']}"
        keyboard_rows.append([InlineKeyboardButton(text=item['name'], callback_data=callback_data)])
        
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    # 3. Отправляем список админу
    await callback_query.message.edit_text(
        "Выберите рассылку для запуска:",
        reply_markup=markup
    )


@dp.callback_query(F.data.startswith("run_broadcast:"))
async def run_broadcast_callback(callback_query: types.CallbackQuery):
    # ... (проверки прав остаются)
    user_id = callback_query.from_user.id
    
    if not is_admin(user_id):
        await callback_query.answer("У вас нет прав", show_alert=True)
        return
        
    await callback_query.answer("Запуск рассылки...")
    
    # 1. Извлекаем название рассылки
    name = callback_query.data.split(":")[1]
    
    await callback_query.message.edit_text(f"⏳ Запускаем рассылку: **{name}**. Ожидайте финальный отчет.")
    
    try:
        # 2. Вызываем функцию отправки, которая теперь возвращает run_id
        # run_id - это ID из таблицы mailing_runs
        run_id = await send_broadcast({"name": name})
        
        # 3. Отправка отчета
        if run_id:
            # Нам нужно найти ID шаблона (mailing_id), чтобы получить title
            mailing_data = await db_manager.mailing_db.get_mailing_by_run_id(run_id) 
            
            # 4. Получаем статистику по УНИКАЛЬНОМУ run_id
            stats = await db_manager.mailing_db.get_stats(run_id)
            
            # --- Формирование отчета ---
            # NOTE: Мы должны добавить в db.py метод get_mailing_by_run_id для получения данных шаблона
            title = mailing_data['title'] if mailing_data else "Неизвестная рассылка"
            total_sent = stats.get('sent', 0)
            total_failed = stats.get('failed', 0)
            total_clicks = stats.get('clicked', 0)
            
            report_text_html = (
                f"🎉 <b>Отчет о запуске #{run_id}</b>\n"
                f"<b>Тема шаблона:</b> <code>{title}</code>\n"
                f"—————————————————————\n"
                f"✅ <b>Отправлено успешно:</b> <b>{total_sent}</b>\n"
                f"❌ <b>Не удалось отправить:</b> <b>{total_failed}</b>\n"
                f"➡️ <b>Кликнувших:</b> <b>{total_clicks}</b>\n"
            )
            
            await callback_query.message.answer(report_text_html)
            
    except Exception as e:
        logger.exception(f"Критическая ошибка при запуске рассылки '{name}'")
        await callback_query.message.answer(f"⚠️ Произошла критическая ошибка при запуске рассылки '{name}': {e}")

# --- ХЕНДЛЕРЫ FSM (Используют StateFilter) ---

@dp.message(Command("broadcast"))
async def start_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear() # Начинаем с чистого листа
    await message.answer("Отправьте медиа-файл (картинка, гифка или видео) или документ")
    await state.set_state(BroadcastStates.waiting_name)

@dp.message(StateFilter(BroadcastStates.waiting_name))
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Отправьте медиа-файл (картинка, гифка или видео) или документ")
    await state.set_state(BroadcastStates.waiting_media)


@dp.message(StateFilter(BroadcastStates.waiting_media)) # Все остальные сообщения в этом состоянии
async def process_media_invalid(message: types.Message, state: FSMContext):
    await message.answer("⚠️ Пожалуйста, отправьте именно медиа-файл (картинку, гифку или видео) или документ для рассылки.")
    # НЕ МЕНЯЕМ СОСТОЯНИЕ!

@dp.message(StateFilter(BroadcastStates.waiting_media), F.content_type.in_({"photo", "video", "document", "animation"}))
async def process_media(message: types.Message, state: FSMContext):
    # Определяем file_id и media_type в строгом порядке
    file_id = None
    media_type = None

    if message.photo:
        file_id = message.photo[-1].file_id
        media_type = ContentType.PHOTO.value
    elif message.video:
        file_id = message.video.file_id
        media_type = ContentType.VIDEO.value
    elif message.animation:
        # ПРИОРИТИЗИРУЕМ ANIMATION (GIF)
        file_id = message.animation.file_id
        media_type = ContentType.ANIMATION.value
    elif message.document:
        # Только если это просто документ, не попавший в предыдущие категории
        file_id = message.document.file_id
        media_type = ContentType.DOCUMENT.value
        
    if not file_id:
        await message.answer("⚠️ Не удалось получить ID медиафайла. Попробуйте снова.")
        return

    # Сохраняем file_id и ТИП КОНТЕНТА
    await state.update_data(media_msg=message, media_file_id=file_id, media_type=media_type)
    await message.answer("Введите заголовок рассылки:")
    await state.set_state(BroadcastStates.waiting_title)

@dp.message(StateFilter(BroadcastStates.waiting_title))
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите текст рассылки:")
    await state.set_state(BroadcastStates.waiting_text)

@dp.message(StateFilter(BroadcastStates.waiting_text))
async def process_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await message.answer("Введите текст кнопки:")
    await state.set_state(BroadcastStates.waiting_button)

@dp.message(StateFilter(BroadcastStates.waiting_button))
async def process_button(message: types.Message, state: FSMContext):
    await state.update_data(button_text=message.text)
    await message.answer("Введите ссылку кнопки:")
    await state.set_state(BroadcastStates.waiting_button_link)
    

@dp.message(StateFilter(BroadcastStates.waiting_button_link))
async def process_button_link(message: types.Message, state: FSMContext):
    await state.update_data(button_link=message.text)
    await message.answer("✅ Создаем")
    data = await state.get_data()
    await create_broadcast(data)
    await state.clear()

# --- ОБЩИЕ CATCH-ALL ХЕНДЛЕРЫ (Должны быть в самом конце) ---

@dp.callback_query()
async def debug_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Этот сработает, если callback_data не "admin_stats" и не "broadcast"
    current_state = await state.get_state() # <-- Получаем текущее состояние
    print("CALLBACK:", callback_query.data, "FROM:", callback_query.from_user.id)
    print(f"User state: {current_state}") # <-- Лог состояния
    await callback_query.answer() # Обязательно ответить

@dp.message(F.text)
async def echo_or_help(message: Message):
    # Этот сработает, если сообщение не команда и не FSM-ответ
    await message.reply("Используй /start чтобы начать.")


# ---------- Webhook server ----------
async def handle_webhook(request: web.Request):
    logger.info(f"--- WEBHOOK RECEIVED --- Method: {request.method}")

    secret = request.match_info.get("secret")
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")

    logger.info(f"Checking secrets: URL_Secret={secret}, Header_Secret={header_secret}")
    logger.info(f"Expected secret: {WEBHOOK_SECRET_TOKEN}")
    
    if secret != WEBHOOK_SECRET_TOKEN and header_secret != WEBHOOK_SECRET_TOKEN:
        logger.warning("Invalid webhook secret token")
        return web.Response(status=403, text="forbidden")
    try:
        body = await request.json()
        # --- ДОБАВЛЕННЫЙ ЛОГ ---
        update_type = list(body.keys())[1] if len(body.keys()) > 1 else 'N/A'
        logger.info(f"--- UPDATE TYPE: {update_type} ---")
        # -----------------------
        update = Update.model_validate(body, context={"bot": bot})
        await dp.feed_update(bot=bot, update=update)
    except Exception:
        logger.exception("Failed to process update")
        return web.Response(status=500, text="Internal Server Error")
    return web.Response(status=200, text="OK")

async def set_webhook():

    webhook_address = f"{WEBHOOK_URL}{WEBHOOK_PATH}/{WEBHOOK_SECRET_TOKEN}"

    await bot.delete_webhook()
    await bot.set_webhook(url=WEBHOOK_URL_FINAL,
                          secret_token=WEBHOOK_SECRET_TOKEN,
                          allowed_updates=[])
    await set_main_commands(bot)
    logger.info(f"Webhook set to {WEBHOOK_URL_FINAL}")

# ---------- App lifecycle ----------
@web.middleware
async def cors_middleware(request, handler):
    # простая CORS — в проде замени '*' на конкретный origin
    if request.method == 'OPTIONS':
        return web.Response(status=200, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Requested-With'
        })
    resp = await handler(request)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'
    return resp

async def root_redirect(request):
        return web.FileResponse(os.path.join(PROJ_ROOT, 'miniapp', 'index.html'))

async def start_app():
    # инициализация БД через db_manager
    await db_manager.setup()
    logger.info("Database initialized")

    # создаём aiohttp app с CORS
    app = web.Application(middlewares=[cors_middleware])
    app['db_manager'] = db_manager

    # маршруты: webhook (POST), api и статика
    app.router.add_get('/', handle_web_app)
    app.router.add_get("/api/video/random", get_random_video)
    app.router.add_post("/api/video/watched", video_watched_handler)
    app.router.add_get("/api/quest/statuses", get_quests_statuses)
    app.router.add_post('/api/quest/visited', mark_quest_visited)
    app.router.add_post('/api/quest/check', check_follow_quest_status_handler) # Для FollowQuest
    app.router.add_post('/api/quest/complete', complete_quest_handler)
    app.router.add_get('/api/quest/get_list', get_quest_config_list)
    app.router.add_post('/api/quest/verify', verify_quest_handler)

    app.router.add_post(f"{WEBHOOK_PATH}/telegram/{{secret}}", handle_webhook)

    # Serve miniapp folder (CSS/JS/images) under '/'
    miniapp_path = PROJ_ROOT / "miniapp"
    if miniapp_path.exists():
        app.router.add_static('/assets', path=str(miniapp_path), show_index=False)
    
    # Serve videos
    vids_path = PROJ_ROOT / "vids"
    if vids_path.exists():
        app.router.add_static('/vids', path=str(vids_path), show_index=False)

    async def on_shutdown(app):
        try:
            await bot.delete_webhook()
        except Exception:
            logger.exception("Failed to delete webhook on shutdown")
        try:
            await bot.session.close()
        except Exception:
            try:
                await bot.close()
            except Exception:
                pass
        if db_manager.pool:
            await db_manager.close()
            logger.info("DB pool closed")

    app.on_shutdown.append(on_shutdown)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="127.0.0.1", port=PORT)
    await site.start()
    logger.info("Webhook server started on port %s", PORT)
    await set_webhook()

    # keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(start_app())
    except KeyboardInterrupt:
        logger.info("Shutting down...")