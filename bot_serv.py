import os
import sys
import logging
import asyncio
import pathlib

import aiohttp
from aiohttp import web
from dotenv import load_dotenv

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

# Попытка импорта проверки подписи Web App
try:
    from aiogram.utils.web_app import check_webapp_signature
except ImportError:
    try:
        from aiogram.utils.web_app import check_web_app_signature as check_webapp_signature
    except ImportError:
        check_webapp_signature = None

# Локальные модули
import db
from db import db_manager

# ----------------- load config -----------------

# ----------------- logging & bot -----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
#WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
#WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook/telegram")
#WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN")
#WEBHOOK_URL = os.getenv("WEBHOOK_URL")


PORT = int(os.getenv("PORT_NEW", "8080"))
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST_NEW")
WEBHOOK_URL = os.getenv("WEBHOOK_URL_NEW") 
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH_NEW") # /webhook
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN_NEW")

WEBHOOK_URL_FINAL = os.getenv("WEBHOOK_URL_NEW_FINAL")


# Загружаем ID admin
admin_ids_raw = os.getenv("ADMIN_IDS", "")

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


CSP_HEADER = (
    "default-src 'self';"
    "script-src 'self' 'wasm-unsafe-eval' https://t.me/ https://telegram.me/ https://telegram.org/;"  # <-- ДОБАВЛЕН https://telegram.org/
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;"
    "font-src 'self' https://fonts.gstatic.com;"
    "img-src 'self' data: https://ngrok.com;"
)

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

# bot.py (Новый хелпер для связи с Telegram API)

