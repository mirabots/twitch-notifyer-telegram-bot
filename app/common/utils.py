import hashlib
import hmac

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .config import cfg


async def verify_telegram_secret(request: Request) -> None:
    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if header_secret != cfg.TELEGRAM_SECRET:
        raise HTTPException(status_code=401, detail="NOT VERIFIED")


async def verify_twitch_event(request: Request) -> None:
    body = (await request.body()).decode()
    sended_HMAC = request.headers.get("Twitch-Eventsub-Message-Signature").lower()
    server_HMAC = (
        "sha256="
        + hmac.new(
            cfg.TWITCH_SUBSCRIPTION_SECRET.encode(),
            (
                request.headers.get("Twitch-Eventsub-Message-Id")
                + request.headers.get("Twitch-Eventsub-Message-Timestamp")
                + body
            ).encode(),
            hashlib.sha256,
        ).hexdigest()
    )
    if sended_HMAC != server_HMAC:
        raise HTTPException(status_code=403, detail="NOT VERIFIED")


async def server_error(request, exc) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


exception_handlers = {500: server_error}
