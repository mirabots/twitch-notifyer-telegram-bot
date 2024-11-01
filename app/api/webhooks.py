import traceback
from contextlib import suppress
from typing import Any

from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from api.tasks import revoke_subscriptions, send_notifications_to_chats
from api.verification import verify_telegram_secret, verify_twitch_secret
from common.config import cfg
from litestar import Request, Response, Router, post
from litestar.background_tasks import BackgroundTask
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT
from telegram.bot import bot, dp


@post("/webhooks/telegram")
async def webhook_telegram(data: dict[str, Any], headers: dict[str, str]) -> Any:
    verify_telegram_secret(headers)

    cfg.logger.debug(data)
    try:
        telegram_update = types.Update(**data)
        await dp.feed_update(bot=bot, update=telegram_update)
    except Exception as exc:
        if cfg.ENV != "dev":
            with suppress(TelegramBadRequest):
                await bot.send_message(
                    chat_id=cfg.TELEGRAM_BOT_OWNER_ID,
                    text=f"ADMIN MESSAGE\nTG ERROR\n{exc}",
                )
        cfg.logger.error(exc)
        traceback.print_exception(exc)
    return Response(status_code=HTTP_204_NO_CONTENT, content=None)


@post("/webhooks/twitch/stream-online")
async def webhook_twitch(
    data: dict[str, Any], headers: dict[str, str], request: Request
) -> None | str:
    await verify_twitch_secret(request)
    cfg.logger.debug(data)

    if data.get("subscription", {}).get("type", "").lower() != "stream.online":
        cfg.logger.error("Notification is not 'stream.online'")
        return Response(status_code=HTTP_204_NO_CONTENT, content=None)

    event_type = headers.get("Twitch-Eventsub-Message-Type".lower(), "").lower()
    streamer_id = (
        data.get("subscription", {})
        .get("condition", {})
        .get("broadcaster_user_id", "0")
    )
    message_id = headers.get("Twitch-Eventsub-Message-Id".lower(), "")
    cfg.logger.info(f"Event {message_id=} {streamer_id=} {event_type=}")

    if event_type == "webhook_callback_verification":
        return Response(
            status_code=HTTP_200_OK, content=data["challenge"], media_type="text/plain"
        )

    elif event_type == "revocation":
        return Response(
            status_code=HTTP_204_NO_CONTENT,
            content=None,
            background=BackgroundTask(
                revoke_subscriptions, data.get("subscription", {})
            ),
        )

    elif event_type == "notification":
        if cfg.BOT_ACTIVE:
            return Response(
                status_code=HTTP_204_NO_CONTENT,
                content=None,
                background=BackgroundTask(
                    send_notifications_to_chats, data.get("event", {}), message_id
                ),
            )
        else:
            cfg.logger.warning("Bot is not active")

    return Response(status_code=HTTP_204_NO_CONTENT, content=None)


router = Router(
    path="",
    route_handlers=[webhook_telegram, webhook_twitch],
)
