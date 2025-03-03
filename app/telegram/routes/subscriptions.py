from collections import namedtuple
from contextlib import suppress
from datetime import datetime, timezone
from enum import Enum
from string import Template

from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils import formatting
from common.config import cfg
from crud import chats as crud_chats
from crud import streamers as crud_streamers
from crud import subscriptions as crud_subs
from telegram.commands import get_command
from telegram.utils.callbacks import (
    CallbackChannelsRemove,
    CallbackChooseChannel,
    CallbackChooseChat,
    CallbackChooseStreamer,
    CallbackPicture,
    CallbackTemplateMode,
    get_choosed_callback_text,
)
from telegram.utils.forms import (
    FormChangeTemplate,
    FormlimitRequestMessage,
    FormPicture,
    FormSubscribe,
)
from telegram.utils.keyboards import (
    get_keyboard_abort,
    get_keyboard_channels,
    get_keyboard_channels_remove,
    get_keyboard_chats,
    get_keyboard_picture,
    get_keyboard_streamers,
    get_keyboard_template_mode,
)
from twitch import functions as twitch

router = Router()


@router.message(Command("channels"))
async def user_channels_handler(message: types.Message, bot: Bot):
    bot_name = (await bot.me()).username
    bot_channel_link = (
        f"tg://resolve?domain={bot_name}&startchannel&admin=post_messages"
    )
    message_text_list = [
        formatting.TextLink(
            "Use this link to select channel and add bot (with only admin ",
            formatting.Bold(formatting.Italic("POST MESSAGES")),
            " permission)",
            url=bot_channel_link,
        ),
        "\nFor removal channel delete bot from channel's admins (not members menu) or use button below",
    ]
    user_id = message.from_user.id
    chats = await crud_chats.get_user_chats(user_id)
    message_text_list.append(f"\n\nOwned chats/channels ({len(chats)}):")
    for chat_id in chats:
        chat_info = await bot.get_chat(chat_id)
        message_text_list.append(
            f"\n● {chat_info.title or 'BOT CHAT'} ({chat_info.type})"
        )
    message_text = formatting.Text(*message_text_list)

    reply_markup = None
    if len(chats) > 1:
        main_keyboard = get_keyboard_channels_remove()
        reply_markup = main_keyboard.as_markup()

    with suppress(TelegramBadRequest):
        await message.answer(**message_text.as_kwargs(), reply_markup=reply_markup)


@router.callback_query(CallbackChannelsRemove.filter())
async def user_channels_remove_handler(callback: types.CallbackQuery, bot: Bot):
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)

    user_id = callback.from_user.id
    chats_ids = await crud_chats.get_user_chats(user_id)
    message_text = "No channels"
    reply_markup = None
    if len(chats_ids) > 1:
        message_text = "Choose channel to remove:"
        channels = [
            await bot.get_chat(chat_id) for chat_id in chats_ids if chat_id != user_id
        ]
        main_keyboard = get_keyboard_channels(channels, "chnlr")
        main_keyboard.adjust(3)
        abort_keyboard = get_keyboard_abort("chnlr")
        main_keyboard.attach(abort_keyboard)
        reply_markup = main_keyboard.as_markup()

    with suppress(TelegramBadRequest):
        await callback.message.answer(text=message_text, reply_markup=reply_markup)


@router.callback_query(CallbackChooseChannel.filter(F.action == "chnlr"))
async def user_channel_remove_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChannel, bot: Bot
):
    channel_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    channel_id = callback_data.id

    await bot.leave_chat(channel_id)
    await crud_chats.remove_chats([channel_id])
    subscriptions = await crud_subs.remove_unsubscribed_streamers()
    for subscription_id in subscriptions:
        await twitch.unsubscribe_event(subscription_id)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"Channel '{channel_name}' was removed with it's subscriptions",
            reply_markup=None,
        )


