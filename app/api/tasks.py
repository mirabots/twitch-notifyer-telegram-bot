import asyncio
import traceback
from contextlib import suppress
from datetime import datetime, timezone
from string import Template

from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.formatting import Bold, Text
from common.config import cfg
from crud import streamers as crud_streamers
from crud import subscriptions as crud_subs
from telegram.bot import bot
from twitch import functions as twitch


async def send_notifications_to_chats(event: dict, message_id: str) -> None:
    try:
        streamer_id = event.get("broadcaster_user_id", "0")
        streamer_login = event.get("broadcaster_user_login", "")
        streamer_name = event.get("broadcaster_user_name", "")

        cfg.logger.info(
            f"Notification ({message_id}): {streamer_login} ({streamer_id})"
        )

        streamer_name_db = await crud_streamers.check_streamer(streamer_id)
        if streamer_name_db == None:
            cfg.logger.error("Streamer not in db")
            return
        elif streamer_name != "" and streamer_name_db != streamer_name:
            await crud_streamers.update_streamer_name(streamer_id, streamer_name)
            streamer_name_db = streamer_name

        streamer_login = event.get("broadcaster_user_login", streamer_name_db.lower())
        streamer_name = event.get("broadcaster_user_name", streamer_name_db)

        if await crud_streamers.check_duplicate_event_message(streamer_id, message_id):
            cfg.logger.error("Duplicated event message")
            return

        stream_info = await twitch.get_stream_info(streamer_id)
        if not stream_info:
            cfg.logger.warning("No stream info from Twitch API")
            stream_info = await twitch.get_channel_info(streamer_id)
            if not stream_info:
                cfg.logger.warning("No channel info from Twitch API")
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

        stream_picture_id = None

        chats = await crud_subs.get_subscribed_chats(streamer_id)
        cfg.logger.info(f"Chats: {[chat['id'] for chat in chats]}")

        for chat in chats:
            template = Template(chat["template"] or "$streamer_name started stream")
            filled_template = template.safe_substitute({"streamer_name": streamer_name})
            if chat["template"] == "":
                filled_template = ""

            links = [f"twitch.tv/{streamer_login}", *(chat["restreams_links"] or [])]

            message = Text(
                Bold(filled_template) if filled_template else "",
                f"\n{stream_details}\n",
                Bold("\n".join(links)),
            )
            message_text, message_entities = message.render()

            if chat["picture_mode"] == "Disabled":
                with suppress(TelegramBadRequest):
                    await bot.send_message(
                        chat_id=chat["id"],
                        text=message_text,
                        entities=message_entities,
                        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
                        request_timeout=120.0,
                    )
            elif chat["picture_mode"] == "Stream start screenshot":
                stream_picture = None
                if stream_picture_id == None:
                    utc_now = datetime.now(tz=timezone.utc).strftime(
                        "%Y_%m_%d_%H_%M_%S"
                    )
                    stream_picture = types.URLInputFile(
                        stream_info["thumbnail_url"].format(
                            width="1920", height="1080"
                        ),
                        filename=f"{streamer_login}_{utc_now}.jpg",
                    )

                with suppress(TelegramBadRequest):
                    sended_message = await bot.send_photo(
                        chat_id=chat["id"],
                        photo=(stream_picture_id or stream_picture),
                        caption=message_text,
                        caption_entities=message_entities,
                        request_timeout=120.0,
                    )
                if stream_picture_id == None:
                    file_size = 0
                    for photo in sended_message.photo:
                        if photo.file_size > file_size:
                            stream_picture_id = photo.file_id
            elif chat["picture_mode"] == "Own pic":
                with suppress(TelegramBadRequest):
                    await bot.send_photo(
                        chat_id=chat["id"],
                        photo=chat["picture_id"],
                        caption=message_text,
                        caption_entities=message_entities,
                        request_timeout=120.0,
                    )
            else:
                pass

            cfg.logger.info(f"Chat {chat['id']} sended with {chat['picture_mode']}")
            await asyncio.sleep(1)
    except Exception as exc:
        if cfg.ENV != "dev":
            with suppress(TelegramBadRequest):
                await bot.send_message(
                    chat_id=cfg.TELEGRAM_BOT_OWNER_ID,
                    text=f"ADMIN MESSAGE\nNOTIFICATION ERROR\n{exc}",
                )
        cfg.logger.error(exc)
        traceback.print_exception(exc)


async def revoke_subscriptions(event: dict) -> None:
    try:
        streamer_id = event.get("condition", {}).get("broadcaster_user_id", "0")
        reason = event.get("status", "")

        streamer_name_db = await crud_streamers.check_streamer(streamer_id)
        if streamer_name_db == None:
            cfg.logger.error("Streamer not in db")
            return

        users = await crud_subs.get_subscribed_users(streamer_id)
        cfg.logger.info(
            f"Revoke subscription for {streamer_name_db}({streamer_id}). Chats: {users}"
        )

        await crud_streamers.remove_streamer(streamer_id)
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
            with suppress(TelegramBadRequest):
                await bot.send_message(
                    chat_id=user, text=message_text, entities=message_entities
                )
            await asyncio.sleep(1)
        if cfg.TELEGRAM_BOT_OWNER_ID not in users:
            message = Text(
                "ADMIN MESSAGE\nSubscription to ",
                Bold(f"{streamer_name_db} ({streamer_id})"),
                " was revoked by twitch\n",
                Bold("Reason: "),
                reason,
            )
            message_text, message_entities = message.render()
            with suppress(TelegramBadRequest):
                await bot.send_message(
                    chat_id=cfg.TELEGRAM_BOT_OWNER_ID,
                    text=message_text,
                    entities=message_entities,
                )
    except Exception as exc:
        if cfg.ENV != "dev":
            with suppress(TelegramBadRequest):
                await bot.send_message(
                    chat_id=cfg.TELEGRAM_BOT_OWNER_ID,
                    text=f"ADMIN MESSAGE\nREVOKATION ERROR\n{exc}",
                )
        cfg.logger.error(exc)
        traceback.print_exception(exc)
