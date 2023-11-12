import time
from contextlib import suppress

from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import IS_ADMIN, IS_NOT_MEMBER, ChatMemberUpdatedFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils import formatting
from common.config import cfg
from crud import chats as crud_chats
from crud import subscriptions as crud_subs
from twitch import functions as twitch

from .utils import (
    CallbackAbort,
    CallbackChooseChat,
    CallbackChooseStreamer,
    CallbackDefault,
    FormChangeTemplate,
    FormSubscribe,
    get_choosed_callback_text,
    get_keyboard_abort,
    get_keyboard_chats,
    get_keyboard_default,
    get_keyboard_streamers,
)

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message):
    chat_id = message.chat.id
    owner_id = message.from_user.id

    print(
        f"Start: {owner_id=} {message.from_user.username=} {chat_id=} {time.asctime()}"
    )

    chat_added = await crud_chats.add_chat(chat_id, owner_id)
    message_text = (
        "Bot started, this chat was added\nUse /info for some information"
        if chat_added
        else "Bot already started"
    )
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_ADMIN))
async def start_channel_handler(event: types.ChatMemberUpdated, bot: Bot):
    if not cfg.BOT_ACTIVE:
        return
    if event.chat.type in ("group", "supergroup", "private"):
        return

    owner_name = event.from_user.username
    owner_id = event.from_user.id
    chat_id = event.chat.id

    if (
        not (await crud_chats.owner_exists(owner_id))
        or owner_name not in cfg.TELEGRAM_ALLOWED
    ):
        return

    print(
        f"Start: {owner_id=} {event.from_user.username=} {chat_id=} {event.chat.title=} {time.asctime()}"
    )

    chat_added = await crud_chats.add_chat(chat_id, owner_id)
    if chat_added:
        message_text = f"Notification\nChannel '{event.chat.title}' added"
        with suppress(TelegramBadRequest):
            await bot.send_message(chat_id=owner_id, text=message_text)


@router.message(Command("stop"))
async def stop_handler(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    owner_id = message.from_user.id

    print(f"Stop: {owner_id=} {message.from_user.username=} {time.asctime()}")

    owned_chats = await crud_chats.get_owned_chats(owner_id)
    if not owned_chats:
        message_text = "Bot already stopped"
        await message.answer(text=message_text)
        return

    await crud_chats.remove_chats(owned_chats)
    subscriptions = await crud_subs.remove_unsubscribed_streamers()
    for subscription_id in subscriptions:
        await twitch.unsubscribe_event(subscription_id)

    for chat_id in owned_chats:
        if chat_id != owner_id:
            await bot.leave_chat(chat_id)

    message_text = (
        "Bot stopped, owned chats/channels were leaved, streamers unsubscribed"
    )
    await message.answer(text=message_text)


@router.my_chat_member(ChatMemberUpdatedFilter(IS_ADMIN >> IS_NOT_MEMBER))
async def stop_channel_handler(event: types.ChatMemberUpdated, bot: Bot):
    if not cfg.BOT_ACTIVE:
        return
    if event.chat.type in ("group", "supergroup", "private"):
        return

    owner_name = event.from_user.username
    owner_id = event.from_user.id
    chat_id = event.chat.id

    if (
        not (await crud_chats.owner_exists(owner_id))
        or owner_name not in cfg.TELEGRAM_ALLOWED
    ):
        return

    print(
        f"Stop: {owner_id=} {event.from_user.username=} {chat_id=} {event.chat.title=} {time.asctime()}"
    )

    await crud_chats.remove_chats([chat_id])
    subscriptions = await crud_subs.remove_unsubscribed_streamers()
    for subscription_id in subscriptions:
        await twitch.unsubscribe_event(subscription_id)

    message_text = f"Notification\nBot leaved from channel '{event.chat.title}'"
    await bot.send_message(chat_id=owner_id, text=message_text)


@router.message(Command("info"))
async def info_handler(message: types.Message, bot: Bot):
    bot_name = (await bot.me()).username
    bot_channel_link = (
        f"tg://resolve?domain={bot_name}&startchannel&admin=post_messages"
    )

    info = formatting.as_marked_section(
        formatting.Bold("Here is simple instruction how to use bot:"),
        formatting.Text(
            "If you want to recieve notifications in channels, first of all, you need to add bot to the channel with only admin ",
            formatting.Italic("POST POSTS"),
            " permission ",
            formatting.TextLink("or use this link", url=bot_channel_link),
            ".",
        ),
        "Secondly, you need to add streamer subscription to chat/channel, using /subscribe command. That's all.",
        "Other commands (managing chats and streamers, changing notification text) can be found in command-menu near text-input.",
        marker="● ",
    )

    with suppress(TelegramBadRequest):
        await message.answer(**info.as_kwargs())


@router.message(Command("add_channel"))
async def add_channel_handler(message: types.Message, bot: Bot):
    bot_name = (await bot.me()).username
    bot_channel_link = (
        f"tg://resolve?domain={bot_name}&startchannel&admin=post_messages"
    )
    message_text = formatting.TextLink(
        "Use this link to select channel", url=bot_channel_link
    )

    with suppress(TelegramBadRequest):
        await message.answer(**message_text.as_kwargs())


@router.message(Command("chats"))
async def owned_chats_handler(message: types.Message, bot: Bot):
    owner_id = message.from_user.id

    chats = await crud_chats.get_owned_chats(owner_id)
    message_text = f"Owned chats/channels ({len(chats)}):"
    for chat_id in chats:
        chat_info = await bot.get_chat(chat_id)
        message_text += f"\n● {chat_info.title or 'ME'} ({chat_info.type})"
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.callback_query(CallbackAbort.filter())
async def abort_handler(
    callback: types.CallbackQuery, callback_data: CallbackAbort, state: FSMContext
):
    await state.clear()

    action = callback_data.action
    action_text = ""
    if action == "subs":
        action_text = "Getting subscriptions"
    if action == "sub":
        action_text = "Subscribe"
    if action == "unsub":
        action_text = "Unsubscribe"
    if action == "tmplt":
        action_text = "Changing template"

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"{action_text} operation was aborted".lstrip().capitalize(),
            reply_markup=None,
        )


