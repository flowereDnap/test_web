import os
import pathlib
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv() # Загружаем переменные из .env

# Серверные настройки
PORT = int(os.getenv("PORT_NEW", "8080"))
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST_NEW")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH_NEW", "/webhook")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN_NEW")

WEBHOOK_URL_FINAL = os.getenv("WEBHOOK_URL_NEW_FINAL")

admin_ids_raw = os.getenv("ADMIN_IDS", "")

try:
    ADMIN_IDS = []
    if admin_ids_raw:
        for item in admin_ids_raw.split(","):
            item = item.strip()
            if item.isdigit():
                ADMIN_IDS.append(int(item))
except Exception as e:
    # Теперь logger определен и ошибки не будет
    logger.error(f"Error parsing ADMIN_IDS: {e}")
    ADMIN_IDS = []

PROJ_ROOT = pathlib.Path(__file__).parent.resolve()

# Токены
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET_TOKEN_NEW")

# Конфиги квестов
QUEST_CONFIG = {
    'quest_subscribe_channel': {
        'channel_username': '@bebes1114',
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

FOLLOW_QUESTS = {
    'quest_subscribe_channel': {
        'channel_username': '@bebes1114',
        'reward': 0.50,
        'type': 'follow'
    },
}

QUEST_CONFIG_2 = {
    'quest_subscribe_channel': {
        'title': 'Подпишись на наш канал',
        'link': 'https://t.me/bebes1114',
        'channel_username': '@bebes1114',
        'reward': 0.50,
        'type': 'follow'
    },
    'milestone_watch_5': {
        'title': 'Посмотри 5 видео',
        'reward': 0.75,
        'goal': 5,
        'type': 'milestone'
    },
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
    "script-src 'self' 'wasm-unsafe-eval' https://t.me/ https://telegram.me/ https://telegram.org/;"
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;"
    "font-src 'self' https://fonts.gstatic.com;"
    "img-src 'self' data: https://ngrok.com;"
)