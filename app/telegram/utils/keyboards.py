from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from telegram.utils.callbacks import (
    CallbackAbort,
    CallbackChannelsRemove,
    CallbackChooseChannel,
    CallbackChooseChat,
    CallbackChooseStreamer,
    CallbackChooseUser,
    CallbackDump,
    CallbackLimitDefault,
    CallbackLimitDefaultUsersUpdate,
    CallbackPicture,
    CallbackRestreamsLinks,
    CallbackTemplateMode,
    CallbackUserLimit,
    CallbackUsersAction,
)


def get_keyboard_chats(chats: list[types.Chat], action: str) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for chat in chats:
        keyboard.button(
            text=f"{chat.title or 'BOT CHAT'} ({chat.type})",
            callback_data=CallbackChooseChat(id=chat.id, action=action),
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


def get_keyboard_template_mode(streamer_id: str, chat_id: int) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for id, choice in enumerate(("Default", "Empty")):
        keyboard.button(
            text=choice,
            callback_data=CallbackTemplateMode(
                choice_id=id, streamer_id=streamer_id, chat_id=chat_id
            ),
        )
    return keyboard


def get_keyboard_picture(streamer_id: str, chat_id: int) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for id, choice in enumerate(("Stream start screenshot", "Own pic", "Disabled")):
        keyboard.button(
            text=choice,
            callback_data=CallbackPicture(
                choice_id=id, streamer_id=streamer_id, chat_id=chat_id
            ),
        )
    return keyboard


def get_keyboard_restreams_links(
    streamer_id: str, chat_id: int
) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for id, choice in enumerate(("Add / Update", "Remove all")):
        keyboard.button(
            text=choice,
            callback_data=CallbackRestreamsLinks(
                choice_id=id, streamer_id=streamer_id, chat_id=chat_id
            ),
        )
    return keyboard


def get_keyboard_users_actions() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for action in ("Invite", "Rename", "Remove"):
        keyboard.button(text=action, callback_data=CallbackUsersAction(action=action))
    return keyboard


def get_keyboard_users(
    users: dict[int, dict[str, int | str | None]], action: str
) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for user_id, user_data in users.items():
        keyboard.button(
            text=user_data["name"],
            callback_data=CallbackChooseUser(
                action=action,
                user_id=user_id,
            ),
        )
    return keyboard


def get_keyboard_limit_default(name: str) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text=name, callback_data=CallbackLimitDefault())
    return keyboard


def get_keyboard_limit_default_users_update(value: int) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for action in ("Yes", "No"):
        keyboard.button(
            text=action,
            callback_data=CallbackLimitDefaultUsersUpdate(action=action, value=value),
        )
    return keyboard


def get_keyboard_user_limit(user_id: int) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for action in ("Unlim", "Default"):
        keyboard.button(
            text=action, callback_data=CallbackUserLimit(action=action, user_id=user_id)
        )
    return keyboard


def get_keyboard_dump() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for action in ("Create", "Restore"):
        keyboard.button(text=action, callback_data=CallbackDump(action=action))
    return keyboard


def get_keyboard_channels_remove() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Choose to remove", callback_data=CallbackChannelsRemove())
    return keyboard


def get_keyboard_channels(
    channels: list[types.Chat], action: str
) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for channel in channels:
        keyboard.button(
            text=channel.title,
            callback_data=CallbackChooseChannel(id=channel.id, action=action),
        )
    return keyboard
