from argparse import ArgumentParser

parser = ArgumentParser(description="Twitch Notifyer Telegram Bot")
parser.add_argument(
    "--host",
    "-H",
    action="store",
    dest="host",
    default="127.0.0.1",
    help="Host addr",
)
parser.add_argument(
    "--port",
    "-P",
    action="store",
    dest="port",
    default="8800",
    help="Port",
)
parser.add_argument(
    "--env",
    "-E",
    action="store",
    dest="env",
    default="dev",
    help="Running environment",
)
args = parser.parse_args()
CURRENT_ENV = args.env

from common.config import cfg

cfg.load_creds(CURRENT_ENV)
print("INFO:\t  Config was loaded")
cfg.load_secrets()
print("INFO:\t  Secrets were loaded to config")


from contextlib import asynccontextmanager

import uvicorn
from aiogram import Bot, Dispatcher, types
from common.tasks import send_notifications_to_chats
from common.utils import exception_handlers, verify_telegram_secret, verify_twitch_event
from db.utils import _engine, check_db
from fastapi import BackgroundTasks, Depends, FastAPI, Request, Response
from telegram.admin import router as admin_router
from telegram.middlewares import (
    ActiveBotMiddleware,
    AdminMiddleware,
    AuthChatMiddleware,
)
from telegram.routes import router as main_router
from telegram.utils import COMMANDS

bot = Bot(token=cfg.TELEGRAM_TOKEN)
dp = Dispatcher()


@asynccontextmanager
async def lifespan_function(app: FastAPI):
    print(f"INFO:\t  {args.env} running {args.host}:{args.port}")
    print()

    await check_db()

    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != f"https://{cfg.DOMAIN}/webhooks/telegram":
        await bot.set_webhook(
            url=f"https://{cfg.DOMAIN}/webhooks/telegram",
            secret_token=cfg.TELEGRAM_SECRET,
        )

    dp.include_router(main_router)
    dp.include_router(admin_router)
    dp.message.middleware(ActiveBotMiddleware())
    dp.message.middleware(AuthChatMiddleware())
    dp.message.middleware(AdminMiddleware())
    await bot.set_my_commands(COMMANDS)
    await bot.set_my_description("Twitch stream.online notification bot")

    if CURRENT_ENV != "dev":
        owner_info = await bot.get_chat(cfg.OWNER_ID)
        if owner_info.username == cfg.OWNER_LOGIN:
            await bot.send_message(
                chat_id=cfg.OWNER_ID, text="ADMIN MESSAGE\nBOT STARTED"
            )

    yield

    await _engine.dispose()
    await bot.session.close()


FastAPP = FastAPI(
    title="",
    version="",
    exception_handlers=exception_handlers,
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)


@FastAPP.post("/webhooks/telegram", dependencies=[Depends(verify_telegram_secret)])
async def webhook_telegram(update: dict):
    telegram_update = types.Update(**update)
    await dp.feed_update(bot=bot, update=telegram_update)


@FastAPP.post(
    "/webhooks/twitch/stream-online", dependencies=[Depends(verify_twitch_event)]
)
async def webhook_twitch(
    event: dict, request: Request, background_tasks: BackgroundTasks
):
    if event.get("subscription", {}).get("type", "") != "stream.online":
        print("Notification is not 'stream.online'")
        return Response(status_code=204)

    event_type = request.headers.get("Twitch-Eventsub-Message-Type")
    streamer_id = (
        event.get("subscription", {})
        .get("condition", {})
        .get("broadcaster_user_id", "0")
    )
    message_id = request.headers.get("Twitch-Eventsub-Message-Id", "")
    print(f"{message_id=} {streamer_id=} {event_type=}")

    if event_type == "webhook_callback_verification":
        return Response(content=event["challenge"], media_type="text/plain")

    if event_type == "revocation":
        pass

    if event_type == "notification":
        if cfg.BOT_ACTIVE:
            background_tasks.add_task(
                send_notifications_to_chats, bot, event.get("event", {}), message_id
            )
        else:
            print("Bot is not active")
    return Response(status_code=204)


if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"][
        "fmt"
    ] = "%(asctime)s - %(client_addr)s - '%(request_line)s' %(status_code)s"

    uvicorn.run(
        "main:FastAPP",
        host=args.host,
        port=int(args.port),
        proxy_headers=True,
        log_config=log_config,
        reload=False,
    )
