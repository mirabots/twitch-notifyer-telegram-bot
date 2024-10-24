from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.telegram.utils.callbacks import (
    CallbackAbort,
    CallbackChooseChat,
    CallbackChooseStreamer,
    CallbackChooseUser,
    CallbackDefault,
    CallbackLimitDefault,
    CallbackPicture,
    CallbackUsersAction,
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


def get_keyboard_abort(action: str, name: str = "Abort") -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=name, callback_data=CallbackAbort(action=action))
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


def get_keyboard_picture(action: str, choices: list[str]) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for choice in choices:
        keyboard.button(text=choice, callback_data=CallbackPicture(action=action))
    return keyboard


def get_keyboard_users_actions() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for action in ("Add", "Remove"):
        keyboard.button(text=action, callback_data=CallbackUsersAction(action=action))
    return keyboard


def get_keyboard_users(
    users: dict[str, int | None], action: str
) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    user_num = 0
    for user_name, user_id in users.items():
        keyboard.button(
            text=user_name,
            callback_data=CallbackChooseUser(
                action=action,
                user_num=user_num,
                user_id=user_id,
            ),
        )
        user_num += 1
    return keyboard


def get_keyboard_limit_default(name: str) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=name, callback_data=CallbackLimitDefault())
    return keyboard