@router.message(Command("subscriptions"))
@router.message(Command("subscribe"))
@router.message(Command("unsubscribe"))
@router.message(Command("template"))
@router.message(Command("picture"))
@router.message(Command("notification_test"))
async def chats_handler(message: types.Message, bot: Bot):
    command = get_command(message.text)
    user_id = message.from_user.id

    ACTONS_TEXTS = namedtuple("ACTONS_TEXTS", ["action", "text"])

    class ACTONS(Enum):
        SUBSCRIPTIONS = ACTONS_TEXTS("subs", "Stream subscriptions list")
        SUBSCRIBE = ACTONS_TEXTS("sub", "Subscribe to stream notification")
        UNSUBSCRIBE = ACTONS_TEXTS("unsub", "Unsubscribe from stream notification")
        TEMPLATE = ACTONS_TEXTS("tmplt", "Change notification template")
        PICTURE = ACTONS_TEXTS("pctr", "Change notification picture mode")
        NOTIFICATION_TEST = ACTONS_TEXTS("ntfctn", "Test notification")

    action, action_string = ACTONS[command.upper()].value

    chats_ids = await crud_chats.get_user_chats(user_id)
    chats = [await bot.get_chat(chat_id) for chat_id in chats_ids]

    main_keyboard = get_keyboard_chats(chats, action)
    main_keyboard.adjust(3)
    abort_keyboard = get_keyboard_abort(action)
    main_keyboard.attach(abort_keyboard)
    reply_markup = main_keyboard.as_markup()

    message_string = "Choose chat/channel:"
    subs_count, subs_count_unique = await crud_subs.get_user_subscription_count(user_id)
    if subs_count == 0 and action != "sub":
        message_string = "No subscriptions"
        reply_markup = None
    if action in ("subs", "sub", "unsub"):
        subs_limit = cfg.TELEGRAM_USERS[user_id]["limit"]
        with suppress(TelegramBadRequest):
            await message.answer(
                text=f"Subs count: {subs_count} ({subs_count_unique} unique) / {subs_limit}"
            )

        if action == "sub":
            if subs_limit != None and subs_count_unique >= subs_limit:
                message_string = "You reached subscription limit!"
                reply_markup = None

    with suppress(TelegramBadRequest):
        await message.answer(
            text=f"{action_string}\n{message_string}",
            reply_markup=reply_markup,
        )


@router.callback_query(CallbackChooseChat.filter(F.action == "subs"))
async def subscriptions_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChat
):
    chat_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"Stream subscriptions list\n'{chat_name}' choosen", reply_markup=None
        )
    streamers = await crud_subs.get_subscribed_streamers(callback_data.id)
    user_streamers_online = await twitch.get_streams_info(list(streamers.keys()))
    if not streamers:
        message_text = formatting.Text("No subscriptions")
    else:
        streamers_sorted = sorted(
            [
                (
                    streamers[id],
                    user_streamers_online.get(id, {}).get("title"),
                    user_streamers_online.get(id, {}).get("category"),
                )
                for id in streamers
            ],
            key=lambda tup: tup[0].lower(),
        )

        message_text = formatting.as_marked_section(
            formatting.Bold(f"Count: {len(streamers)}"),
            *[
                formatting.Text(
                    formatting.TextLink(name, url=f"https://twitch.tv/{name.lower()}"),
                    f" ({category})" if category else "",
                    f" — {title}" if title else "",
                )
                for name, title, category in streamers_sorted
            ],
            marker="● ",
        )

    with suppress(TelegramBadRequest):
        await callback.message.answer(
            **message_text.as_kwargs(),
            link_preview_options=types.LinkPreviewOptions(is_disabled=True),
            reply_markup=None,
        )


@router.callback_query(CallbackChooseChat.filter(F.action == "sub"))
async def subscribe_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChat, state: FSMContext
):
    user_id = callback.from_user.id
    _, subs_count_unique = await crud_subs.get_user_subscription_count(user_id)
    subs_limit = cfg.TELEGRAM_USERS[user_id]["limit"]
    if subs_limit != None and subs_count_unique >= subs_limit:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(
                text="You reached subscription limit!", reply_markup=None
            )
        return

    chat_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"Subscribe to stream notification\n'{chat_name}' choosen",
            reply_markup=None,
        )
    abort_keyboard = get_keyboard_abort(callback_data.action)
    with suppress(TelegramBadRequest):
        sended_message = await callback.message.answer(
            text="Enter streamer name:",
            reply_markup=abort_keyboard.as_markup(),
        )

        await state.set_data(
            {
                "chat_id": callback_data.id,
                "outgoing_form_message_id": sended_message.message_id,
            }
        )
        await state.set_state(FormSubscribe.streamer_name)


