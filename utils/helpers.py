import asyncio
import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramBadRequest

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
    Полный цикл рассылки: получение данных, отправка с лимитами, логирование.
    """
    name = data.get("name")
    if not name:
        logger.error("send_broadcast: В данных отсутствует 'name'")
        return None

    mailing_data = await db_manager.mailing_db.get_mailing_by_name(name)
    if not mailing_data:
        logger.error(f"Рассылка с именем '{name}' не найдена в базе данных.")
        return None
    
    mailing_id = mailing_data['id']
    try:
        run_id = await db_manager.mailing_db.start_new_run(mailing_id)
    except Exception as e:
        logger.error(f"Не удалось создать run_id: {e}")
        return None

    media_file_id = mailing_data.get('media_url')
    media_type = mailing_data.get('media_type')
    title = mailing_data.get('title', '')
    text = mailing_data.get('text', '')
    button_text = mailing_data.get('button_text')
    link = mailing_data.get('button_link')

    caption = f"<b>{title}</b>\n\n{text}" if title else text
    
    markup = None
    if button_text and link:
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=button_text, url=link)
        ]])

    # Метод должен возвращать список ID (например, [123, 456])
    user_ids = await db_manager.users_db.get_all_user_ids() 
    
    count = 0
    for user_id in user_ids:
        try:
            if media_file_id and media_type:
                if media_type == 'photo':
                    await bot.send_photo(user_id, photo=media_file_id, caption=caption, reply_markup=markup, parse_mode="HTML")
                elif media_type == 'video':
                    await bot.send_video(user_id, video=media_file_id, caption=caption, reply_markup=markup, parse_mode="HTML")
                elif media_type == 'animation':
                    await bot.send_animation(user_id, animation=media_file_id, caption=caption, reply_markup=markup, parse_mode="HTML")
                else:
                    await bot.send_document(user_id, document=media_file_id, caption=caption, reply_markup=markup, parse_mode="HTML")
            else:
                await bot.send_message(user_id, text=caption, reply_markup=markup, parse_mode="HTML")

            await db_manager.mailing_db.log_stat(run_id, user_id, "sent")
            count += 1
            
            # Anti-flood: не более 30 сообщений в секунду
            if count % 25 == 0:
                await asyncio.sleep(1)

        except TelegramForbiddenError:
            await db_manager.mailing_db.log_stat(run_id, user_id, "blocked")
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(user_id, text=caption, reply_markup=markup, parse_mode="HTML")
            except: pass 
        except TelegramBadRequest as e:
            logger.error(f"Bad Request для {user_id}: {e}")
            await db_manager.mailing_db.log_stat(run_id, user_id, "error_content")
        except Exception as e:
            logger.error(f"Не удалось отправить {user_id}: {e}")
            await db_manager.mailing_db.log_stat(run_id, user_id, "failed")

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