from collections.abc import Awaitable, Callable

from httpx import Response

from app.common.config import cfg
from app.twitch.api import (
    _auth,
    _get_channel_info,
    _get_costs,
    _get_stream_info,
    _get_streamers_info,
    _subscribe_event,
    _unsubscribe_event,
)


async def _make_api_request(
    api_function: Callable[..., Awaitable[Response]], *args, **kwargs
) -> Response:
    try:
        answer = await api_function(*args, **kwargs)
        if answer.status_code == 401:
            await _auth()
            answer = await api_function(*args, **kwargs)
        return answer
    except Exception:
        return Response(status_code=-1, content="{}")


async def get_streamer_info(streamer_login: str) -> dict[str, str]:
    answer = await _make_api_request(_get_streamers_info, {"login": streamer_login})
    if answer.status_code != 200:
        cfg.logger.error(f"Getting streamer id error with code {answer.status_code}")
        return {}

    answer_json = answer.json()
    if not answer_json.get("data"):
        return {}
    return {
        "id": answer_json["data"][0]["id"],
        "name": answer_json["data"][0]["display_name"],
    }


async def get_streamers_names(streamers_ids: list[str]) -> dict[str, str]:
    correct_get = True
    result = {}
    slice_size = 100
    while streamers_ids:
        streamers_ids_slice = streamers_ids[:slice_size]
        answer = await _make_api_request(
            _get_streamers_info, {"id": streamers_ids_slice}
        )

        answer_json = answer.json()
        if not answer_json.get("data"):
            correct_get = False
            break
        else:
            result.update(
                {
                    streamer["id"]: streamer["display_name"]
                    for streamer in answer_json["data"]
                }
            )
        del streamers_ids[:slice_size]

    if not correct_get:
        return {}
    return result


async def get_stream_info(streamer_id: str) -> dict[str, str]:
    answer = await _make_api_request(_get_stream_info, streamer_id)
    if answer.status_code != 200:
        cfg.logger.error(f"Getting streamer info error with code {answer.status_code}")
        return {}

    answer_json = answer.json()
    if not answer_json.get("data"):
        return {}
    return {
        "title": answer_json["data"][0]["title"],
        "category": answer_json["data"][0]["game_name"],
        "thumbnail_url": answer_json["data"][0]["thumbnail_url"],
    }


async def get_channel_info(streamer_id: str) -> dict[str, str]:
    answer = await _make_api_request(_get_channel_info, streamer_id)
    if answer.status_code != 200:
        cfg.logger.error(f"Getting channel info error with code {answer.status_code}")
        return {}

    answer_json = answer.json()
    if not answer_json.get("data"):
        return {}
    return {
        "title": answer_json["data"][0]["title"],
        "category": answer_json["data"][0]["game_name"],
    }


async def subscribe_event(streamer_id: str, event_type: str) -> str:
    answer = await _make_api_request(_subscribe_event, streamer_id, event_type)
    if answer.status_code != 202:
        cfg.logger.error(
            f"Subscribe event ({event_type}) error with code {answer.status_code}"
        )
        return ""

    answer_json = answer.json()
    if not answer_json.get("data"):
        return ""
    return answer_json["data"][0]["id"]


async def unsubscribe_event(event_id: str) -> None:
    answer = await _make_api_request(_unsubscribe_event, event_id)
    if answer.status_code != 204:
        cfg.logger.error(f"Unsubscribe event error with code {answer.status_code}")


async def get_costs() -> dict[str, int]:
    answer = await _make_api_request(_get_costs)
    if answer.status_code != 200:
        cfg.logger.error(f"Getting costs info with error {answer.status_code}")
        return {}

    answer_json = answer.json()
    return {
        "total": answer_json["total"],
        "total_cost": answer_json["total_cost"],
        "max_total_cost": answer_json["max_total_cost"],
    }
