from contextlib import suppress

from aiogram import Bot, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from common.config import cfg
from crud import admin as crud_admin
from twitch import functions as twitch

router = Router()


@router.message(Command("admin"))
async def admin_commands_handler(message: types.Message):
    admin_commands = {
        "/users": "List all users with their channels",
        "/streamers": "List subscribed streamers",
        "/pause": "(Un)Pause bot",
        "/secrets": "Reload secrets",
    }
    message_text = "Available admin commands:"
    for command, description in admin_commands.items():
        message_text += f"\n● {description}\n○ {command}"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("users"))
async def users_handler(message: types.Message, bot: Bot):
    chats = await crud_admin.get_all_chats()
    message_text = f"Users ({len(chats)}):"
    for user_id, user_chats in chats.items():
        chat_info = await bot.get_chat(user_id)
        message_text += f"\n● {chat_info.username}"
        if user_chats:
            message_text += f" ({len(user_chats)}):\n○ ["
            for chat_id in user_chats:
                chat_info = await bot.get_chat(chat_id)
                message_text += f"{chat_info.title}, "
            message_text = message_text.rstrip(", ")
            message_text += "]"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("streamers"))
async def streamers_handler(message: types.Message):
    streamers = await crud_admin.get_all_streamers()
    if not streamers:
        message_text = "No streamers"
    else:
        streamers_with_names = await twitch.get_streamers_names(streamers)
        message_text = f"Streamers ({len(streamers_with_names)}):"
        for streamer_name in sorted(
            list(streamers_with_names.values()), key=lambda name: name.lower()
        ):
            message_text += f"\n● {streamer_name}"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("pause"))
async def bot_active_handler(message: types.Message):
    if cfg.BOT_ACTIVE:
        cfg.BOT_ACTIVE = False
        message_text = "Bot was paused"
    else:
        cfg.BOT_ACTIVE = True
        message_text = "Bot was resumed"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("secrets"))
async def secrets_reload_handler(message: types.Message):
    unavailable_secrets = await cfg.reload_secrets()
    message_text = "Secrets were reloaded"
    if unavailable_secrets:
        message_text += "\nUnavailable secrets:\n" + "\n".join(unavailable_secrets)

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)
