from aiogram.filters.callback_data import CallbackData


def get_choosed_callback_text(keyboards, callback_data) -> str:
    for keyboard in keyboards:
        for button in keyboard:
            if button.callback_data == callback_data:
                return button.text


class CallbackChooseChat(CallbackData, prefix="chat"):
    id: int
    action: str


class CallbackChooseStreamer(CallbackData, prefix="strmr"):
    action: str
    streamer_id: str
    chat_id: int


class CallbackAbort(CallbackData, prefix="abort"):
    action: str


class CallbackDefault(CallbackData, prefix="dflt"):
    action: str
    streamer_id: str
    chat_id: int