@router.message(Command("subscriptions"))
@router.message(Command("subscribe"))
@router.message(Command("unsubscribe"))
@router.message(Command("template"))
async def chats_handler(message: types.Message, bot: Bot):
    command_text = message.text.rstrip()

    action = "subs"
    if "/subscribe" in command_text:
        action = "sub"
    if "/unsubscribe" in command_text:
        action = "unsub"
    if "/template" in command_text:
        action = "tmplt"

    chats_ids = await crud_chats.get_owned_chats(message.from_user.id)
    chats = [await bot.get_chat(chat_id) for chat_id in chats_ids]

    main_keyboard = get_keyboard_chats(chats, action)
    main_keyboard.adjust(3)
    abort_keyboard = get_keyboard_abort(action)
    main_keyboard.attach(abort_keyboard)
    with suppress(TelegramBadRequest):
        await message.answer(
            text="Choose chat/channel:", reply_markup=main_keyboard.as_markup()
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
            text=f"'{chat_name}' choosen", reply_markup=None
        )
        streamers = await crud_subs.get_subscriptions(callback_data.id)
        if not streamers:
            message_text = "No subscriptions"
        else:
            streamers_with_names = await twitch.get_streamers_names(streamers)
            message_text = (
                f"Subscriptions ({len(streamers_with_names)}):\n ●"
                + "\n● ".join(
                    sorted(
                        list(streamers_with_names.values()),
                        key=lambda name: name.lower(),
                    )
                )
            )

        await callback.message.answer(text=message_text, reply_markup=None)


@router.callback_query(CallbackChooseChat.filter(F.action == "sub"))
async def subscribe_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseChat, state: FSMContext
):
    chat_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"'{chat_name}' choosen", reply_markup=None
        )
        abort_keyboard = get_keyboard_abort(callback_data.action)
        sended_message = await callback.message.answer(
            text="Enter streamer name to subscribe:",
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
            chat_id=message.from_user.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )

    chat_id = state_data["chat_id"]
    await state.clear()

    streamer_name = message.text.rstrip().lower()

    streamer_id = await twitch.get_streamer_id(streamer_name)
    if not streamer_id:
        await message.answer(text="No streamer with this name")
        return

    if not (await crud_subs.check_streamer(streamer_id)):
        subscription_id = await twitch.subscribe_event(streamer_id, "stream.online")
        if not subscription_id:
            await message.answer(text="Subscription error from twitch")
            return
        await crud_subs.add_streamer(streamer_id, subscription_id)

    newly_subbed = await crud_subs.subscribe_to_streamer(chat_id, streamer_id)
    message_text = "Subscribed for notifications"
    if not newly_subbed:
        message_text = "Already subscribed!"
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
            text=f"'{chat_name}' choosen", reply_markup=None
        )
        streamers = await crud_subs.get_subscriptions(chat_id)
        if not streamers:
            await callback.message.answer(text="No subscriptions", reply_markup=None)
        else:
            streamers_with_names = await twitch.get_streamers_names(streamers)
            main_keyboard = get_keyboard_streamers(
                "unsub", streamers_with_names, chat_id
            )
            main_keyboard.adjust(3)
            abort_keyboard = get_keyboard_abort(callback_data.action)
            main_keyboard.attach(abort_keyboard)

            await callback.message.answer(
                text="Choose streamer to unsubscribe:",
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
            text=f"'{chat_name}' choosen", reply_markup=None
        )
        streamers = await crud_subs.get_subscriptions(chat_id)
        if not streamers:
            await callback.message.answer(text="No subscriptions", reply_markup=None)
        else:
            streamers_with_names = await twitch.get_streamers_names(streamers)
            main_keyboard = get_keyboard_streamers(
                "tmplt", streamers_with_names, chat_id
            )
            main_keyboard.adjust(3)
            abort_keyboard = get_keyboard_abort(callback_data.action)
            main_keyboard.attach(abort_keyboard)

            await callback.message.answer(
                text="Choose streamer to change template:",
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

        main_keyboard = get_keyboard_default(
            callback_data.action, callback_data.streamer_id, callback_data.chat_id
        )
        abort_keyboard = get_keyboard_abort(callback_data.action)
        main_keyboard.attach(abort_keyboard)
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
async def template_streamer_form(
    message: types.Message, state: FSMContext, bot: Bot
) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]

    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.from_user.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )

    chat_id = state_data["chat_id"]
    streamer_id = state_data["streamer_id"]
    await state.clear()

    await crud_subs.change_template(chat_id, streamer_id, message.text.rstrip())
    await message.answer(text="New template was set")


@router.callback_query(CallbackDefault.filter(F.action == "tmplt"))
async def template_default_handler(
    callback: types.CallbackQuery, callback_data: CallbackDefault, state: FSMContext
):
    await state.clear()

    await crud_subs.change_template(
        callback_data.chat_id, callback_data.streamer_id, None
    )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text="Default template was set",
            reply_markup=None,
        )
