import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramAPIError, TelegramBadRequest

# Импортируем конфиг для получения списка админов
from config import ADMIN_IDS

# Настройка логгера
logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором."""
    return int(user_id) in ADMIN_IDS

async def save_referral(new_user_id: int, ref_payload: str, db_manager):
    """
    Записывает информацию о реферале. 
    Теперь принимает db_manager как аргумент.
    """
    if not db_manager.users_db:
        logger.warning("save_referral: users_db not initialized")
        return
    try:
        ref_id = int(ref_payload)
        # Если пользователь пытается пригласить сам себя
        if ref_id == new_user_id:
            return
    except (ValueError, TypeError):
        # Payload не числовой (например, строковая метка)
        return
        
    try:
        await db_manager.users_db.add_referral(referrer_id=ref_id, referral_id=new_user_id)
    except Exception as e:
        logger.error(f"Ошибка при сохранении реферала: {e}")

async def send_broadcast(data: dict, bot: Bot, db_manager):
    """
    Безопасная рассылка с поддержкой медиа и фоновым выполнением.
    """
    id = data.get("id")
    if not id:
        logger.error("send_broadcast: В данных отсутствует 'id'")
        return None
    
    run_id = await db_manager.mailing_db.start_new_run(id)

    mailing_data = await db_manager.mailing_db.get_mailing_by_run_id(id)
    if not mailing_data:
        return None
    

    media_file_id = mailing_data.get('media_url')
    media_type = mailing_data.get('media_type')
    caption = f"<b>{mailing_data['title']}</b>\n\n{mailing_data['text']}" if mailing_data.get('title') else mailing_data.get('text', '')
    
    link = mailing_data['button_link']

    if link.startswith('@'):
            link = f"https://t.me/{link[1:]}"

    markup = None
    if mailing_data.get('button_text') and mailing_data.get('button_link'):
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=mailing_data['button_text'], url=link)
        ]])

    # Берем только тех, кто не заблокировал бота (is_alive=True)
    user_ids = await db_manager.users_db.get_all_alive_user_ids() 
    
    for user_id in user_ids:
        try:
            if media_file_id and media_type:
                if media_type == 'photo':
                    await bot.send_photo(user_id, photo=media_file_id, caption=caption, reply_markup=markup)
                elif media_type == 'video':
                    await bot.send_video(user_id, video=media_file_id, caption=caption, reply_markup=markup)
                elif media_type == 'animation':
                    await bot.send_animation(user_id, animation=media_file_id, caption=caption, reply_markup=markup)
                else:
                    await bot.send_document(user_id, document=media_file_id, caption=caption, reply_markup=markup)
            else:
                await bot.send_message(user_id, text=caption, reply_markup=markup)

            await db_manager.mailing_db.log_stat(run_id, user_id, "sent")
            # Пауза 0.05 сек = ~20 сообщений в сек (безопасно для TG)
            await asyncio.sleep(0.05) 

        except TelegramForbiddenError:
            # Помечаем юзера "мертвым", чтобы не слать ему в следующий раз
            await db_manager.users_db.update_user_status(user_id, is_alive=False)
            await db_manager.mailing_db.log_stat(run_id, user_id, "blocked")
        
        except TelegramRetryAfter as e:
            # Если словили лимит — ждем и пробуем еще раз ОДИН раз
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(user_id, text=caption, reply_markup=markup)
                await db_manager.mailing_db.log_stat(run_id, user_id, "sent")
            except:
                await db_manager.mailing_db.log_stat(run_id, user_id, "failed")
        
        except (TelegramBadRequest, TelegramAPIError) as e:
            logger.error(f"Ошибка API для {user_id}: {e}")
            await db_manager.mailing_db.log_stat(run_id, user_id, "error")
            
    return run_id


async def create_broadcast(data: dict, db_manager):
    """Создает шаблон рассылки в БД"""
    await db_manager.mailing_db.add_broadcast(
        name=data["name"],
        title=data["title"],
        text=data["text"],
        media_url=data.get("media_file_id"),
        media_type=data.get("media_type"),
        button_text=data.get("button_text"),
        button_link=data.get("button_link")
    )

async def fetch_bot_stats(db_manager) -> str:
    """Генерирует текст статистики для админ-панели"""
    if not db_manager.users_db.pool:
        return "❌ Ошибка: Подключение к БД отсутствует"
        
    async with db_manager.users_db.pool.acquire() as conn:
        users_count = await conn.fetchval("SELECT count(*) FROM tg_users") or 0
        today_users = await conn.fetchval("SELECT count(*) FROM tg_users WHERE created_at::date = current_date") or 0
        refs_count = await conn.fetchval("SELECT count(*) FROM tg_users WHERE referrer_id IS NOT NULL") or 0
        total_watched = await conn.fetchval("SELECT COALESCE(SUM(watched), 0) FROM videos") or 0
        today_watched = await conn.fetchval(
            "SELECT videos_watched FROM daily_statistics WHERE stat_date = current_date"
        ) or 0
        
    stats_text = (
        f"📊 <b>ОБЩАЯ СТАТИСТИКА БОТА</b>\n"
        f"—————————————————————\n"
        f"👤 <b>ПОЛЬЗОВАТЕЛИ</b>\n"
        f"— Всего: <b>{users_count}</b>\n"
        f"— Новых сегодня: <b>{today_users}</b>\n"
        f"— Рефералов: <b>{refs_count}</b>\n\n"
        f"🎥 <b>ВИДЕО / РЕКЛАМА</b>\n"
        f"— Просмотров всего: <b>{total_watched}</b>\n"
        f"— Просмотров сегодня: <b>{today_watched}</b>"
    )
    return stats_text

async def save_user_to_db(user, db_manager, timezone: str | None = None):
    """Универсальное сохранение пользователя при /start"""
    try:
        await db_manager.users_db.add_user(
            telegram_id=user.id,
            username=getattr(user, "username", None),
            first_name=getattr(user, "first_name", None),
            last_name=getattr(user, "last_name", None),
            language_code=getattr(user, "language_code", None),
            timezone=timezone,
            is_premium=bool(getattr(user, "is_premium", False))
        )
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователя {user.id}: {e}")