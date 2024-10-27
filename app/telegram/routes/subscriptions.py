from contextlib import suppress

from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils import formatting

from app.common.config import cfg
from app.crud import chats as crud_chats
from app.crud import streamers as crud_streamers
from app.crud import subscriptions as crud_subs
from app.telegram.utils.callbacks import (
    CallbackChooseChat,
    CallbackChooseStreamer,
    CallbackDefault,
    CallbackPicture,
    get_choosed_callback_text,
)
from app.telegram.utils.forms import FormChangeTemplate, FormSubscribe
from app.telegram.utils.keyboards import (
    get_keyboard_abort,
    get_keyboard_chats,
    get_keyboard_default,
    get_keyboard_picture,
    get_keyboard_streamers,
)
from app.twitch import functions as twitch

router = Router()


@router.message(Command("add_channel"))
async def add_channel_handler(message: types.Message, bot: Bot):
    bot_name = (await bot.me()).username
    bot_channel_link = (
        f"tg://resolve?domain={bot_name}&startchannel&admin=post_messages"
    )
    message_text = formatting.Text(
        formatting.TextLink("Use this link", url=bot_channel_link),
        " to select channel and add bot (with only admin ",
        formatting.Italic("POST POSTS"),
        " permission).",
    )
    with suppress(TelegramBadRequest):
        await message.answer(**message_text.as_kwargs())


@router.message(Command("chats"))
async def user_chats_handler(message: types.Message, bot: Bot):
    user_id = message.from_user.id

    chats = await crud_chats.get_user_chats(user_id)
    message_text = f"Owned chats/channels ({len(chats)}):"
    for chat_id in chats:
        chat_info = await bot.get_chat(chat_id)
        message_text += f"\n● {chat_info.title or 'ME'} ({chat_info.type})"
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("subscriptions"))
@router.message(Command("subscribe"))
@router.message(Command("unsubscribe"))
@router.message(Command("template"))
@router.message(Command("picture"))
async def chats_handler(message: types.Message, bot: Bot):
    command_text = message.text.rstrip()
    user_id = message.from_user.id

    action = "subs"
    if "/subscribe" in command_text:
        action = "sub"
    if "/unsubscribe" in command_text:
        action = "unsub"
    if "/template" in command_text:
        action = "tmplt"
    if "/picture" in command_text:
        action = "pctr"

    chats_ids = await crud_chats.get_user_chats(user_id)
    chats = [await bot.get_chat(chat_id) for chat_id in chats_ids]

    main_keyboard = get_keyboard_chats(chats, action)
    main_keyboard.adjust(3)
    abort_keyboard = get_keyboard_abort(action)
    main_keyboard.attach(abort_keyboard)
    reply_markup = main_keyboard.as_markup()

    subs_string = ""
    message_string = "Choose chat/channel:"
    if action in ("subs", "sub", "unsub"):
        subs_count = await crud_subs.get_user_subscription_count(user_id)
        subs_limit = cfg.TELEGRAM_USERS[user_id]["limit"]
        subs_string = f"Subscriptions count: {subs_count}/{subs_limit}\n"

        if action == "sub":
            if subs_limit != None and subs_count >= subs_limit:
                message_string = "You reached subscription limit!"
                reply_markup = None

    with suppress(TelegramBadRequest):
        await message.answer(
            text=f"{subs_string}{message_string}", reply_markup=reply_markup
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
                f"Subscriptions ({len(streamers_with_names)}):\n● "
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

    if (await crud_streamers.check_streamer(streamer_id)) == None:
        subscription_id = await twitch.subscribe_event(streamer_id, "stream.online")
        if not subscription_id:
            await message.answer(text="Subscription error from twitch")
            return
        await crud_streamers.add_streamer(streamer_id, streamer_name, subscription_id)

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
            text=f"'{chat_name}' choosen", reply_markup=None
        )
        streamers = await crud_subs.get_subscriptions(chat_id)
        if not streamers:
            await callback.message.answer(text="No subscriptions", reply_markup=None)
        else:
            streamers_with_names = await twitch.get_streamers_names(streamers)
            main_keyboard = get_keyboard_streamers(
                "pctr", streamers_with_names, chat_id
            )
            main_keyboard.adjust(3)
            abort_keyboard = get_keyboard_abort(callback_data.action)
            main_keyboard.attach(abort_keyboard)

            await callback.message.answer(
                text="Choose streamer to change notification picture mode:",
                reply_markup=main_keyboard.as_markup(),
            )


@router.callback_query(CallbackChooseStreamer.filter(F.action == "pctr"))
async def picture_streamer_handler(
    callback: types.CallbackQuery,
    callback_data: CallbackChooseStreamer,
    state: FSMContext,
):
    streamer_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )

    with suppress(TelegramBadRequest):
        current_picture_mode = await crud_subs.get_current_picture_mode(
            callback_data.chat_id, callback_data.streamer_id
        )

        await callback.message.edit_text(
            text=f"'{streamer_name}' choosen", reply_markup=None
        )
        main_keyboard = get_keyboard_picture()
        abort_keyboard = get_keyboard_abort(callback_data.action)
        main_keyboard.attach(abort_keyboard)
        sended_message = await callback.message.answer(
            text=f"Change notification picture mode\nCurrent mode: '{current_picture_mode}'",
            reply_markup=main_keyboard.as_markup(),
        )

        await state.set_data(
            {
                "chat_id": callback_data.chat_id,
                "streamer_id": callback_data.streamer_id,
                "outgoing_form_message_id": sended_message.message_id,
            }
        )


@router.callback_query(CallbackPicture.filter())
async def picture_streamer_mode_handler(
    callback: types.CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    picture_mode = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]

    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=callback.from_user.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )

        chat_id = state_data["chat_id"]
        streamer_id = state_data["streamer_id"]
        if picture_mode == "New picture":
            pass
        else:
            await state.clear()

            await crud_subs.change_picture_mode(chat_id, streamer_id, picture_mode)
            await callback.message.answer(text=f"New mode ('{picture_mode}') was set")
