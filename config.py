import os
from dotenv import load_dotenv
import pathlib

load_dotenv() # Загружаем переменные из .env

# Серверные настройки
PORT = int(os.getenv("PORT_NEW", "8080"))
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST_NEW")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH_NEW", "/webhook")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN_NEW")

WEBHOOK_URL_FINAL = os.getenv("WEBHOOK_URL_NEW_FINAL")

admin_ids_raw = os.getenv("ADMIN_IDS", "")

PROJ_ROOT = pathlib.Path(__file__).parent.resolve()


# Токены
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET_TOKEN_NEW")

# Конфиги квестов (которые нельзя в .env)
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


CSP_HEADER = (
    "default-src 'self';"
    "script-src 'self' 'wasm-unsafe-eval' https://t.me/ https://telegram.me/ https://telegram.org/;"  # <-- ДОБАВЛЕН https://telegram.org/
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;"
    "font-src 'self' https://fonts.gstatic.com;"
    "img-src 'self' data: https://ngrok.com;"
)