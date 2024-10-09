from typing import Any

from aiogram import types
from litestar import Request, Response, Router, post
from litestar.background_tasks import BackgroundTask
from litestar.status_codes import HTTP_200_OK, HTTP_204_NO_CONTENT

from app.api.tasks import revoke_subscriptions, send_notifications_to_chats
from app.api.verification import verify_telegram_secret, verify_twitch_secret
from app.common.config import cfg
from app.common.utils import get_logger, levelDEBUG, levelINFO
from app.telegram.bot import bot, dp

logger = get_logger(levelDEBUG if cfg.ENV == "dev" else levelINFO)


@post("/webhooks/telegram")
async def webhook_telegram(data: dict[str, Any], headers: dict[str, str]) -> Any:
    verify_telegram_secret(headers)

    logger.debug(data)
    telegram_update = types.Update(**data)
    return await dp.feed_update(bot=bot, update=telegram_update)


@post("/webhooks/twitch/stream-online")
async def webhook_twitch(
    data: dict[str, Any], headers: dict[str, str], request: Request
) -> None | str:
    await verify_twitch_secret(request)

    if data.get("subscription", {}).get("type", "") != "stream.online":
        logger.error("Notification is not 'stream.online'")
        return Response(status_code=HTTP_204_NO_CONTENT, content=None)

    event_type = headers.get("Twitch-Eventsub-Message-Type")
    streamer_id = (
        data.get("subscription", {})
        .get("condition", {})
        .get("broadcaster_user_id", "0")
    )
    message_id = headers.get("Twitch-Eventsub-Message-Id", "")
    logger.info(f"{message_id=} {streamer_id=} {event_type=}")

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
            logger.warning("Bot is not active")

    return Response(status_code=HTTP_204_NO_CONTENT, content=None)


router = Router(
    path="",
    route_handlers=[webhook_telegram, webhook_twitch],
)
