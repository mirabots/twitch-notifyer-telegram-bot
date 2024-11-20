import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from aiogram.exceptions import TelegramBadRequest
from api.webhooks import router as litestar_router
from common.config import cfg
from crud.streamers import get_all_streamers, update_streamer_name
from crud.users import add_user, get_users, update_user
from db.common import _engine, check_db
from litestar import Litestar, Request, Response
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR
from telegram.bot import bot, dp
from telegram.commands import COMMANDS
from telegram.middlewares import (
    ActiveBotMiddleware,
    AdminMiddleware,
    AuthChatMiddleware,
)
from telegram.routes.admin import router as telegram_router_admin
from telegram.routes.base import router as telegram_router_base
from telegram.routes.subscriptions import router as telegram_router_subscriptions
from twitch.functions import get_streamers_names
from versions import APP_VERSION_STRING


@asynccontextmanager
async def lifespan_function(app: Litestar) -> AsyncGenerator[None, None]:
    await check_db()

    # webhook_info = await bot.get_webhook_info()
    # if webhook_info.url != f"https://{cfg.DOMAIN}/webhooks/telegram":
    await bot.set_webhook(
        url=f"https://{cfg.DOMAIN}/webhooks/telegram",
        secret_token=cfg.TELEGRAM_SECRET,
        drop_pending_updates=True if cfg.ENV == "dev" else False,
    )

    dp.include_router(telegram_router_base)
    dp.include_router(telegram_router_subscriptions)
    dp.include_router(telegram_router_admin)
    dp.message.middleware(ActiveBotMiddleware())
    dp.message.middleware(AuthChatMiddleware())
    dp.message.middleware(AdminMiddleware())
    dp.callback_query.middleware(ActiveBotMiddleware())
    dp.callback_query.middleware(AuthChatMiddleware())
    dp.callback_query.middleware(AdminMiddleware())
    await bot.set_my_commands(COMMANDS)
    await bot.set_my_description("Twitch stream.online notification bot")

    cfg.TELEGRAM_USERS = await get_users()
    # add owner at first startup
    if cfg.TELEGRAM_BOT_OWNER_ID not in cfg.TELEGRAM_USERS:
        cfg.logger.info("Adding owner admin user")
        cfg.TELEGRAM_USERS[cfg.TELEGRAM_BOT_OWNER_ID] = {"limit": None, "name": "admin"}
        await add_user(cfg.TELEGRAM_BOT_OWNER_ID, None, "admin")

    # update users names and limites (after db changes)
    if any(
        [
            str(user_id) == user_data["name"]
            for user_id, user_data in cfg.TELEGRAM_USERS.items()
        ]
    ):
        cfg.logger.info("Updating users names")
        for user_id, user_data in cfg.TELEGRAM_USERS.items():
            updated_user_data = {}
            if user_id != cfg.TELEGRAM_BOT_OWNER_ID and user_data["limit"] == None:
                updated_user_data["limit"] = cfg.TELEGRAM_LIMIT_DEFAULT
                cfg.TELEGRAM_USERS[user_id]["limit"] = cfg.TELEGRAM_LIMIT_DEFAULT
            if str(user_id) == user_data["name"]:
                user_info = await bot.get_chat(user_id)
                user_name = user_info.full_name + f" ({user_info.username})"
                updated_user_data["name"] = user_name
                cfg.TELEGRAM_USERS[user_id]["name"] = user_name
            if updated_user_data:
                await update_user(user_id, updated_user_data)

    # update streamers names
    streamers = await get_all_streamers()
    if streamers:
        cfg.logger.info("Updating streamers names")
    streamers_with_names = await get_streamers_names(list(streamers.keys()))
    for streamer_id, streamer_name in streamers.items():
        twitch_name = streamers_with_names.get(streamer_id, "")
        if streamer_name in ("-", None) or (
            twitch_name != "" and streamer_name != twitch_name
        ):
            if not twitch_name:
                streamer_with_name = await get_streamers_names([streamer_id])
                twitch_name = streamer_with_name[streamer_id]
            await update_streamer_name(streamer_id, twitch_name)

    if cfg.ENV != "dev":
        with suppress(TelegramBadRequest):
            await bot.send_message(
                chat_id=cfg.TELEGRAM_BOT_OWNER_ID,
                text=f"ADMIN MESSAGE\nBOT STARTED\n{APP_VERSION_STRING}",
            )

    try:
        yield
    finally:
        if cfg.ENV != "dev":
            with suppress(TelegramBadRequest):
                await bot.send_message(
                    chat_id=cfg.TELEGRAM_BOT_OWNER_ID,
                    text="ADMIN MESSAGE\nBOT WAS STOPPED",
                )

        await bot.session.close()
        await _engine.dispose()


def internal_server_error_handler(_: Request, exc: Exception) -> Response:
    cfg.logger.error(exc)
    traceback.print_exception(exc)
    return Response(
        status_code=500,
        content={"detail": "Server error"},
    )


app = Litestar(
    [litestar_router],
    lifespan=[lifespan_function],
    logging_config=cfg.logging_config,
    exception_handlers={
        HTTP_500_INTERNAL_SERVER_ERROR: internal_server_error_handler,
    },
)
