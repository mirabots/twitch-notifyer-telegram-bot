from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, types
from common.config import cfg
from telegram.commands import COMMANDS_ADMIN, get_command


class ActiveBotMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [types.Message | types.CallbackQuery, Dict[str, Any]], Awaitable[Any]
        ],
        event: types.Message | types.CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        text = getattr(event, "text", "") or getattr(event, "caption", "") or ""
        command = get_command(text)
        user_id = event.from_user.id

        if cfg.BOT_ACTIVE:
            return await handler(event, data)
        else:
            if user_id == cfg.TELEGRAM_BOT_OWNER_ID and command == "pause":
                return await handler(event, data)


class AuthChatMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [types.Message | types.CallbackQuery, Dict[str, Any]], Awaitable[Any]
        ],
        event: types.Message | types.CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        text = getattr(event, "text", "") or getattr(event, "caption", "") or ""
        command = get_command(text)
        user_id = event.from_user.id

        if command == "start":
            return await handler(event, data)

        if user_id not in cfg.TELEGRAM_USERS:
            return

        return await handler(event, data)


class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [types.Message | types.CallbackQuery, Dict[str, Any]], Awaitable[Any]
        ],
        event: types.Message | types.CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        text = getattr(event, "text", "") or getattr(event, "caption", "") or ""
        command = get_command(text)
        admin_commands = ["admin", *COMMANDS_ADMIN.keys()]
        user_id = event.from_user.id

        if command in admin_commands and user_id != cfg.TELEGRAM_BOT_OWNER_ID:
            return

        return await handler(event, data)
