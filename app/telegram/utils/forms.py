from aiogram.fsm.state import State, StatesGroup


class FormSubscribe(StatesGroup):
    streamer_name = State()


class FormChangeTemplate(StatesGroup):
    template_text = State()


class FormChangePictureMode(StatesGroup):
    picture_mode = State()
    picture_input = State()


class FormUserAdd(StatesGroup):
    user_name = State()
