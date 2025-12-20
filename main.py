import os
import asyncio
import pathlib
import aiohttp
import logging
from aiohttp import web

# Импорт бота, диспетчера и конфига
from init_bot import bot, dp, logger
from config import (
    WEBHOOK_URL_FINAL, WEBHOOK_PATH, WEBHOOK_SECRET_TOKEN, 
    PORT, PROJ_ROOT
)
from db import db_manager

# Импорт роутеров бота
from handlers.comands import router as commands_router
from handlers.admin_menu import router as admin_router

# Импорт актуальных обработчиков API
from api.routes import (
    handle_web_app,
    get_random_video,
    video_watched_handler,
    mark_quest_visited,
    get_quest_config_list,
    verify_quest_handler,
    get_quests_statuses  # Мы переименовали старый check_quest_status в это
)

# Подключаем роутеры бота
dp.include_router(commands_router)
dp.include_router(admin_router)

# ---------- Жизненный цикл приложения ----------

async def on_startup(app):
    app['http_session'] = aiohttp.ClientSession()
    app['db_manager'] = db_manager
    app['bot'] = bot
    logger.info("Application startup: HTTP session and Bot objects are ready.")

async def on_shutdown(app):
    logger.info("Shutting down application...")
    try:
        await bot.delete_webhook()
    except: pass
    await app['http_session'].close()
    await bot.session.close()
    if db_manager.pool:
        await db_manager.close()
    logger.info("Application shutdown complete.")

# ---------- Обработка Webhook ----------

async def handle_webhook(request: web.Request):
    secret = request.match_info.get("secret")
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")

    if secret != WEBHOOK_SECRET_TOKEN and header_secret != WEBHOOK_SECRET_TOKEN:
        return web.Response(status=403, text="Forbidden")

    try:
        from aiogram.types import Update
        body = await request.json()
        update = Update.model_validate(body, context={"bot": bot})
        await dp.feed_update(bot=bot, update=update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return web.Response(status=500)
    
    return web.Response(status=200, text="OK")

async def setup_telegram():
    webhook_url = f"{WEBHOOK_URL_FINAL}{WEBHOOK_PATH}/telegram/{WEBHOOK_SECRET_TOKEN}"
    await bot.set_webhook(
        url=webhook_url,
        secret_token=WEBHOOK_SECRET_TOKEN,
        drop_pending_updates=True
    )
    
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="admin", description="👑 Админ-панель")
    ])
    logger.info(f"Webhook set: {webhook_url}")

# ---------- Middleware ----------

@web.middleware
async def cors_middleware(request, handler):
    if request.method == 'OPTIONS':
        return web.Response(status=200, headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Requested-With',
        })
    resp = await handler(request)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

# ---------- Запуск сервера ----------

async def start_app():
    # 1. БД
    await db_manager.setup()

    # 2. Приложение
    app = web.Application(middlewares=[cors_middleware])
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # 3. Маршруты (API)
    app.router.add_get('/', handle_web_app)
    app.router.add_get("/api/video/random", get_random_video)
    app.router.add_post("/api/video/watched", video_watched_handler)
    
    # Квесты (Используем только универсальные пути)
    app.router.add_get('/api/quest/get_list', get_quest_config_list)
    app.router.add_get('/api/quest/statuses', get_quests_statuses) 
    app.router.add_post('/api/quest/verify', verify_quest_handler)
    app.router.add_post('/api/quest/visited', mark_quest_visited)

    # Вебхук
    app.router.add_post(f"{WEBHOOK_PATH}/telegram/{{secret}}", handle_webhook)

    # 4. Статика
    app.router.add_static('/assets', path=str(pathlib.Path(PROJ_ROOT) / "miniapp"), show_index=False)
    vids_path = pathlib.Path(PROJ_ROOT) / "vids"
    if vids_path.exists():
        app.router.add_static('/vids', path=str(vids_path), show_index=False)

    # 5. Старт
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    
    await setup_telegram()
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(start_app())
    except KeyboardInterrupt:
        pass