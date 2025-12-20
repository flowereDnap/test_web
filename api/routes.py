import os
import aiohttp
import logging
from aiohttp import web
from config import (
    QUEST_CONFIG_2, PROJ_ROOT, CSP_HEADER, BOT_TOKEN
)

# Проверка подписи WebApp
try:
    from aiogram.utils.web_app import check_webapp_signature
except ImportError:
    try:
        from aiogram.utils.web_app import check_web_app_signature as check_webapp_signature
    except ImportError:
        check_webapp_signature = None

logger = logging.getLogger(__name__)

# --- Вспомогательные функции ---

async def check_subscription_status(telegram_id: int, channel_username: str, session: aiohttp.ClientSession) -> bool:
    """
    Проверяет, подписан ли юзер на канал.
    """
    if not channel_username or not BOT_TOKEN:
        logger.error("Missing channel_username or BOT_TOKEN for subscription check")
        return False
    
    chat_id = channel_username if channel_username.startswith('@') else f"@{channel_username}"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {'chat_id': chat_id, 'user_id': telegram_id}
    
    try:
        async with session.get(url, params=params, timeout=5) as resp:
            if resp.status != 200:
                return False
            result = await resp.json()
            status = result.get('result', {}).get('status')
            # 'left' или 'kicked' означают отсутствие подписки
            return status in ['member', 'creator', 'administrator']
    except Exception as e:
        logger.error(f"Telegram API Error (Subscription): {e}")
        return False

# --- Обработчики API ---

async def handle_web_app(request):
    """Отдает index.html для Mini App."""
    html_path = os.path.join(PROJ_ROOT, 'miniapp', 'index.html')
    if not os.path.exists(html_path):
        return web.Response(text="Index file not found", status=404)
        
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    response = web.Response(text=html_content, content_type='text/html')
    response.headers['Content-Security-Policy'] = CSP_HEADER
    return response

async def get_quests_statuses(request: web.Request):
    """GET /api/quest/statuses?telegram_id=..."""
    telegram_id = request.query.get("telegram_id")
    if not telegram_id:
        return web.json_response({"error": "Missing telegram_id"}, status=400)
    
    db_manager = request.app['db_manager']
    t_id = int(telegram_id)
    
    quests_statuses = await db_manager.quests_db.get_user_quest_statuses(t_id)
    user = await db_manager.users_db.get_user_by_telegram_id(t_id)
    
    if not user:
        return web.json_response({"error": "User not found"}, status=404)
        
    videos_watched_count = await db_manager.counters_db.get_counter(t_id, 'videos_watched')
    
    return web.json_response({
        "status": "ok",
        "balance": float(user['balance']),
        "quests": quests_statuses,
        "counters": {"videos_watched": videos_watched_count}
    })

async def get_quest_config_list(request: web.Request):
    """GET /api/quest/get_list"""
    # Теперь отдаем список из единого конфига QUEST_CONFIG_2
    quest_list = [{"id": k, **v} for k, v in QUEST_CONFIG_2.items()]
    return web.json_response(quest_list)

async def mark_quest_visited(request: web.Request):
    """POST /api/quest/visited"""
    data = await request.json()
    t_id = int(data.get('telegram_id'))
    q_id = data.get('quest_id')
    
    await request.app['db_manager'].quests_db.set_quest_status(t_id, q_id, 'visited')
    return web.json_response({'status': 'ok'})

async def verify_quest_handler(request: web.Request):
    """
    УНИВЕРСАЛЬНЫЙ хендлер проверки (заменяет complete_quest_handler и check_follow_quest_status_handler)
    """
    data = await request.json()
    quest_id = data.get("quest_id")
    telegram_id = int(data.get("telegram_id"))
    
    db_manager = request.app['db_manager']
    config = QUEST_CONFIG_2.get(quest_id)
    
    if not config:
        return web.json_response({"error": "Unknown quest"}, status=400)

    user_statuses = await db_manager.quests_db.get_user_quest_statuses(telegram_id)
    current_status = next((s['status'] for s in user_statuses if s['quest_id'] == quest_id), None)

    if current_status == 'completed':
        return web.json_response({"isCompleted": True, "reward": 0, "message": "Already rewarded"})

    is_valid = False
    
    if config['type'] == 'follow':
        is_valid = await check_subscription_status(telegram_id, config['channel_username'], request.app['http_session'])
    
    elif config['type'] == 'milestone':
        if current_status == 'ready_to_claim':
            is_valid = True
        else:
            current_count = await db_manager.counters_db.get_counter(telegram_id, 'videos_watched')
            is_valid = current_count >= config.get('goal', 999)

    if is_valid:
        reward = config['reward']
        # Атомарно прибавляем баланс
        await db_manager.users_db.update_balance(telegram_id, reward)
        await db_manager.quests_db.set_quest_status(telegram_id, quest_id, 'completed')
        return web.json_response({"isCompleted": True, "reward": reward})
    
    return web.json_response({"isCompleted": False})

async def video_watched_handler(request: web.Request):
    """POST /api/video/watched"""
    try:
        data = await request.json()
        t_id = int(data.get("telegram_id"))
        v_id = data.get("video_id")
        
        db_manager = request.app['db_manager']
        await db_manager.videos_db.increment_watched(v_id)
        new_count = await db_manager.counters_db.increment_counter(t_id, 'videos_watched')
        
        # Автоматический перевод в ready_to_claim для всех подходящих милстоунов
        newly_ready = []
        for q_id, q_cfg in QUEST_CONFIG_2.items():
            if q_cfg.get('type') == 'milestone' and new_count >= q_cfg.get('goal', 999):
                user_statuses = await db_manager.quests_db.get_user_quest_statuses(t_id)
                current_status = next((s['status'] for s in user_statuses if s['quest_id'] == q_id), None)
                if current_status not in ['completed', 'ready_to_claim']:
                    await db_manager.quests_db.set_quest_status(t_id, q_id, 'ready_to_claim')
                    newly_ready.append(q_id)

        return web.json_response({"status": "ok", "videos_watched_count": new_count, "newly_ready": newly_ready})
    except Exception as e:
        logger.error(f"Error: {e}")
        return web.json_response({"error": "Internal error"}, status=500)

async def get_random_video(request: web.Request):
    """GET /api/video/random"""
    init_data = request.query.get("initData")
    bot = request.app['bot']
    
    if check_webapp_signature and not check_webapp_signature(bot.token, init_data):
        return web.json_response({"error": "Invalid auth"}, status=403)

    video = await request.app['db_manager'].videos_db.get_random_video()
    if not video:
        return web.json_response({"error": "No videos"}, status=404)

    vurl = video["video_url"]
    if not vurl.startswith("http"):
        host = request.headers.get("Host")
        vurl = f"https://{host}/{vurl.lstrip('/')}"

    return web.json_response({"id": video["id"], "title": video["title"], "video_url": vurl})