async def check_subscription_status(telegram_id: int, channel_username: str) -> bool:
    """Проверяет статус подписки пользователя в канале через Bot API."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing.")
        return False
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {
        'chat_id': channel_username,
        'user_id': telegram_id
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    # Сценарий, если бот не админ или API-ошибка (обработка 400)
                    logger.error(f"Telegram API error (getChatMember, Status {resp.status}) for user {telegram_id} in {channel_username}: {await resp.text()}")
                    # Возвращаем False, так как проверку выполнить не удалось
                    return False
                    
                data = await resp.json()
                if data.get('ok'):
                    status = data['result']['status']
                    # Статусы: member, creator, administrator
                    return status in ['member', 'creator', 'administrator']
                else:
                    logger.error(f"Telegram API result not ok: {data.get('description')} for user {telegram_id} in {channel_username}")
                    return False
        except Exception as e:
            logger.error(f"Exception during check_subscription_status: {e}")
            return False

QUEST_CONFIG = {
    'quest_subscribe_channel': {
        'channel_username': '@bebes1114', # <-- Обязательно замените!
        'reward': 0.50,
        'type': 'follow'
    },
    'milestone_watch_5': {
        'reward': 0.75,
        'goal': 5,
        'type': 'milestone'
    }
}

MILESTONE_QUESTS = {
    'milestone_watch_5': {'goal': 5, 'reward': 0.10}
}

# [НОВОЕ] Добавьте конфигурации для FollowQuest
FOLLOW_QUESTS = {
    'quest_subscribe_channel': {
        'channel_username': '@bebes1114', # <-- Обязательно замените!
        'reward': 0.50,
        'type': 'follow'
    },
}


# 1. Используем QUEST_CONFIG, который вы определили:
QUEST_CONFIG_2 = {
    'quest_subscribe_channel': {
        'title': 'Подпишись на наш канал', # [НОВОЕ] Добавьте title, его не было в вашем примере
        'link': 'https://t.me/bebes1114',
        'channel_username': '@bebes1114',
        'reward': 0.50,
        'type': 'follow'
    },
    'milestone_watch_5': {
        'title': 'Посмотри 5 видео', # [НОВОЕ] Добавьте title
        'reward': 0.75,
        'goal': 5,
        'type': 'milestone'
    },
    # Добавьте другие квесты, например:
    'quest_casino_reg': {
        'title': 'Регистрация в Казино',
        'link': 'https://casino.com/ref',
        'channel_username': '@casino_channel', 
        'reward': 1.00,
        'type': 'follow'
    },
}

async def get_quest_config_list(request: web.Request):
    """
    GET /api/quest/get_list
    Возвращает полный список конфигураций квестов.
    """
    quest_list = []
    for quest_id, config in QUEST_CONFIG_2.items():
        # Копируем конфигурацию
        item = config.copy()
        # Добавляем ID в объект
        item['id'] = quest_id
        quest_list.append(item)
        
    return web.json_response(quest_list)

def get_quest_config(quest_id: str) -> dict | None:
    return QUEST_CONFIG.get(quest_id)

def get_channel_username_for_quest(quest_id: str) -> str | None:
    config = get_quest_config(quest_id)
    return config.get('channel_username') if config and config.get('type') == 'follow' else None

def get_quest_reward_amount(quest_id: str) -> float:
    config = get_quest_config(quest_id)
    return config.get('reward', 0.0) if config else 0.0

async def handle_web_app(request):

    html_path = os.path.join(PROJ_ROOT, 'miniapp', 'index.html')
    # Загружаем содержимое index.html
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Создаем текстовый ответ
    response = web.Response(text=html_content, content_type='text/html')
    
    # !!! КРИТИЧЕСКИЙ ШАГ: Добавление заголовка CSP !!!
    response.headers['Content-Security-Policy'] = CSP_HEADER
    
    return response

# Предположим, что награды и цели MilestoneQuest хранятся тут (или в БД)
MILESTONE_QUESTS = {
    'milestone_watch_5': {'goal': 5, 'reward': 0.10}
}

async def verify_quest_handler(request: web.Request):
    data = await request.json()
    quest_id = data.get("quest_id")
    telegram_id = int(data.get("telegram_id"))
    
    # 1. Получаем общую конфигурацию
    config = QUEST_CONFIG_2.get(quest_id)
    if not config: return web.json_response({"error": "Unknown quest"}, status=400)

    # 2. Проверяем тип и логику
    is_valid = False
    if config['type'] == 'follow':
        is_valid = await check_subscription_status(telegram_id, config['channel_username'])
    elif config['type'] == 'milestone':
        user_statuses = await db_manager.quests_db.get_user_quest_statuses(telegram_id)
        current_status = next((s['status'] for s in user_statuses if s['quest_id'] == quest_id), None)
        is_valid = (current_status == 'ready_to_claim')

    # 3. Если проверка прошла — начисляем деньги и закрываем
    if is_valid:
        async with db_manager.users_db.pool.acquire() as conn:
            await conn.execute("UPDATE tg_users SET balance = balance + $1 WHERE telegram_id = $2;", 
                               config['reward'], telegram_id)
        await db_manager.quests_db.set_quest_status(telegram_id, quest_id, 'completed')
        return web.json_response({"isCompleted": True, "reward": config['reward']})
    
    return web.json_response({"isCompleted": False})

async def check_subscription_status(telegram_id: int, channel_username: str) -> bool:
    """Проверяет подписку на канал с помощью Telegram Bot API."""
    if not channel_username or not BOT_TOKEN:
        print("ERROR: BOT_TOKEN or Channel username is missing for quest check.")
        return False
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {
        'chat_id': channel_username,
        'user_id': telegram_id
    }
    
    # Используем aiohttp.ClientSession (предполагая, что он импортирован)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                print(f"Telegram API Error (Status {resp.status}): {await resp.text()}")
                return False
                
            result = await resp.json()
            status = result.get('result', {}).get('status')
            
            # Статусы, указывающие на подписку: member, creator, administrator
            is_subscribed = status in ['member', 'creator', 'administrator']
            return is_subscribed

async def check_milestone_quest_completion(telegram_id: int, counter_key: str, new_count: int):
    """
    Проверяет, достигнута ли цель для квеста просмотра видео.
    Если достигнута и не был завершен/готов ранее, обновляет статус на 'ready_to_claim'.
    """
    if counter_key == 'videos_watched':
        quest_id = 'milestone_watch_5'
        quest_config = MILESTONE_QUESTS.get(quest_id)
        
        if not quest_config:
            return {"is_ready_to_claim": False}

        # 1. Проверяем статус в БД
        user_statuses = await db_manager.quests_db.get_user_quest_statuses(telegram_id)
        current_status = next((s['status'] for s in user_statuses if s['quest_id'] == quest_id), None)
        
        # Награда начисляется ТОЛЬКО при вызове /api/quest/complete
        if new_count >= quest_config['goal'] and current_status not in ['completed', 'ready_to_claim']:
            # 2. Обновляем статус на 'ready_to_claim'
            await db_manager.quests_db.set_quest_status(telegram_id, quest_id, 'ready_to_claim')
            return {"is_ready_to_claim": True}
            
    return {"is_ready_to_claim": False}

# --- НОВЫЙ ОБРАБОТЧИК: check_follow_quest_status_handler ---
async def check_follow_quest_status_handler(request: web.Request):
    """
    POST /api/quest/check
    body: { quest_id: str, telegram_id: int }
    Handles FollowQuest completion check (app.checkQuestStatus).
    """
    try:
        data = await request.json()
        quest_id = data.get("quest_id")
        telegram_id = data.get("telegram_id")
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if not quest_id or not telegram_id:
        return web.json_response({"error": "Missing fields"}, status=400)
        
    quest_config = FOLLOW_QUESTS.get(quest_id)

    if not quest_config:
         return web.json_response({"status": "error", "error": "FollowQuest not configured"}, status=400)

    channel_username = quest_config.get('channel_username') # !!! НУЖНО ПОЛУЧИТЬ ЮЗЕРНЕЙМ !!!
    if not channel_username:
         return web.json_response({"status": "error", "error": "Channel username missing in config"}, status=400)

    reward = quest_config['reward']
    
    # 1. Проверяем текущий статус (должен быть 'visited' или null)
    user_statuses = await db_manager.quests_db.get_user_quest_statuses(telegram_id)
    current_status = next((s['status'] for s in user_statuses if s['quest_id'] == quest_id), None)
    

    is_external_check_successful = await check_subscription_status(telegram_id, channel_username)
    # ********************************************************************************************
    
    if is_external_check_successful:
        # 2. Начисляем награду и обновляем статус
        async with db_manager.users_db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE tg_users SET balance = balance + $1 WHERE telegram_id = $2;",
                reward, telegram_id
            )
        await db_manager.quests_db.set_quest_status(telegram_id, quest_id, 'completed')
        
        return web.json_response({
            "status": "ok",
            "isCompleted": True,
            "reward": reward
        })
    else:
        await db_manager.quests_db.set_quest_status(telegram_id, quest_id, 'initial')      
        return web.json_response({"status": "ok", "isCompleted": False})
    
    # Если статус не 'visited' или внешняя проверка не прошла
    return web.json_response({"status": "ok", "isCompleted": False}) # isCompleted: false соответствует quests.js


# --- НОВЫЙ ОБРАБОТЧИК: complete_quest_handler ---
async def complete_quest_handler(request: web.Request):
    """
    POST /api/quest/complete
    body: { quest_id: str, telegram_id: int }
    Handles MilestoneQuest reward claiming (app.completeQuest).
    """
    try:
        data = await request.json()
        quest_id = data.get("quest_id")
        telegram_id = data.get("telegram_id")
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if not quest_id or not telegram_id:
        return web.json_response({"error": "Missing fields"}, status=400)
        
    quest_config = MILESTONE_QUESTS.get(quest_id)
    if not quest_config:
         return web.json_response({"status": "error", "error": "MilestoneQuest not configured"}, status=400)

    reward = quest_config['reward']
    
    # 1. Проверяем, готов ли квест к получению награды (статус 'ready_to_claim')
    user_statuses = await db_manager.quests_db.get_user_quest_statuses(telegram_id)
    current_status = next((s['status'] for s in user_statuses if s['quest_id'] == quest_id), None)
    
    if current_status == 'ready_to_claim':
        # 2. Начисляем награду и обновляем статус
        async with db_manager.users_db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE tg_users SET balance = balance + $1 WHERE telegram_id = $2;",
                reward, telegram_id
            )
        await db_manager.quests_db.set_quest_status(telegram_id, quest_id, 'completed')
        
        return web.json_response({
            "status": "ok",
            "isCompleted": True,
            "reward": reward
        })
    
    # Если не готов к получению
    return web.json_response({"status": "ok", "isCompleted": False})


async def mark_quest_visited(request):
    quest_db: db.QuestStatusDBManager = request.app['db_manager'].quests_db
    try:
        data = await request.json()
        
        # Получаем telegram_id из заголовка или данных (ВАЖНО: откуда вы его берете?)
        # В идеале, telegram_id должен идти через заголовок X-Telegram-User-ID, 
        # но пока возьмем из тела, как и предполагалось:
        telegram_id = data.get('telegram_id')
        quest_id = data.get('quest_id')
        
        if not telegram_id or not quest_id:
            return web.json_response({'status': 'error', 'error': 'Missing data'}, status=400)
            
        telegram_id = int(telegram_id) # Убеждаемся, что это число
        
        # !!! ИСПОЛЬЗУЕМ ВАШУ ФУНКЦИЮ БД !!!
        await quest_db.set_quest_status(telegram_id, quest_id, 'visited')
        
        print(f"✅ Quest {quest_id} marked as VISITED for user {telegram_id}.")
        return web.json_response({'status': 'ok', 'message': 'Status set to visited'})

    except ValueError:
        return web.json_response({'status': 'error', 'error': 'Invalid telegram_id format'}, status=400)
    except Exception as e:
        print(f"Error in mark_quest_visited: {e}")
        return web.json_response({'status': 'error', 'error': 'Internal server error'}, status=500)

async def check_quest_status(request):
    db_manager: db.DatabaseManager = request.app['db_manager']
    db_quests: db.QuestStatusDBManager = db_manager.quests_db
    db_users: db.UsersDBManager = db_manager.users_db
    
    try:
        telegram_id = request.query.get('telegram_id')
        quest_id = request.query.get('quest_id')
        
        if not telegram_id or not quest_id:
            return web.json_response({'isCompleted': False, 'error': 'Missing ID'}, status=400)
            
        telegram_id = int(telegram_id)
        
        config = get_quest_config(quest_id)
        if not config:
            return web.json_response({'isCompleted': False, 'error': 'Quest not found'}, status=404)

        # --- 1. Логика FollowQuest (Подписка) ---
        if config['type'] == 'follow':
            channel_username = get_channel_username_for_quest(quest_id)
            if not channel_username:
                 return web.json_response({'isCompleted': False, 'error': 'Channel link missing'}, status=400)
            
            is_subscribed = await check_subscription_status(telegram_id, channel_username)
            
            if is_subscribed:
                reward = get_quest_reward_amount(quest_id)
                
                # 2. Обновляем статус в БД на 'completed'
                await db_quests.set_quest_status(telegram_id, quest_id, 'completed')
                
                # 3. Увеличиваем баланс пользователя
                # ВАЖНО: Ваша БД имеет только 'update_balance', поэтому нам нужно получить текущий баланс
                user_record = await db_users.get_user_by_telegram_id(telegram_id)
                if user_record:
                    new_balance = user_record['balance'] + reward
                    await db_users.update_balance(telegram_id, new_balance)
                
                print(f"🎉 Follow Quest {quest_id} completed for user {telegram_id}. Reward: {reward}")
                
                return web.json_response({
                    'isCompleted': True, 
                    'reward': reward 
                })
            else:
                return web.json_response({'isCompleted': False, 'reward': 0})
                
        # --- 2. Логика MilestoneQuest (Просмотры) ---
        elif config['type'] == 'milestone':
             # Эта логика должна быть отдельной, т.к. фронтенд вызывает completeQuest, а не checkQuestStatus
             # Но для простоты: проверяем, достигнута ли цель
             current_count = await db_manager.counters_db.get_counter(telegram_id, 'videos_watched')
             if current_count >= config['goal']:
                 # Логика получения награды
                 reward = get_quest_reward_amount(quest_id)
                 await db_quests.set_quest_status(telegram_id, quest_id, 'completed')
                 
                 user_record = await db_users.get_user_by_telegram_id(telegram_id)
                 if user_record:
                     new_balance = user_record['balance'] + reward
                     await db_users.update_balance(telegram_id, new_balance)
                     
                 print(f"🎉 Milestone Quest {quest_id} completed for user {telegram_id}. Reward: {reward}")

                 return web.json_response({'isCompleted': True, 'reward': reward})
             
             return web.json_response({'isCompleted': False, 'reward': 0})

    except ValueError:
        return web.json_response({'isCompleted': False, 'error': 'Invalid ID format'}, status=400)
    except Exception as e:
        print(f"Error in check_quest_status: {e}")
        return web.json_response({'isCompleted': False, 'error': 'Internal server error'}, status=500)

# Обновленный video_watched_handler
async def video_watched_handler(request: web.Request):
    """
    POST /api/video/watched
    Отмечает просмотр видео и проверяет выполнение MilestoneQuest.
    """
    try:
        data = await request.json()
        telegram_id = data.get("telegram_id")
        video_id = data.get("video_id")
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    if not telegram_id or not video_id:
        return web.json_response({"error": "Missing fields"}, status=400)

    # 1. Увеличиваем общий счетчик просмотров видео в таблице `videos`
    await db_manager.videos_db.increment_watched(video_id)

    # 2. Увеличиваем счетчик просмотров ДЛЯ ПОЛЬЗОВАТЕЛЯ в новой таблице `user_counters`
    new_count = await db_manager.counters_db.increment_counter(
        telegram_id=telegram_id, 
        counter_key='videos_watched'
    )

    # 3. Проверяем, выполнил ли пользователь квест
    quest_result = await check_milestone_quest_completion(telegram_id, 'videos_watched', new_count)

    return web.json_response({
        "status": "ok",
        "videos_watched_count": new_count,
        "quest_completed": quest_result["is_completed"]
    })

async def save_user_to_db(user, timezone: str | None = None):
    if not db_manager.users_db:
        logger.warning("save_user_to_db: users_db not initialized")
        return
    await db_manager.users_db.add_user(
        telegram_id=user.id,
        username=getattr(user, "username", None),
        first_name=getattr(user, "first_name", None),
        last_name=getattr(user, "last_name", None),
        language_code=getattr(user, "language_code", None),
        timezone=timezone,
        is_premium=getattr(user, "is_premium", False)
    )

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

async def fetch_bot_stats() -> str:
    if not db_manager.users_db or not db_manager.users_db.pool:
        return "DB not connected"
        
    async with db_manager.users_db.pool.acquire() as conn:
        
        # 1. СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ
        users = await conn.fetchval("SELECT count(*) FROM tg_users") or 0
        today_users = await conn.fetchval("SELECT count(*) FROM tg_users WHERE created_at::date = current_date") or 0
        refs = await conn.fetchval("""
            SELECT count(*) 
            FROM (SELECT unnest(referrals) FROM tg_users) s(id) 
            WHERE id IS NOT NULL
        """) or 0
        
        # 2. СТАТИСТИКА ВИДЕО (ПРОСМОТРЫ)
        # Total watched (берется из таблицы videos, столбец watched)
        total_watched = await conn.fetchval("SELECT COALESCE(SUM(watched), 0) FROM videos")
        
        # Watched Today (берется из daily_statistics, если менеджер статистики запускается ежедневно)
        today_watched = await conn.fetchval(
            "SELECT videos_watched FROM daily_statistics WHERE stat_date = current_date"
        ) or 0
        
    stats_text = (
    f"📊 <b>ОБЩАЯ СТАТИСТИКА БОТА</b>\n"
    f"—————————————————————\n"
    f"👤 <b>ПОЛЬЗОВАТЕЛИ</b>\n"
    f"— Всего пользователей: <b>{users}</b>\n"
    f"— Новых сегодня: <b>{today_users}</b>\n"
    f"— Рефералов: <b>{refs}</b>\n"
    f"—————————————————————\n"
    f"🎥 <b>ВИДЕО / РЕКЛАМА</b>\n"
    f"— Просмотров всего: <b>{total_watched}</b>\n"
    f"— Просмотров сегодня: <b>{today_watched}</b>\n"
    )
    return stats_text



# -------------------- Функция отправки бродкаста --------------------
async def create_broadcast(data: dict):
    name = data["name"]
    media_file_id = data.get("media_file_id") 
    media_type = data.get("media_type")
    title = data["title"]
    text = data["text"]
    button_text = data["button_text"]
    link=data["button_link"]

    
    await db_manager.mailing_db.add_broadcast(name, title, text, media_file_id, media_type, button_text, link)


# -------------------- Функция отправки бродкаста --------------------
async def send_broadcast(data: dict):
    name = data["name"] # Используем name, чтобы найти рассылку

    # 1. Находим данные рассылки по имени
    mailing_data = await db_manager.mailing_db.get_mailing_by_name(name)
    
    if not mailing_data:
        print(f"Ошибка: Рассылка с именем '{name}' не найдена в базе данных.")
        return None
    
    # ID шаблона (повторно используемый контент)
    mailing_id = mailing_data['id']
    
    try:
        run_id = await db_manager.mailing_db.start_new_run(mailing_id)
    except Exception as e:
        logger.error(f"Не удалось создать run_id для mailing_id {mailing_id}: {e}")
        return None
    

    # 2. Извлекаем данные из БД
    broadcast_id = mailing_data['id']
    media_file_id = mailing_data['media_url']
    media_type = mailing_data['media_type']  # <-- Используем тип из БД
    title = mailing_data['title']
    text = mailing_data['text']
    button_text = mailing_data['button_text']
    link = mailing_data['button_link']

    # --- Подготовка к рассылке ---
    user_ids = await db_manager.get_all_users() 
    caption = f"{title}\n{text}"
    
    # Создание клавиатуры
    markup = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text=button_text, url=link)
        ]])
    
    for user_id in user_ids:
        try:
            # 3. Отправка в зависимости от media_type
            if media_file_id and media_type:
                
                # Используем тип, сохраненный в БД, для выбора правильного метода
                if media_type == ContentType.PHOTO.value:
                    await bot.send_photo(user_id, photo=media_file_id, caption=caption, reply_markup=markup)
                elif media_type == ContentType.VIDEO.value:
                    await bot.send_video(user_id, video=media_file_id, caption=caption, reply_markup=markup)
                elif media_type == ContentType.ANIMATION.value:
                    await bot.send_animation(user_id, animation=media_file_id, caption=caption, reply_markup=markup)
                elif media_type == ContentType.DOCUMENT.value:
                    await bot.send_document(user_id, document=media_file_id, caption=caption, reply_markup=markup)
                else:
                    # Если тип медиа не распознан, отправляем как документ (наиболее универсально)
                    await bot.send_document(user_id, document=media_file_id, caption=caption, reply_markup=markup)
                    
            else:
                # Если медиафайла нет, отправляем простое текстовое сообщение
                await bot.send_message(user_id, text=caption, reply_markup=markup)

            await db_manager.mailing_db.log_stat(run_id, user_id, "sent")
            
        except Exception as e:
            await db_manager.mailing_db.log_stat(run_id, user_id, "failed")
            print(f"Не удалось отправить {user_id}: {e}")

    return run_id

# ---------- Webapp endpoints ----------
async def get_random_video(request: web.Request):
    """
    GET /api/video/random?initData=<initData>
    Проверяет initData (если доступна проверка). Возвращает JSON с полным video_url.
    """
    # get initData from query (frontend should pass Telegram.WebApp.initData)
    init_data = request.query.get("initData")
    if not init_data:
        return web.json_response({"error": "Missing initData"}, status=400)

    # validate initData if helper available
    if check_webapp_signature:
        try:
            valid = check_webapp_signature(bot.token, init_data)
        except Exception:
            valid = False
    else:
        # Если нет helper-а — логим и временно разрешаем (в проде лучше иметь проверку)
        logger.warning("check_webapp_signature not available in aiogram — skipping initData validation")
        valid = True

    if not valid:
        return web.json_response({"error": "Invalid initData"}, status=403)

    # Получаем случайное видео из БД
    video = await db_manager.videos_db.get_random_video()
    if not video:
        return web.json_response({"error": "No videos found"}, status=404)

    vurl = video["video_url"]
    # если в БД относительный путь, делаем абсолютный на основе request
    if not vurl.startswith("http://") and not vurl.startswith("https://"):
        scheme = "https" # Принудительно ставим https, так как у нас есть SSL
        host = request.headers.get("Host")
        
        # Гарантируем, что путь начинается с ОДНОГО слэша
        path = vurl if vurl.startswith("/") else f"/{vurl}"
        
        # Убираем возможный слэш в конце хоста и склеиваем
        vurl = f"{scheme}://{host.rstrip('/')}{path}"

    logger.info(f"Sending video URL to frontend: {vurl}") # Добавим лог в консоль сервера

    return web.json_response({
        "id": video["id"],
        "title": video["title"],
        "video_url": vurl
    })


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
async def get_quests_statuses(request: web.Request):
    """
    GET /api/quest/statuses?telegram_id=<id>
    Возвращает JSON с текущими статусами квестов пользователя.
    """
    telegram_id_str = request.query.get("telegram_id")
    if not telegram_id_str:
        return web.json_response({"error": "Missing telegram_id"}, status=400)
    
    try:
        telegram_id = int(telegram_id_str)
    except ValueError:
        return web.json_response({"error": "Invalid telegram_id"}, status=400)
        
    # 1. Получаем статусы квестов
    quests_statuses = await db_manager.quests_db.get_user_quest_statuses(telegram_id)
    
    # 2. Получаем баланс
    user = await db_manager.users_db.get_user_by_telegram_id(telegram_id) # Предполагается, что такой метод есть
    if not user:
        return web.json_response({"error": "User not found"}, status=404)
    balance = float(user['balance'])
    
    # 3. Получаем текущий счетчик просмотров видео
    videos_watched_count = await db_manager.counters_db.get_counter(telegram_id, 'videos_watched')
    
    # 4. Формируем ответ
    return web.json_response({
        "status": "ok",
        "balance": balance,
        "quests": quests_statuses,
        "counters": {
            "videos_watched": videos_watched_count
        }
    })


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