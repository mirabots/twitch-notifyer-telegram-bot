from contextlib import suppress

from aiogram import Bot, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command

from app.common.config import cfg
from app.common.utils import get_logger, levelDEBUG, levelINFO
from app.crud import admin as crud_admin
from app.telegram.commands import COMMANDS_ADMIN
from app.twitch import functions as twitch

router = Router()
logger = get_logger(levelDEBUG if cfg.ENV == "dev" else levelINFO)


@router.message(Command("admin"))
async def admin_commands_handler(message: types.Message):
    message_text = "Available admin commands:"
    for command, description in COMMANDS_ADMIN.items():
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


@router.message(Command("secrets_reload"))
async def secrets_reload_handler(message: types.Message):
    logger.info("Reloading secrets")
    error = await cfg.load_secrets_async()
    if error:
        logger.error(error)
        with suppress(TelegramBadRequest):
            await message.answer(text=error)
            return

    no_secrets = cfg.apply_secrets(get_db=False)
    if no_secrets:
        logger.error(f"No secrets found: {no_secrets}")
        with suppress(TelegramBadRequest):
            await message.answer(text=f"No secrets found:\n{str(no_secrets)}")
            return
    logger.info("Secrets were reloaded")
    with suppress(TelegramBadRequest):
        await message.answer(text="Reloaded")


@router.message(Command("costs"))
async def costs_handler(message: types.Message):
    costs_info = await twitch.get_costs()
    message_text = "Error getting costs info("
    if costs_info:
        message_text = ""
        for cost, value in costs_info.items():
            message_text += f"\n● {cost}\n○ {value}"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)
