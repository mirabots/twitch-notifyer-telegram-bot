from datetime import datetime, timezone
from string import Template

from aiogram import types
from aiogram.utils.formatting import Bold, Text

from app.common.config import cfg
from app.common.utils import get_logger, levelDEBUG, levelINFO
from app.crud import subscriptions as crud_subs
from app.telegram.bot import bot
from app.twitch import functions as twitch

logger = get_logger(levelDEBUG if cfg.ENV == "dev" else levelINFO)


async def send_notifications_to_chats(event: dict, message_id: str) -> None:
    streamer_id = event.get("broadcaster_user_id", "0")
    streamer_login = event.get("broadcaster_user_login", "")
    streamer_name = event.get("broadcaster_user_name", "")

    logger.info(f"Notification ({message_id}): {streamer_login} ({streamer_id})")

    streamer_name_db = await crud_subs.check_streamer(streamer_id)
    if streamer_name_db == None:
        logger.error("Streamer not in db")
        return
    elif streamer_name_db != streamer_name:
        await crud_subs.update_streamer_name(streamer_id, streamer_name)

    if await crud_subs.check_duplicate_event_message(streamer_id, message_id):
        logger.error("Duplicated event message")
        return

    stream_info = await twitch.get_stream_info(streamer_id)
    if not stream_info:
        logger.warning("No stream info from Twitch API")
        stream_info = await twitch.get_channel_info(streamer_id)
        if not stream_info:
            logger.warning("No channel info from Twitch API")
        stream_info["thumbnail_url"] = (
            "https://static-cdn.jtvnw.net/previews-ttv/live_user_"
            + streamer_login
            + "-{width}x{height}.jpg"
        )

    stream_title = stream_info.get("title", "")
    stream_category = stream_info.get("category", "")
    stream_details = ""

    if stream_title:
        stream_details += f"\n● {stream_title}"
    if stream_category:
        stream_details += f"\n○ {stream_category}"
    if stream_details:
        stream_details += "\n"

    stream_picture = None

    chats = await crud_subs.get_subscribed_chats(streamer_id)
    logger.info(f"Chats: {[chat['id'] for chat in chats]}")

    for chat in chats:
        template = Template(chat["template"] or "$streamer_name started stream")
        filled_template = template.safe_substitute({"streamer_name": streamer_name})

        message = Text(
            Bold(filled_template),
            f"\n{stream_details}\n",
            Bold(f"twitch.tv/{streamer_login}"),
        )
        message_text, message_entities = message.render()

        if chat["picture_mode"] == "Disabled":
            await bot.send_message(
                chat_id=chat["id"],
                text=message_text,
                entities=message_entities,
                link_preview_options=types.LinkPreviewOptions(is_disabled=True),
            )
        elif chat["picture_mode"] == "Stream start screenshot":
            if stream_picture == None:
                utc_now = datetime.now(tz=timezone.utc).strftime("%Y_%m_%d_%H_%M_%S")
                stream_picture = types.URLInputFile(
                    stream_info["thumbnail_url"].format(width="1920", height="1080"),
                    filename=f"{streamer_login}_{utc_now}.jpg",
                    bot=bot,
                )

            await bot.send_photo(
                chat_id=chat["id"],
                photo=stream_picture,
                caption=message_text,
                caption_entities=message_entities,
            )
        else:
            pass


async def revoke_subscriptions(event: dict) -> None:
    streamer_id = event.get("condition", {}).get("broadcaster_user_id", "0")
    reason = event.get("status", "")

    streamer_name_db = await crud_subs.check_streamer(streamer_id)
    if streamer_name_db == None:
        logger.error("Streamer not in db")
        return

    users = await crud_subs.get_subscribed_users(streamer_id)
    logger.info(
        f"Revoke subscription for {streamer_name_db}({streamer_id}). Chats: {users}"
    )

    await crud_subs.remove_streamer(streamer_id)
    await crud_subs.remove_streamer_subscriptions(streamer_id)

    message = Text(
        "Subscription to ",
        Bold(streamer_name_db),
        " was revoked by twitch\n",
        Bold("Reason: "),
        reason,
    )
    message_text, message_entities = message.render()
    for user in users:
        await bot.send_message(
            chat_id=user, text=message_text, entities=message_entities
        )