@router.message(FormSubscribe.streamer_name)
async def subscribe_form(message: types.Message, state: FSMContext, bot: Bot) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]
    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )

    chat_id = state_data["chat_id"]
    await state.clear()

    streamer_login = message.text.strip().lower()
    streamer_info = await twitch.get_streamer_info(streamer_login)
    if not streamer_info:
        with suppress(TelegramBadRequest):
            await message.answer(text="No streamer with this name")
        return
    streamer_id = streamer_info["id"]
    streamer_name = streamer_info["name"]

    if (await crud_streamers.check_streamer(streamer_id)) == None:
        subscription_id = await twitch.subscribe_event(streamer_id, "stream.online")
        if not subscription_id:
            with suppress(TelegramBadRequest):
                await message.answer(text="Subscription error from twitch")
            return
        await crud_streamers.add_streamer(streamer_id, streamer_name, subscription_id)

    newly_subbed = await crud_subs.subscribe_to_streamer(chat_id, streamer_id)
    message_text = "Subscribed for notifications"
    if not newly_subbed:
        message_text = "Already subscribed!"
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.callback_query(CallbackChooseChat.filter(F.action == "unsub"))
async def unsubscribe_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChat
):
    chat_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    chat_id = callback_data.id

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"Unsubscribe from stream notification\n'{chat_name}' choosen",
            reply_markup=None,
        )
    streamers = await crud_subs.get_subscribed_streamers(chat_id)
    if not streamers:
        with suppress(TelegramBadRequest):
            await callback.message.answer(text="No subscriptions", reply_markup=None)
    else:
        main_keyboard = get_keyboard_streamers("unsub", streamers, chat_id)
        main_keyboard.adjust(3)
        abort_keyboard = get_keyboard_abort(callback_data.action)
        main_keyboard.attach(abort_keyboard)

        with suppress(TelegramBadRequest):
            await callback.message.answer(
                text="Choose streamer:",
                reply_markup=main_keyboard.as_markup(),
            )


@router.callback_query(CallbackChooseStreamer.filter(F.action == "unsub"))
async def unsubscribe_streamer_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseStreamer
):
    streamer_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    await crud_subs.unsubscribe_from_streamer(
        callback_data.chat_id, callback_data.streamer_id
    )
    subscriptions = await crud_subs.remove_unsubscribed_streamers()
    for subscription_id in subscriptions:
        await twitch.unsubscribe_event(subscription_id)

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"Unsubscribed from '{streamer_name}'", reply_markup=None
        )


@router.callback_query(CallbackChooseChat.filter(F.action == "tmplt"))
async def template_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChat
):
    chat_id = callback_data.id
    chat_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"Change notification template\n'{chat_name}' choosen",
            reply_markup=None,
        )
    streamers = await crud_subs.get_subscribed_streamers(chat_id)
    if not streamers:
        with suppress(TelegramBadRequest):
            await callback.message.answer(text="No subscriptions", reply_markup=None)
    else:
        main_keyboard = get_keyboard_streamers("tmplt", streamers, chat_id)
        main_keyboard.adjust(3)
        abort_keyboard = get_keyboard_abort(callback_data.action)
        main_keyboard.attach(abort_keyboard)

        with suppress(TelegramBadRequest):
            await callback.message.answer(
                text="Choose streamer:",
                reply_markup=main_keyboard.as_markup(),
            )


@router.callback_query(CallbackChooseStreamer.filter(F.action == "tmplt"))
async def template_streamer_handler(
    callback: types.CallbackQuery,
    callback_data: CallbackChooseStreamer,
    state: FSMContext,
):
    streamer_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"'{streamer_name}' choosen", reply_markup=None
        )

    main_keyboard = get_keyboard_template_mode(
        callback_data.streamer_id, callback_data.chat_id
    )
    abort_keyboard = get_keyboard_abort(callback_data.action)
    main_keyboard.attach(abort_keyboard)
    with suppress(TelegramBadRequest):
        sended_message = await callback.message.answer(
            text="Enter new template\nDefault is:\n$streamer_name started stream",
            reply_markup=main_keyboard.as_markup(),
        )

        await state.set_data(
            {
                "chat_id": callback_data.chat_id,
                "streamer_id": callback_data.streamer_id,
                "outgoing_form_message_id": sended_message.message_id,
            }
        )
        await state.set_state(FormChangeTemplate.template_text)


