from datetime import datetime, timezone

import httpx
from common.config import cfg
from telegram.bot import bot

ROUTE_OAUTH2_TOKEN = "https://id.twitch.tv/oauth2/token"
ROUTE_USERS = "https://api.twitch.tv/helix/users"
ROUTE_STREAMS = "https://api.twitch.tv/helix/streams"
ROUTE_CHANNELS = "https://api.twitch.tv/helix/channels"
ROUTE_EVENTS_SUBSCRIPTIONS = "https://api.twitch.tv/helix/eventsub/subscriptions"


async def _auth() -> None:
    try:
        async with httpx.AsyncClient() as ac:
            answer = await ac.post(
                ROUTE_OAUTH2_TOKEN,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_id": cfg.TWITCH_CLIENT_ID,
                    "client_secret": cfg.TWITCH_CLIENT_SECRET,
                    "grant_type": "client_credentials",
                },
            )
            if answer.status_code != 200:
                raise Exception(f"Response: {answer.status_code}")
            cfg.TWITCH_BEARER = answer.json()["access_token"]
    except Exception as e:
        cfg.logger.error(f"Twitch auth error {str(e)}")
        if cfg.ENV != "dev":
            datetime_utc_now = datetime.now(tz=timezone.utc).isoformat()
            await bot.send_message(
                chat_id=cfg.TELEGRAM_BOT_OWNER_ID,
                text=f"ADMIN MESSAGE\nTWITCH AUTH FAILED at {datetime_utc_now}\n{str(e)}",
            )


async def _get_streamers_info(params: dict[str, str | list[str]]) -> httpx.Response:
    async with httpx.AsyncClient() as ac:
        return await ac.get(
            ROUTE_USERS,
            headers={
                "Client-Id": cfg.TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {cfg.TWITCH_BEARER}",
            },
            params=params,
        )


async def _get_stream_info(streamer_id: str) -> httpx.Response:
    async with httpx.AsyncClient() as ac:
        return await ac.get(
            ROUTE_STREAMS,
            headers={
                "Client-Id": cfg.TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {cfg.TWITCH_BEARER}",
            },
            params={"user_id": streamer_id},
        )


async def _get_channel_info(streamer_id: str) -> httpx.Response:
    async with httpx.AsyncClient() as ac:
        return await ac.get(
            ROUTE_CHANNELS,
            headers={
                "Client-Id": cfg.TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {cfg.TWITCH_BEARER}",
            },
            params={"broadcaster_id": streamer_id},
        )


async def _subscribe_event(streamer_id: str, event_type: str) -> httpx.Response:
    async with httpx.AsyncClient() as ac:
        return await ac.post(
            ROUTE_EVENTS_SUBSCRIPTIONS,
            headers={
                "Client-Id": cfg.TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {cfg.TWITCH_BEARER}",
            },
            json={
                "type": event_type,
                "version": "1",
                "condition": {"broadcaster_user_id": streamer_id},
                "transport": {
                    "method": "webhook",
                    "callback": f"https://{cfg.DOMAIN}/webhooks/twitch/stream-online",
                    "secret": cfg.TWITCH_SUBSCRIPTION_SECRET,
                },
            },
        )


async def _unsubscribe_event(event_id: str) -> httpx.Response:
    async with httpx.AsyncClient() as ac:
        return await ac.delete(
            ROUTE_EVENTS_SUBSCRIPTIONS,
            headers={
                "Client-Id": cfg.TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {cfg.TWITCH_BEARER}",
            },
            params={"id": event_id},
        )


async def _get_costs() -> httpx.Response:
    async with httpx.AsyncClient() as ac:
        return await ac.get(
            ROUTE_EVENTS_SUBSCRIPTIONS,
            headers={
                "Client-Id": cfg.TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {cfg.TWITCH_BEARER}",
            },
        )
