from aiogram.fsm.state import State, StatesGroup


class FormSubscribe(StatesGroup):
    streamer_name = State()


class FormChangeTemplate(StatesGroup):
    template_text = State()


class FormLimitDefault(StatesGroup):
    value = State()


class FormUserLimit(StatesGroup):
    value = State()


class FromUserRename(StatesGroup):
    name = State()


class FormDump(StatesGroup):
    dump = State()


class FormPicture(StatesGroup):
    new_picture = State()


class FormBroadcastMessage(StatesGroup):
    message = State()
