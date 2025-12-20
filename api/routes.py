from aiohttp import web
import os
import aiohttp
import logging
from config import QUEST_CONFIG, QUEST_CONFIG_2, PROJ_ROOT, CSP_HEADER, BOT_TOKEN, MILESTONE_QUESTS, FOLLOW_QUESTS
import db

try:
    from aiogram.utils.web_app import check_webapp_signature
except ImportError:
    try:
        from aiogram.utils.web_app import check_web_app_signature as check_webapp_signature
    except ImportError:
        check_webapp_signature = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    quests_statuses = await request.app['db_manager'].quests_db.get_user_quest_statuses(telegram_id)
    
    # 2. Получаем баланс
    user = await request.app['db_manager'].users_db.get_user_by_telegram_id(telegram_id) # Предполагается, что такой метод есть
    if not user:
        return web.json_response({"error": "User not found"}, status=404)
    balance = float(user['balance'])
    
    # 3. Получаем текущий счетчик просмотров видео
    videos_watched_count = await request.app['db_manager'].counters_db.get_counter(telegram_id, 'videos_watched')
    
    # 4. Формируем ответ
    return web.json_response({
        "status": "ok",
        "balance": balance,
        "quests": quests_statuses,
        "counters": {
            "videos_watched": videos_watched_count
        }
    })


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


async def verify_quest_handler(request: web.Request):
    try:
        data = await request.json()
        quest_id = data.get("quest_id")
        telegram_id = int(data.get("telegram_id"))
    except Exception:
        return web.json_response({"error": "Invalid JSON or ID"}, status=400)

    # Получаем конфиг (убедись, что он общий для всех типов)
    config = QUEST_CONFIG_2.get(quest_id)
    if not config: 
        return web.json_response({"error": "Unknown quest"}, status=400)

    # ПРОВЕРКА: Не выполнен ли уже этот квест? (Защита от абуза)
    user_statuses = await request.app['db_manager'].quests_db.get_user_quest_statuses(telegram_id)
    current_status = next((s['status'] for s in user_statuses if s['quest_id'] == quest_id), None)
    
    if current_status == 'completed':
        return web.json_response({"isCompleted": True, "reward": 0, "message": "Already rewarded"})

    is_valid = False
    
    # ЛОГИКА: Подписка
    if config['type'] == 'follow':
        # Используем общую сессию из app
        is_valid = await check_subscription_status(
            telegram_id, 
            config['channel_username'], 
            request.app['http_session']
        )
    
    # ЛОГИКА: Достижение (просмотры)
    elif config['type'] == 'milestone':
        # Квест считается валидным, если видео просмотрено >= цели
        # Мы можем проверить это напрямую по счетчику, не полагаясь только на 'ready_to_claim'
        current_count = await db_manager.counters_db.get_counter(telegram_id, 'videos_watched')
        is_valid = current_count >= config.get('goal', 99999)

    # 3. Если проверка прошла — начисляем награду
    if is_valid:
        reward = config['reward']
        # Используем метод твоей БД для обновления баланса
        user_record = await request.app['db_manager'].users_db.get_user_by_telegram_id(telegram_id)
        if user_record:
            new_balance = user_record['balance'] + reward
            await request.app['db_manager'].users_db.update_balance(telegram_id, new_balance)
            
        # Фиксируем выполнение
        await request.app['db_manager'].quests_db.set_quest_status(telegram_id, quest_id, 'completed')
        
        return web.json_response({
            "isCompleted": True, 
            "reward": reward
        })
    
    return web.json_response({"isCompleted": False})

async def check_subscription_status(telegram_id: int, channel_username: str, session: aiohttp.ClientSession) -> bool:
    if not channel_username or not BOT_TOKEN:
        return False
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {'chat_id': channel_username, 'user_id': telegram_id}
    
    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200: return False
            result = await resp.json()
            status = result.get('result', {}).get('status')
            return status in ['member', 'creator', 'administrator']
    except Exception as e:
        logger.error(f"Telegram API Error: {e}")
        return False

async def check_milestone_quest_completion(telegram_id: int, counter_key: str, new_count: int, db_manager):
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
    user_statuses = await request.app['db_manager'].quests_db.get_user_quest_statuses(telegram_id)
    current_status = next((s['status'] for s in user_statuses if s['quest_id'] == quest_id), None)
    

    is_external_check_successful = await check_subscription_status(telegram_id, channel_username)
    # ********************************************************************************************
    
    if is_external_check_successful:
        # 2. Начисляем награду и обновляем статус
        async with request.app['db_manager'].users_db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE tg_users SET balance = balance + $1 WHERE telegram_id = $2;",
                reward, telegram_id
            )
        await request.app['db_manager'].quests_db.set_quest_status(telegram_id, quest_id, 'completed')
        
        return web.json_response({
            "status": "ok",
            "isCompleted": True,
            "reward": reward
        })
    else:
        await request.app['db_manager'].quests_db.set_quest_status(telegram_id, quest_id, 'initial')      
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
    user_statuses = await request.app['db_manager'].quests_db.get_user_quest_statuses(telegram_id)
    current_status = next((s['status'] for s in user_statuses if s['quest_id'] == quest_id), None)
    
    if current_status == 'ready_to_claim':
        # 2. Начисляем награду и обновляем статус
        async with request.app['db_manager'].users_db.pool.acquire() as conn:
            await conn.execute(
                "UPDATE tg_users SET balance = balance + $1 WHERE telegram_id = $2;",
                reward, telegram_id
            )
        await request.app['db_manager'].quests_db.set_quest_status(telegram_id, quest_id, 'completed')
        
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
            
            is_subscribed = await check_subscription_status(telegram_id, channel_username, request.app['http_session'])
            
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
    await request.app['db_manager'].videos_db.increment_watched(video_id)

    # 2. Увеличиваем счетчик просмотров ДЛЯ ПОЛЬЗОВАТЕЛЯ в новой таблице `user_counters`
    new_count = await request.app['db_manager'].counters_db.increment_counter(
        telegram_id=telegram_id, 
        counter_key='videos_watched'
    )

    # 3. Проверяем, выполнил ли пользователь квест
    quest_result = await check_milestone_quest_completion(telegram_id, 'videos_watched', new_count, db_manager=request.app['db_manager'])

    return web.json_response({
        "status": "ok",
        "videos_watched_count": new_count,
        "quest_completed": quest_result["is_ready_to_claim"]
    })

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
            bot = request.app['bot'] 
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
    video = await request.app['db_manager'].videos_db.get_random_video()
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