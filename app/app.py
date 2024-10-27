import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from litestar import Litestar, Request, Response
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR

from app.api.webhooks import router as litestar_router
from app.common.config import cfg
from app.crud.users import add_user, get_users, update_user
from app.db.common import _engine, check_db
from app.telegram.bot import bot, dp
from app.telegram.commands import COMMANDS
from app.telegram.middlewares import (
    ActiveBotMiddleware,
    AdminMiddleware,
    AuthChatMiddleware,
)
from app.telegram.routes.admin import router as telegram_router_admin
from app.telegram.routes.base import router as telegram_router_base
from app.telegram.routes.subscriptions import router as telegram_router_subscriptions


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
    for user_id, user_data in cfg.TELEGRAM_USERS.items():
        if str(user_id) == user_data["name"]:
            user_info = await bot.get_chat(user_id)
            user_name = user_info.full_name + f" ({user_info.username})"
            await update_user(user_id, {"name": user_name})
            cfg.TELEGRAM_USERS[user_id]["name"] = user_name
    if cfg.TELEGRAM_BOT_OWNER_ID not in cfg.TELEGRAM_USERS:
        cfg.TELEGRAM_USERS[cfg.TELEGRAM_BOT_OWNER_ID] = {"limit": None, "name": "admin"}
        await add_user(cfg.TELEGRAM_BOT_OWNER_ID, None, "admin")

    if cfg.ENV != "dev":
        await bot.send_message(
            chat_id=cfg.TELEGRAM_BOT_OWNER_ID, text="ADMIN MESSAGE\nBOT STARTED"
        )

    try:
        yield
    finally:
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
    # debug=True,
    exception_handlers={
        HTTP_500_INTERNAL_SERVER_ERROR: internal_server_error_handler,
    },
)
