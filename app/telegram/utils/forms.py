from aiogram.fsm.state import State, StatesGroup


class FormSubscribe(StatesGroup):
    streamer_name = State()


class FormChangeTemplate(StatesGroup):
    template_text = State()
