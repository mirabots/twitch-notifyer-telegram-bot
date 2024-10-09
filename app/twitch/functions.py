from app.common.config import cfg
from app.common.utils import get_logger, levelDEBUG, levelINFO
from app.twitch.api import (
    _auth,
    _get_channel_info,
    _get_costs,
    _get_stream_info,
    _get_streamer_id,
    _get_streamer_picture,
    _get_streamers_names,
    _subscribe_event,
    _unsubscribe_event,
)

logger = get_logger(levelDEBUG if cfg.ENV == "dev" else levelINFO)


async def get_streamer_id(streamer_name: str) -> str:
    answer = await _get_streamer_id(streamer_name)
    if answer.status_code == 401:
        await _auth()
        answer = await _get_streamer_id(streamer_name)

    if answer.status_code != 200:
        logger.error("get id error")
        return ""

    answer_json = answer.json()
    if not answer_json["data"]:
        return ""
    return answer_json["data"][0]["id"]


async def get_streamers_names(streamers_ids: list[str]) -> dict[str, str]:
    answer = await _get_streamers_names(streamers_ids)
    if answer.status_code == 401:
        await _auth()
        answer = await _get_streamers_names(streamers_ids)

    answer_json = answer.json()
    return {
        streamer["id"]: streamer["display_name"] for streamer in answer_json["data"]
    }


async def get_streamer_picture(streamer_id: str) -> str:
    answer = await _get_streamer_picture(streamer_id)
    if answer.status_code == 401:
        await _auth()
        answer = await _get_streamer_picture(streamer_id)
    if answer.status_code != 200:
        logger.error("get picture error")
        return ""

    answer_json = answer.json()
    if not answer_json["data"]:
        return ""
    return answer_json["data"][0]["profile_image_url"]


async def get_stream_info(streamer_id: str) -> dict[str, str]:
    answer = await _get_stream_info(streamer_id)
    if answer.status_code == 401:
        await _auth()
        answer = await _get_stream_info(streamer_id)
    if answer.status_code != 200:
        logger.error("get stream info error")
        return {}
    answer_json = answer.json()
    if not answer_json["data"]:
        return {}
    return {
        "title": answer_json["data"][0]["title"],
        "category": answer_json["data"][0]["game_name"],
        "thumbnail_url": answer_json["data"][0]["thumbnail_url"],
    }


async def get_channel_info(streamer_id: str) -> dict[str, str]:
    answer = await _get_channel_info(streamer_id)
    if answer.status_code == 401:
        await _auth()
        answer = await _get_channel_info(streamer_id)
    if answer.status_code != 200:
        logger.error("get channel info error")
        return {}
    answer_json = answer.json()
    if not answer_json["data"]:
        return {}
    return {
        "title": answer_json["data"][0]["title"],
        "category": answer_json["data"][0]["game_name"],
    }


async def subscribe_event(streamer_id: str, event_type: str) -> str:
    answer = await _subscribe_event(streamer_id, event_type)
    if answer.status_code == 401:
        await _auth()
        answer = await _subscribe_event(streamer_id, event_type)
    if answer.status_code != 202:
        logger.error("subscribe error")
        return ""

    answer_json = answer.json()
    if not answer_json["data"]:
        return ""
    return answer_json["data"][0]["id"]


async def unsubscribe_event(event_id: str) -> None:
    answer = await _unsubscribe_event(event_id)
    if answer.status_code == 401:
        await _auth()
        answer = await _unsubscribe_event(event_id)
    if answer.status_code != 204:
        logger.error("unsubscribe error")


async def get_costs() -> dict[str, int]:
    answer = await _get_costs()
    if answer.status_code == 401:
        await _auth()
        answer = await _get_costs()
    if answer.status_code != 200:
        logger.error("get costs info error")
        return {}
    answer_json = answer.json()
    return {
        "total": answer_json["total"],
        "total_cost": answer_json["total_cost"],
        "max_total_cost": answer_json["max_total_cost"],
    }