@router.message(FormChangeTemplate.template_text)
async def template_text_form(
    message: types.Message, state: FSMContext, bot: Bot
) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]

    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )

    chat_id = state_data["chat_id"]
    streamer_id = state_data["streamer_id"]
    await state.clear()

    await crud_subs.change_template(chat_id, streamer_id, message.text.rstrip())
    with suppress(TelegramBadRequest):
        await message.answer(text="New template was set")


@router.callback_query(CallbackTemplateMode.filter())
async def template_mode_handler(
    callback: types.CallbackQuery,
    callback_data: CallbackTemplateMode,
    state: FSMContext,
):
    mode_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    await state.clear()

    new_template = None
    if mode_name == "Empty":
        new_template = ""
    await crud_subs.change_template(
        callback_data.chat_id, callback_data.streamer_id, new_template
    )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"{mode_name} template was set",
            reply_markup=None,
        )


@router.callback_query(CallbackChooseChat.filter(F.action == "pctr"))
async def picture_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChat
):
    chat_id = callback_data.id
    chat_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"Change notification picture mode\n'{chat_name}' choosen",
            reply_markup=None,
        )
    streamers = await crud_subs.get_subscribed_streamers(chat_id)
    if not streamers:
        with suppress(TelegramBadRequest):
            await callback.message.answer(text="No subscriptions", reply_markup=None)
    else:
        main_keyboard = get_keyboard_streamers("pctr", streamers, chat_id)
        main_keyboard.adjust(3)
        abort_keyboard = get_keyboard_abort(callback_data.action)
        main_keyboard.attach(abort_keyboard)

        with suppress(TelegramBadRequest):
            await callback.message.answer(
                text="Choose streamer:",
                reply_markup=main_keyboard.as_markup(),
            )


@router.callback_query(CallbackChooseStreamer.filter(F.action == "pctr"))
async def picture_streamer_handler(
    callback: types.CallbackQuery,
    callback_data: CallbackChooseStreamer,
):
    streamer_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    streamer_id = callback_data.streamer_id
    chat_id = callback_data.chat_id

    current_picture_mode = await crud_subs.get_current_picture_mode(
        chat_id, streamer_id
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"'{streamer_name}' choosen", reply_markup=None
        )
    main_keyboard = get_keyboard_picture(streamer_id, chat_id)
    abort_keyboard = get_keyboard_abort(callback_data.action)
    main_keyboard.attach(abort_keyboard)
    with suppress(TelegramBadRequest):
        await callback.message.answer(
            text=f"Current mode: '{current_picture_mode}'",
            reply_markup=main_keyboard.as_markup(),
        )


@router.callback_query(CallbackPicture.filter())
async def picture_streamer_mode_handler(
    callback: types.CallbackQuery,
    callback_data: CallbackPicture,
    state: FSMContext,
) -> None:
    picture_mode = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    streamer_id = callback_data.streamer_id
    chat_id = callback_data.chat_id

    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)

    if picture_mode == "Own pic":
        abort_keyboard = get_keyboard_abort("pctr")
        with suppress(TelegramBadRequest):
            sended_message = await callback.message.answer(
                text="Send picture in landscape mode and at least 1000px width:",
                reply_markup=abort_keyboard.as_markup(),
            )
            await state.set_data(
                {
                    "chat_id": chat_id,
                    "streamer_id": streamer_id,
                    "outgoing_form_message_id": sended_message.message_id,
                }
            )
            await state.set_state(FormPicture.new_picture)
    else:
        await crud_subs.change_picture_mode(chat_id, streamer_id, picture_mode)
        with suppress(TelegramBadRequest):
            await callback.message.answer(text=f"New mode ('{picture_mode}') was set")


