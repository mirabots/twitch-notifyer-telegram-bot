import hashlib
import hmac

from common.config import cfg
from litestar import Request
from litestar.exceptions import HTTPException


def verify_telegram_secret(headers: dict[str, str]) -> None:
    try:
        header_secret = headers.get("X-Telegram-Bot-Api-Secret-Token".lower(), "")
        if header_secret != cfg.TELEGRAM_SECRET:
            raise HTTPException(status_code=401, detail="NOT VERIFIED")
    except Exception:
        raise HTTPException(status_code=401, detail="NOT VERIFIED")


async def verify_twitch_secret(request: Request) -> None:
    try:
        body = (await request.body()).decode()
        sended_HMAC = request.headers.get(
            "Twitch-Eventsub-Message-Signature".lower()
        ).lower()
        server_HMAC = (
            "sha256="
            + hmac.new(
                cfg.TWITCH_SUBSCRIPTION_SECRET.encode(),
                (
                    request.headers.get("Twitch-Eventsub-Message-Id".lower())
                    + request.headers.get("Twitch-Eventsub-Message-Timestamp".lower())
                    + body
                ).encode(),
                hashlib.sha256,
            ).hexdigest()
        )
        if sended_HMAC != server_HMAC:
            raise HTTPException(status_code=403, detail="NOT VERIFIED")
    except Exception:
        raise HTTPException(status_code=403, detail="NOT VERIFIED")
