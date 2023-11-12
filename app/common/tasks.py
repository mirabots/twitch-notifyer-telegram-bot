from datetime import datetime
from string import Template

from aiogram import Bot, types
from aiogram.utils.formatting import Bold, Text
from crud import subscriptions as crud_subs
from twitch import functions as twitch


async def send_notifications_to_chats(bot: Bot, event: dict, message_id: str) -> None:
    streamer_id = event.get("broadcaster_user_id", "0")
    streamer_login = event.get("broadcaster_user_login", "")
    streamer_name = event.get("broadcaster_user_name", "")

    print(f"Notification ({message_id}): {streamer_login} ({streamer_id})")
    if not (await crud_subs.check_streamer(streamer_id)):
        print("ERROR: Streamer not in db")
        return

    if await crud_subs.check_duplicate_event_message(streamer_id, message_id):
        print("ERROR: Duplicated event message")
        return

    stream_info = await twitch.get_stream_info(streamer_id)
    if not stream_info:
        print("WARNING: No stream info from Twitch API")
        stream_info = await twitch.get_channel_info(streamer_id)
        if not stream_info:
            print("WARNING: No channel info from Twitch API")
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

    utc_now = datetime.utcnow().strftime("%Y_%m_%d_%H_%M_%S")
    stream_picture = types.URLInputFile(
        stream_info["thumbnail_url"].format(width="1920", height="1080"),
        filename=f"{streamer_login}_{utc_now}.jpg",
        bot=bot,
    )

    chats = await crud_subs.get_subscribed_chats(streamer_id)
    print(f"Chats: {[chat['id'] for chat in chats]}")

    for chat in chats:
        template = Template(chat["template"] or "$streamer_name started stream")
        filled_template = template.safe_substitute({"streamer_name": streamer_name})

        message = Text(
            Bold(filled_template),
            f"\n{stream_details}\n",
            Bold(f"twitch.tv/{streamer_login}"),
        )
        message_text, message_entities = message.render()
        await bot.send_photo(
            chat_id=chat["id"],
            photo=stream_picture,
            caption=message_text,
            caption_entities=message_entities,
        )