@router.message(FormPicture.new_picture)
async def picture_streamer_form(
    message: types.Message, state: FSMContext, bot: Bot
) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]

    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )

    chat_id = state_data["chat_id"]
    streamer_id = state_data["streamer_id"]
    await state.clear()

    message_text = "Own picture was set"
    if not message.photo:
        message_text = "No picture was send\nNo changes"
    else:
        orig_photo = types.PhotoSize(
            file_id="0", file_unique_id="0", width=0, height=0, file_size=0
        )
        for photo in message.photo:
            if photo.file_size > orig_photo.file_size:
                orig_photo = photo

        if orig_photo.width < 1000:
            message_text = f"Picture is small ({orig_photo.width}px width)\nNo changes"
        elif orig_photo.width < orig_photo.height:
            message_text = "Picture is not in landscape mode\nNo changes"
        else:
            await crud_subs.change_picture_mode(
                chat_id, streamer_id, "Own pic", orig_photo.file_id
            )
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.callback_query(CallbackChooseChat.filter(F.action == "ntfctn"))
async def notification_test_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChat
):
    chat_id = callback_data.id
    chat_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"Test notification\n'{chat_name}' choosen", reply_markup=None
        )
    streamers = await crud_subs.get_subscribed_streamers(chat_id)
    if not streamers:
        with suppress(TelegramBadRequest):
            await callback.message.answer(text="No subscriptions", reply_markup=None)
    else:
        main_keyboard = get_keyboard_streamers("ntfctn", streamers, chat_id)
        main_keyboard.adjust(3)
        abort_keyboard = get_keyboard_abort(callback_data.action)
        main_keyboard.attach(abort_keyboard)

        with suppress(TelegramBadRequest):
            await callback.message.answer(
                text="Choose streamer:",
                reply_markup=main_keyboard.as_markup(),
            )


@router.callback_query(CallbackChooseStreamer.filter(F.action == "ntfctn"))
async def notification_test_message_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseStreamer
):
    streamer_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    streamer_login = streamer_name.lower()
    chat_id = callback_data.chat_id
    streamer_id = callback_data.streamer_id

    current_picture_mode = await crud_subs.get_current_picture_mode(
        chat_id, streamer_id
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"'{streamer_name}' choosen\nCurrent picture mode: '{current_picture_mode}'",
            reply_markup=None,
        )

    subscription_info = await crud_subs.get_subscription(chat_id, streamer_id)
    sub_template = subscription_info.message_template
    sub_picture_mode = subscription_info.picture_mode
    sub_picture_id = subscription_info.picture_id

    stream_info = await twitch.get_channel_info(streamer_id)
    stream_info["thumbnail_url"] = (
        "https://static-cdn.jtvnw.net/previews-ttv/live_user_"
        + streamer_login
        + "-{width}x{height}.jpg"
    )

    default_title = "My awesome test stream title"
    default_category = "Just Chatting"
    stream_title = stream_info.get("title", default_title) or default_title
    stream_category = stream_info.get("category", default_category) or default_category
    stream_details = f"\n● {stream_title}\n○ {stream_category}\n"

    template = Template(sub_template or "$streamer_name started stream")
    filled_template = template.safe_substitute({"streamer_name": streamer_name})
    if sub_template == "":
        filled_template = ""

    message = formatting.Text(
        formatting.Bold(filled_template) if filled_template else "",
        f"\n{stream_details}\n",
        formatting.Bold(f"twitch.tv/{streamer_login}"),
    )
    message_text, message_entities = message.render()

    if sub_picture_mode == "Disabled":
        with suppress(TelegramBadRequest):
            await callback.message.answer(
                text=message_text,
                entities=message_entities,
                link_preview_options=types.LinkPreviewOptions(is_disabled=True),
            )
    elif sub_picture_mode == "Stream start screenshot":
        utc_now = datetime.now(tz=timezone.utc).strftime("%Y_%m_%d_%H_%M_%S")
        stream_picture = types.URLInputFile(
            stream_info["thumbnail_url"].format(width="1920", height="1080"),
            filename=f"{streamer_login}_{utc_now}.jpg",
        )

        with suppress(TelegramBadRequest):
            await callback.message.answer_photo(
                photo=stream_picture,
                caption=message_text,
                caption_entities=message_entities,
            )
    elif sub_picture_mode == "Own pic":
        with suppress(TelegramBadRequest):
            await callback.message.answer_photo(
                photo=sub_picture_id,
                caption=message_text,
                caption_entities=message_entities,
            )
    else:
        pass


