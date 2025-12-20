import os
from config import WEBHOOK_HOST

from aiogram.types import (
    Message, 
    CallbackQuery, 
    WebAppInfo, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    Update,
    InputFile
)


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
