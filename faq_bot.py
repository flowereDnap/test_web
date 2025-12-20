import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton, 
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import asyncpg
from dotenv import load_dotenv
from deep_translator import GoogleTranslator

load_dotenv()

DATABASE_DSN = os.getenv("DATABASE_DSN")

# Загружаем admin ID
admin_ids_str = os.getenv("ADMIN_IDS", "0")
ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]

# Функция проверки 
def is_admin(user_id: int) -> bool:
    # Явное приведение к int перед проверкой
    return int(user_id) in ADMIN_IDS

FAQ_BOT_TOKEN = os.getenv("FAQ_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

# --- Переводчик ---
def auto_translate(text: str, target_lang: str):
    try:
        if not text or len(text.strip()) == 0: return ""
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as e:
        logging.error(f"Translation error: {e}")
        return text

# --- Тексты ---
MESSAGES = {
    'ru': {
        'start': "Нажмите кнопку открыть заявку, напишите ваш вопрос в одном сообщении со всеми деталями. Когда закончите писать отправьте сообщение и нажмите отправить заявку",
        'btn_open': "Открыть заявку",
        'btn_submit': "Подать заявку",
        'thanks': "спасибо за обращение, простараемся ответить как можно быстрее",
        'btn_another': "открыть другую заявку",
    },
    'en': {
        'start': "Press the 'Open Ticket' button, write your question in messages with all details. When finished, press 'Submit Ticket'.",
        'btn_open': "Open Ticket",
        'btn_submit': "Submit Ticket",
        'thanks': "thank you for your request, we will try to answer as soon as possible",
        'btn_another': "open another ticket",
    }
}

def get_text(key: str, lang: str):
    return MESSAGES.get(lang if lang in MESSAGES else 'en', MESSAGES['en']).get(key)

class UserStates(StatesGroup):
    writing_ticket = State()

class AdminStates(StatesGroup):
    replying = State()

# --- База данных ---
class DB:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(DATABASE_DSN)
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    lang_code VARCHAR(10),
                    text TEXT,
                    translated_text TEXT,
                    status VARCHAR(20) DEFAULT 'открыта',
                    admin_id BIGINT,
                    reply_text TEXT
                )
            ''')

    async def create_ticket(self, user_id: int, lang: str, text: str, translated: str):
        return await self.pool.fetchval(
            "INSERT INTO tickets (user_id, lang_code, text, translated_text) VALUES ($1, $2, $3, $4) RETURNING id", 
            user_id, lang, text, translated
        )

    async def get_open_tickets(self):
        return await self.pool.fetch("SELECT * FROM tickets WHERE status = 'открыта' ORDER BY id")

    async def update_status(self, ticket_id: int, status: str, admin_id: int, reply: str = None):
        await self.pool.execute(
            "UPDATE tickets SET status = $1, admin_id = $2, reply_text = $3 WHERE id = $4",
            status, admin_id, reply, ticket_id
        )

db = DB()
# Инициализация с MemoryStorage, чтобы состояния не терялись
bot = Bot(token=FAQ_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- Клавиатуры ---
def kb_open(lang: str):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=get_text('btn_open', lang))]], resize_keyboard=True)

def kb_submit(lang: str):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=get_text('btn_submit', lang))]], resize_keyboard=True)

def kb_another(lang: str):
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=get_text('btn_another', lang))]], resize_keyboard=True)

# --- Логика админа ---
async def show_admin_panel(message: types.Message, state: FSMContext, index: int, edit: bool = False):
    tickets = await db.get_open_tickets()
    if not tickets:
        msg = "Нет открытых заявок."
        if edit: await message.edit_text(msg)
        else: await message.answer(msg)
        return

    if index < 0: index = 0
    if index >= len(tickets): index = len(tickets) - 1
    
    t = tickets[index]
    await state.update_data(current_index=index, cur_t_id=t['id'], cur_u_id=t['user_id'], cur_u_lang=t['lang_code'])

    msg_text = (f"<b>Заявка #{t['id']}</b>\nID: <code>{t['user_id']}</code>\n"
                f"Язык: {t['lang_code']}\n\n"
                f"<b>Текст:</b>\n{t['text']}\n\n"
                f"<b>Перевод:</b>\n{t['translated_text']}")

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"adm_nav_{index-1}"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data=f"adm_close_{t['id']}"),
        InlineKeyboardButton(text="Вперед ➡️", callback_data=f"adm_nav_{index+1}")
    )
    kb.row(InlineKeyboardButton(text="💬 Ответить", callback_data=f"adm_prep_reply_{t['id']}"))
    
    if edit:
        try: await message.edit_text(msg_text, reply_markup=kb.as_markup(), parse_mode="HTML")
        except: pass
    else:
        await message.answer(msg_text, reply_markup=kb.as_markup(), parse_mode="HTML")

# --- Хэндлеры Пользователя ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    if is_admin(message.from_user.id):
        await show_admin_panel(message, state, 0)
    else:
        lang = message.from_user.language_code
        await message.answer(get_text('start', lang), reply_markup=kb_open(lang))

@dp.message(F.text.in_({"Открыть заявку", "Open Ticket", "открыть другую заявку", "open another ticket"}))
async def user_open_ticket(message: types.Message, state: FSMContext):
    lang = message.from_user.language_code
    await state.set_state(UserStates.writing_ticket)
    await state.update_data(messages=[]) 
    # При нажатии "Открыть" просто меняем кнопки на "Подать"
    await message.answer("📝 Записываю... Напишите ваш вопрос и нажмите кнопку ниже.", reply_markup=kb_submit(lang))

# Хэндлер для кнопки "Подать заявку" (ставим ВЫШЕ обычного сбора текста)
@dp.message(UserStates.writing_ticket, F.text.in_({"Подать заявку", "Submit Ticket"}))
async def user_submit(message: types.Message, state: FSMContext):
    lang = message.from_user.language_code
    data = await state.get_data()
    msgs = data.get('messages', [])
    full_text = "\n".join(msgs)

    if not full_text.strip():
        await message.answer("Вы еще не написали вопрос.")
        return

    translated = auto_translate(full_text, 'ru') if lang != 'ru' else full_text
    await db.create_ticket(message.from_user.id, lang, full_text, translated)
    
    await state.clear()
    await message.answer(get_text('thanks', lang), reply_markup=kb_another(lang))

# Хэндлер для сбора ВСЕГО текста, пока пользователь в состоянии записи
@dp.message(UserStates.writing_ticket)
async def user_collect_text(message: types.Message, state: FSMContext):
    if not message.text: return
    data = await state.get_data()
    msgs = data.get('messages', [])
    msgs.append(message.text)
    await state.update_data(messages=msgs)
    # Можно добавить визуальный фидбек (опционально)
    # await message.reply("✅ Принято, пишите дальше или нажмите 'Подать'")

# --- Хэндлеры Админа ---

@dp.callback_query(F.data.startswith("adm_nav_"))
async def adm_nav(call: types.CallbackQuery, state: FSMContext):
    idx = int(call.data.split("_")[2])
    await show_admin_panel(call.message, state, idx, edit=True)
    await call.answer()

@dp.callback_query(F.data.startswith("adm_close_"))
async def adm_close(call: types.CallbackQuery, state: FSMContext):
    t_id = int(call.data.split("_")[2])
    await db.update_status(t_id, "закрыта", call.from_user.id)
    await call.answer("Заявка закрыта")
    await show_admin_panel(call.message, state, 0, edit=True)

@dp.callback_query(F.data.startswith("adm_prep_reply_"))
async def adm_prep_reply(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = data.get('current_index', 0)
    t_id = data.get('cur_t_id')
    
    # Меняем текст кнопки в инлайне
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"adm_nav_{idx-1}"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data=f"adm_close_{t_id}"),
        InlineKeyboardButton(text="Вперед ➡️", callback_data=f"adm_nav_{idx+1}")
    )
    kb.row(InlineKeyboardButton(text="отправить ответ", callback_data="none"))
    await call.message.edit_reply_markup(reply_markup=kb.as_markup())
    
    await state.set_state(AdminStates.replying)
    reply_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Отправить ответ")]], resize_keyboard=True)
    await call.message.answer("Введите текст ответа:", reply_markup=reply_kb)
    await call.answer()

@dp.message(AdminStates.replying, F.text != "Отправить ответ")
async def adm_collect_reply(message: types.Message, state: FSMContext):
    await state.update_data(admin_text=message.text)

@dp.message(AdminStates.replying, F.text == "Отправить ответ")
async def adm_send_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    admin_text = data.get('admin_text')
    
    if not admin_text:
        await message.answer("Ошибка: текст ответа пуст!")
        return

    user_lang = data.get('cur_u_lang', 'en')
    final_reply = auto_translate(admin_text, user_lang) if user_lang != 'ru' else admin_text
    
    try:
        await bot.send_message(data.get('cur_u_id'), f"<b>Ответ:</b>\n\n{final_reply}", parse_mode="HTML")
        await db.update_status(data.get('cur_t_id'), "отвечена", message.from_user.id, admin_text)
        await message.answer("Готово!", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await show_admin_panel(message, state, 0)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

async def main():
    await db.connect()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())