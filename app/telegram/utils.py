from aiogram import types
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

COMMANDS = [
    types.BotCommand(command="start", description="Start bot"),
    types.BotCommand(command="info", description="Simple info"),
    types.BotCommand(command="add_channel", description="Add bot to channel"),
    types.BotCommand(command="chats", description="Show chats/channels list"),
    types.BotCommand(command="subscriptions", description="Subscriptions list"),
    types.BotCommand(
        command="subscribe", description="Subscribe to stream notification"
    ),
    types.BotCommand(command="template", description="Change notification template"),
    types.BotCommand(
        command="unsubscribe", description="Unsubscribe from stream notification"
    ),
    types.BotCommand(command="stop", description="Stop bot"),
    types.BotCommand(command="admin", description="List of admin commands"),
]


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


class FormSubscribe(StatesGroup):
    streamer_name = State()


class FormChangeTemplate(StatesGroup):
    template_text = State()


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


def get_choosed_callback_text(keyboards, callback_data) -> str:
    for keyboard in keyboards:
        for button in keyboard:
            if button.callback_data == callback_data:
                return button.text
