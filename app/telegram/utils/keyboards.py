from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.telegram.utils.callbacks import (
    CallbackAbort,
    CallbackChooseChat,
    CallbackChooseStreamer,
    CallbackDefault,
)


def get_keyboard_chats(chats: list[types.Chat], action: str) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for chat in chats:
        keyboard.button(
            text=f"{chat.title or 'ME'} ({chat.type})",
            callback_data=CallbackChooseChat(id=str(chat.id), action=action),
        )
    return keyboard


def get_keyboard_streamers(
    action: str, streamers: dict[str, str], chat_id: int
) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    streamers_list = list(streamers.items())
    for streamer_id, streamer_name in sorted(
        streamers_list, key=lambda streamer: streamer[1].lower()
    ):
        keyboard.button(
            text=streamer_name,
            callback_data=CallbackChooseStreamer(
                action=action,
                streamer_id=streamer_id,
                chat_id=chat_id,
            ),
        )
    return keyboard


def get_keyboard_abort(action: str) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Abort", callback_data=CallbackAbort(action=action))
    return keyboard


def get_keyboard_default(
    action: str, streamer_id: str, chat_id: int
) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text="Default",
        callback_data=CallbackDefault(
            action=action, streamer_id=streamer_id, chat_id=chat_id
        ),
    )
    return keyboard
