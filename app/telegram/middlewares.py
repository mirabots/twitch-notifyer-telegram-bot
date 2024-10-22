from contextlib import suppress
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, types
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.common.config import cfg
from app.crud.chats import user_exists
from app.telegram.commands import COMMANDS_ADMIN


class AuthChatMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        command = event.text.rstrip()
        user_id = event.from_user.id
        user_name = event.from_user.username

        if command == "/start":
            if user_name.lower() not in cfg.TELEGRAM_ALLOWED:
                with suppress(TelegramBadRequest, TelegramForbiddenError):
                    await event.answer("You are not allowed to use this bot")
                return
            else:
                return await handler(event, data)

        if not (await user_exists(user_id)):
            return

        return await handler(event, data)


class ActiveBotMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        command = event.text.rstrip()
        user_id = event.from_user.id
        user_name = event.from_user.username

        if cfg.BOT_ACTIVE:
            return await handler(event, data)
        else:
            if (
                user_id == cfg.BOT_OWNER_ID
                and user_name == cfg.BOT_OWNER_LOGIN
                and command == "/pause"
            ):
                return await handler(event, data)


class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any],
    ) -> Any:
        command = event.text.rstrip()
        admin_commands = ["/admin", *COMMANDS_ADMIN.keys()]

        user_id = event.from_user.id
        user_name = event.from_user.username

        if command in admin_commands:
            if (
                user_id == cfg.BOT_OWNER_ID
                and user_name.lower() == cfg.BOT_OWNER_LOGIN.lower()
            ):
                return await handler(event, data)
            else:
                return

        return await handler(event, data)
