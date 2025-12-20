from aiogram.fsm.state import State, StatesGroup

class BroadcastStates(StatesGroup):
    waiting_name = State()
    waiting_media = State()
    waiting_title = State()
    waiting_text = State()
    waiting_button = State()
    waiting_button_link = State()