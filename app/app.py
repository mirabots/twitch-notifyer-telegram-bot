import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from litestar import Litestar, Request, Response
from litestar.status_codes import HTTP_500_INTERNAL_SERVER_ERROR

from app.api.webhooks import router as litestar_router
from app.common.config import cfg
from app.common.utils import get_logger, get_logging_config, levelDEBUG, levelINFO
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

logger = get_logger(levelDEBUG if cfg.ENV == "dev" else levelINFO)
logging_config = get_logging_config(levelDEBUG if cfg.ENV == "dev" else levelINFO)


@asynccontextmanager
async def lifespan_function(app: Litestar) -> AsyncGenerator[None, None]:
    await check_db(logger)

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
    await bot.set_my_commands(COMMANDS)
    await bot.set_my_description("Twitch stream.online notification bot")

    if cfg.ENV != "dev":
        await bot.send_message(
            chat_id=cfg.BOT_OWNER_ID, text="ADMIN MESSAGE\nBOT STARTED"
        )

    try:
        yield
    finally:
        await bot.session.close()
        await _engine.dispose()


def internal_server_error_handler(_: Request, exc: Exception) -> Response:
    logger.error(exc)
    traceback.print_exception(exc)
    return Response(
        status_code=500,
        content={"detail": "Server error"},
    )


app = Litestar(
    [litestar_router],
    lifespan=[lifespan_function],
    logging_config=logging_config,
    # debug=True,
    exception_handlers={
        HTTP_500_INTERNAL_SERVER_ERROR: internal_server_error_handler,
    },
)