@router.message(Command("online_streamers"))
async def online_streamers_handler(message: types.Message):
    user_id = message.from_user.id
    user_streamers = await crud_subs.get_user_subscribed_streamers(user_id)
    if not user_streamers:
        message_text = formatting.Text("No subscriptions")
    else:
        user_streamers_online = await twitch.get_streams_info(
            list(user_streamers.keys())
        )
        if not user_streamers_online:
            message_text = formatting.Text("No online streamers")
        else:
            user_streamers_online_sorted = sorted(
                [
                    (
                        user_streamers_online[id]["user_name"],
                        user_streamers_online[id]["title"],
                        user_streamers_online[id]["category"],
                    )
                    for id in user_streamers_online
                ],
                key=lambda tup: tup[0].lower(),
            )

            message_text = formatting.as_marked_section(
                formatting.Bold(f"Streamers online ({len(user_streamers_online)}):"),
                *[
                    formatting.Text(
                        formatting.TextLink(
                            name, url=f"https://twitch.tv/{name.lower()}"
                        ),
                        f" ({category})" if category else "",
                        f" — {title}" if title else "",
                    )
                    for name, title, category in user_streamers_online_sorted
                ],
                marker="● ",
            )

    with suppress(TelegramBadRequest):
        await message.answer(
            **message_text.as_kwargs(),
            link_preview_options=types.LinkPreviewOptions(is_disabled=True),
        )


@router.message(Command("limit_request"))
async def limit_request_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    subs_count, subs_count_unique = await crud_subs.get_user_subscription_count(user_id)
    subs_limit = cfg.TELEGRAM_USERS[user_id]["limit"]
    with suppress(TelegramBadRequest):
        await message.answer(
            text=f"Subs count: {subs_count} ({subs_count_unique} unique) / {subs_limit}"
        )
    abort_keyboard = get_keyboard_abort("lrmsg")
    with suppress(TelegramBadRequest):
        sended_message = await message.answer(
            text="Send limit request message to admin:",
            reply_markup=abort_keyboard.as_markup(),
        )

        await state.set_data({"outgoing_form_message_id": sended_message.message_id})
        await state.set_state(FormlimitRequestMessage.message)


@router.message(FormlimitRequestMessage.message)
async def limit_request_form(
    message: types.Message, state: FSMContext, bot: Bot
) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]
    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )
    await state.clear()

    answer_text = "Request was send"
    message_text = message.text or ""
    message_entities = message.entities or None
    if not message_text:
        answer_text = "Can't send empty message!"
    else:
        user_id = message.from_user.id
        user_name = cfg.TELEGRAM_USERS[user_id]["name"]
        admin_text = f"LIMIT REQUEST FROM {user_name} ({user_id}):\n"

        if message_entities:
            for entity in message_entities:
                entity.offset += len(admin_text.encode("utf-16-le").decode("utf-16-le"))

        with suppress(TelegramBadRequest):
            await bot.send_message(
                chat_id=cfg.TELEGRAM_BOT_OWNER_ID,
                text=f"{admin_text}{message_text}",
                entities=message_entities,
                link_preview_options=types.LinkPreviewOptions(is_disabled=True),
            )

    with suppress(TelegramBadRequest):
        await message.answer(text=answer_text)


@router.message(FormlimitRequestMessage.message)
async def limit_request_form2(
    message: types.Message, state: FSMContext, bot: Bot
) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]
    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )
    await state.clear()

    answer_text = "Request was send"
    message_text = message.text or ""
    message_entities = message.entities or None
    if not message_text:
        answer_text = "Can't send empty message!"
    else:
        crud.add_request(  # noqa
            message.from_user.id,
            message_text,
            message_entities.model_dump() if message_entities else None,
        )

    with suppress(TelegramBadRequest):
        await message.answer(text=answer_text)
