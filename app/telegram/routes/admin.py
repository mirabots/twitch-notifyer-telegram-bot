import json
from contextlib import suppress
from copy import copy
from datetime import datetime, timezone

from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from common.config import cfg
from crud import admin as crud_admin
from crud import chats as crud_chats
from crud import streamers as crud_streamers
from crud import subscriptions as crud_subs
from crud import users as crud_users
from telegram.commands import COMMANDS_ADMIN
from telegram.utils.callbacks import (
    CallbackChooseUser,
    CallbackDump,
    CallbackLimitDefault,
    CallbackUserLimit,
    CallbackUsersAction,
    get_choosed_callback_text,
)
from telegram.utils.forms import (
    FormBroadcastMessage,
    FormDump,
    FormLimitDefault,
    FormUserLimit,
    FromUserRename,
)
from telegram.utils.keyboards import (
    get_keyboard_abort,
    get_keyboard_dump,
    get_keyboard_limit_default,
    get_keyboard_user_limit,
    get_keyboard_users,
    get_keyboard_users_actions,
)
from twitch import functions as twitch
from versions import APP_VERSION_STRING

router = Router()


@router.message(Command("admin"))
async def admin_commands_handler(message: types.Message):
    message_text = "Available admin commands:"
    for command, description in COMMANDS_ADMIN.items():
        message_text += f"\n● {description}\n○ /{command}"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("version"))
async def version_handler(message: types.Message):
    with suppress(TelegramBadRequest):
        await message.answer(text=APP_VERSION_STRING)


@router.message(Command("pause"))
async def bot_active_handler(message: types.Message):
    if cfg.BOT_ACTIVE:
        cfg.BOT_ACTIVE = False
        message_text = "Bot was paused"
    else:
        cfg.BOT_ACTIVE = True
        message_text = "Bot was resumed"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("secrets_reload"))
async def secrets_reload_handler(message: types.Message):
    message_text = "Reloaded"
    cfg.logger.info("Reloading secrets")
    error = await cfg.load_secrets_async()
    if error:
        cfg.logger.error(error)
        message_text = error
    else:
        no_secrets = cfg.apply_secrets(get_db=False)
        if no_secrets:
            cfg.logger.error(f"No secrets found: {no_secrets}")
            message_text = f"No secrets found:\n{str(no_secrets)}"
        else:
            cfg.logger.info("Secrets were reloaded")
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("users"))
async def users_handler(message: types.Message, bot: Bot):
    users_channels = await crud_chats.get_users_chats()
    message_text = f"Users ({len(cfg.TELEGRAM_USERS)}):"

    for user_id, user_channels in users_channels.items():
        user_name = cfg.TELEGRAM_USERS[user_id]["name"]
        channels_string = f" ({str(len(user_channels))})" if user_channels else ""
        message_text += f"\n● {user_name}{channels_string}"
        if user_channels:
            message_text += ". Channels:\n○ ["
            for channel_id in user_channels:
                channel_info = await bot.get_chat(channel_id)
                message_text += f"{channel_info.title}, "
            message_text = message_text.rstrip(", ")
            message_text += "]"

    main_keyboard = get_keyboard_users_actions()
    main_keyboard.adjust(3)
    abort_keyboard = get_keyboard_abort("usrs", "End")
    main_keyboard.attach(abort_keyboard)
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text, reply_markup=main_keyboard.as_markup())


@router.callback_query(CallbackUsersAction.filter(F.action == "Invite"))
async def user_invite_handler(callback: types.CallbackQuery, bot: Bot):
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)

    bot_name = (await bot.me()).username
    bot_join_link = f"https://t.me/{bot_name}?start={cfg.TELEGRAM_INVITE_CODE}"

    with suppress(TelegramBadRequest):
        await callback.message.answer(
            text=f"Use this link for join bot:\n{bot_join_link}",
            link_preview_options=types.LinkPreviewOptions(is_disabled=True),
        )


@router.callback_query(CallbackUsersAction.filter(F.action == "Rename"))
async def user_name_choose_handler(callback: types.CallbackQuery):
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)

    main_keyboard = get_keyboard_users(cfg.TELEGRAM_USERS, "usrsn")
    main_keyboard.adjust(2)
    abort_keyboard = get_keyboard_abort("usrn")
    main_keyboard.attach(abort_keyboard)
    with suppress(TelegramBadRequest):
        await callback.message.answer(
            text="Choose user to remane:",
            reply_markup=main_keyboard.as_markup(),
        )


@router.callback_query(CallbackChooseUser.filter(F.action == "usrsn"))
async def user_name_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseUser, state: FSMContext
):
    user_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    user_id = callback_data.user_id
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"'{user_name}' choosen", reply_markup=None
        )

    abort_keyboard = get_keyboard_abort("usrn")
    with suppress(TelegramBadRequest):
        sended_message = await callback.message.answer(
            text="Enter new user name:",
            reply_markup=abort_keyboard.as_markup(),
        )

        await state.set_data(
            {"outgoing_form_message_id": sended_message.message_id, "user_id": user_id}
        )
        await state.set_state(FromUserRename.name)


@router.message(FromUserRename.name)
async def user_name_form(message: types.Message, state: FSMContext, bot: Bot) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]
    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )
    user_id = copy(state_data["user_id"])
    await state.clear()

    new_name = message.text.strip()
    cfg.TELEGRAM_USERS[user_id]["name"] = new_name
    await crud_users.update_user(user_id, {"name": new_name})

    with suppress(TelegramBadRequest):
        await message.answer(text="User was renamed")


@router.callback_query(CallbackUsersAction.filter(F.action == "Remove"))
async def user_remove_choose_handler(callback: types.CallbackQuery):
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)

    main_keyboard = get_keyboard_users(cfg.TELEGRAM_USERS, "usrsr")
    main_keyboard.adjust(2)
    abort_keyboard = get_keyboard_abort("usrr")
    main_keyboard.attach(abort_keyboard)
    with suppress(TelegramBadRequest):
        await callback.message.answer(
            text="Choose user to remove:",
            reply_markup=main_keyboard.as_markup(),
        )


@router.callback_query(CallbackChooseUser.filter(F.action == "usrsr"))
async def user_remove_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseUser, bot: Bot
):
    user_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    user_id = callback_data.user_id

    message_text = f"User {user_name} removed"
    if user_id == cfg.TELEGRAM_BOT_OWNER_ID:
        message_text = "Can't remove owner"
    else:
        del cfg.TELEGRAM_USERS[user_id]
        await crud_users.remove_user(user_id)
        user_chats = await crud_chats.get_user_chats(user_id)
        await crud_chats.remove_chats(user_chats)

        subscriptions = await crud_subs.remove_unsubscribed_streamers()
        for subscription_id in subscriptions:
            await twitch.unsubscribe_event(subscription_id)

        for chat_id in user_chats:
            if chat_id != user_id:
                await bot.leave_chat(chat_id)

        with suppress(TelegramBadRequest):
            await bot.send_message(
                chat_id=user_id,
                text=(
                    "You, your channels and twitch notification subscriptions"
                    " were removed from bot by administator"
                ),
            )

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text=message_text, reply_markup=None)


@router.message(Command("limites"))
async def limites_handler(message: types.Message):
    limit_default_keyboard = get_keyboard_limit_default("Default value")
    main_keyboard = get_keyboard_users(cfg.TELEGRAM_USERS, "usrsl")
    main_keyboard.adjust(2)
    abort_keyboard = get_keyboard_abort("usrsl", "End")
    limit_default_keyboard.attach(main_keyboard)
    limit_default_keyboard.attach(abort_keyboard)

    message_text = (
        f"Current default limit: {cfg.TELEGRAM_LIMIT_DEFAULT}"
        "\nChange default or user's limit:"
    )
    with suppress(TelegramBadRequest):
        await message.answer(
            text=message_text,
            reply_markup=limit_default_keyboard.as_markup(),
        )


@router.callback_query(CallbackLimitDefault.filter())
async def limit_default_handler(callback: types.CallbackQuery, state: FSMContext):
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"Current default limit: {cfg.TELEGRAM_LIMIT_DEFAULT}",
            reply_markup=None,
        )

    abort_keyboard = get_keyboard_abort("usrsld")
    with suppress(TelegramBadRequest):
        sended_message = await callback.message.answer(
            text="Enter new default limit value:",
            reply_markup=abort_keyboard.as_markup(),
        )

        await state.set_data(
            {
                "outgoing_form_message_id": sended_message.message_id,
            }
        )
        await state.set_state(FormLimitDefault.value)


@router.message(FormLimitDefault.value)
async def limit_default_form(
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

    message_text = "Default limit was changed"
    try:
        value = int(message.text.rstrip())
        if value <= 0:
            message_text = "Value can't be 0 or lower"
        elif value > 10000:
            message_text = "Value can't more than cost limit (10000)"
        else:
            update_result = await cfg.update_limit_default(value)
            if update_result:
                message_text = f"Setting new default limit error:\n{update_result}"
    except Exception:
        message_text = "Value is not a number"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.callback_query(CallbackChooseUser.filter(F.action == "usrsl"))
async def user_limit_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseUser, state: FSMContext
):
    user_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    user_id = callback_data.user_id

    subs_count, subs_count_unique = await crud_subs.get_user_subscription_count(user_id)

    message_text = (
        f"Current default limit: {cfg.TELEGRAM_LIMIT_DEFAULT}\n"
        f"\nUser {user_name}:"
        f"\n● limit: {cfg.TELEGRAM_USERS[user_id]['limit']}"
        f"\n● subscriptions count: {subs_count}"
        f"\n● unique subscriptions count: {subs_count_unique}"
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text=message_text, reply_markup=None)

    if user_id == cfg.TELEGRAM_BOT_OWNER_ID:
        return

    main_keyboard = get_keyboard_user_limit(user_id)
    main_keyboard.adjust(2)
    abort_keyboard = get_keyboard_abort("usrl")
    main_keyboard.attach(abort_keyboard)
    with suppress(TelegramBadRequest):
        sended_message = await callback.message.answer(
            text="Enter new limit value:",
            reply_markup=main_keyboard.as_markup(),
        )

        await state.set_data(
            {
                "outgoing_form_message_id": sended_message.message_id,
                "user_id": user_id,
            }
        )
        await state.set_state(FormUserLimit.value)


@router.callback_query(CallbackUserLimit.filter())
async def user_limit_action_handler(
    callback: types.CallbackQuery, callback_data: CallbackUserLimit, state: FSMContext
):
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)
    user_id = callback_data.user_id
    await state.clear()

    limit_action = callback_data.action
    new_limit = None
    if limit_action == "Default":
        new_limit = cfg.TELEGRAM_LIMIT_DEFAULT

    cfg.TELEGRAM_USERS[user_id]["limit"] = new_limit
    await crud_users.update_user(user_id, {"limit": new_limit})

    with suppress(TelegramBadRequest):
        await callback.answer(text="Limit was changed")


@router.message(FormUserLimit.value)
async def user_limit_form(message: types.Message, state: FSMContext, bot: Bot) -> None:
    state_data = await state.get_data()
    outgoing_form_message_id = state_data["outgoing_form_message_id"]
    with suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=outgoing_form_message_id,
            reply_markup=None,
        )
    user_id = copy(state_data["user_id"])
    await state.clear()

    message_text = "Limit was changed"
    try:
        new_limit_int = int(message.text.rstrip())
        if new_limit_int <= 0:
            message_text = "Value can't be 0 or lower"
        elif new_limit_int > 10000:
            message_text = "Value can't more than cost limit (10000)"
        else:
            cfg.TELEGRAM_USERS[user_id]["limit"] = new_limit_int
            await crud_users.update_user(user_id, {"limit": new_limit_int})
    except Exception:
        message_text = "Value is not a number"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("streamers"))
async def streamers_handler(message: types.Message, bot: Bot):
    streamers = await crud_streamers.get_all_streamers()
    if not streamers:
        with suppress(TelegramBadRequest):
            await message.answer(text="No streamers")
    else:
        with suppress(TelegramBadRequest):
            sended_message = await message.answer(
                text="Updating streamers names from twitch"
            )

            streamers_with_names = await twitch.get_streamers_names(
                list(streamers.keys())
            )
            for streamer_id, streamer_name in streamers.items():
                twitch_name = streamers_with_names.get(streamer_id, "")
                if streamer_name in ("-", None) or (
                    twitch_name != "" and streamer_name != twitch_name
                ):
                    if not twitch_name:
                        streamer_with_name = await twitch.get_streamers_names(
                            [streamer_id]
                        )
                        twitch_name = streamer_with_name[streamer_id]
                    await crud_streamers.update_streamer_name(streamer_id, twitch_name)
                    streamers[streamer_id] = twitch_name

            message_text = f"Streamers ({len(streamers)}):"
            for streamer_name in sorted(
                list(streamers.values()), key=lambda name: name.lower()
            ):
                message_text += f"\n● {streamer_name}"

            with suppress(TelegramBadRequest):
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=sended_message.message_id,
                    text=message_text,
                )


@router.message(Command("costs"))
async def costs_handler(message: types.Message):
    costs_info = await twitch.get_costs()
    message_text = "Error getting costs info("
    if costs_info:
        message_text = ""
        for cost, value in costs_info.items():
            message_text += f"\n● {cost}\n○ {value}"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("dump"))
async def dump_handler(message: types.Message):
    main_keyboard = get_keyboard_dump()
    main_keyboard.adjust(2)
    abort_keyboard = get_keyboard_abort("dumpc")
    main_keyboard.attach(abort_keyboard)
    with suppress(TelegramBadRequest):
        await message.answer(
            text="Choose dump action:",
            reply_markup=main_keyboard.as_markup(),
        )


@router.callback_query(CallbackDump.filter(F.action == "Create"))
async def dump_create_handler(callback: types.CallbackQuery):
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text="Created dump:", reply_markup=None)

    dump = await crud_admin.create_dump()
    jsoned_payload = json.dumps(
        dump, ensure_ascii=False, indent=4, separators=(",", ": ")
    )
    current_datetime = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    file = types.BufferedInputFile(
        jsoned_payload.encode(), f"tntb_{cfg.ENV}_{current_datetime}.json"
    )

    with suppress(TelegramBadRequest):
        await callback.message.answer_document(document=file)


@router.callback_query(CallbackDump.filter(F.action == "Restore"))
async def dump_restore_handler(callback: types.CallbackQuery, state: FSMContext):
    abort_keyboard = get_keyboard_abort("dumpr")
    with suppress(TelegramBadRequest):
        sended_message = await callback.message.edit_text(
            text="Send json-file for restoring dump:",
            reply_markup=abort_keyboard.as_markup(),
        )
        await state.set_data({"outgoing_form_message_id": sended_message.message_id})
        await state.set_state(FormDump.dump)


@router.message(FormDump.dump)
async def dump_restore_form(
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

    message_text = "Dump was restored"
    input_file = message.document
    if not input_file:
        message_text = "No file was sended"
    else:
        file = await bot.download(input_file)
        json_data = None
        try:
            json_data = json.load(file)
        except Exception:
            message_text = "File is not json"
        if json_data:
            try:
                await crud_admin.restore_dump(json_data)
            except Exception:
                message_text = "Incorrect json data"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("broadcast_message"))
async def broadcast_message_handler(message: types.Message, state: FSMContext):
    abort_keyboard = get_keyboard_abort("bmsg")
    with suppress(TelegramBadRequest):
        sended_message = await message.answer(
            text="Send broadcast message to all users:",
            reply_markup=abort_keyboard.as_markup(),
        )

        await state.set_data({"outgoing_form_message_id": sended_message.message_id})
        await state.set_state(FormBroadcastMessage.message)


@router.message(FormBroadcastMessage.message)
async def broadcast_message_form(
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

    message_text = message.text or message.caption or ""
    message_entities = message.entities or message.caption_entities or None
    picture_id = None
    if message.photo:
        file_size = 0
        for photo in message.photo:
            if photo.file_size > file_size:
                picture_id = photo.file_id

    admin_message = "Message was sended"

    if not (message_text or picture_id):
        admin_message = "Can't send empty message"
    else:
        for user_id in cfg.TELEGRAM_USERS:
            if user_id != cfg.TELEGRAM_BOT_OWNER_ID:
                if picture_id:
                    with suppress(TelegramBadRequest):
                        await bot.send_photo(
                            chat_id=user_id,
                            photo=picture_id,
                            caption=message_text,
                            caption_entities=message_entities,
                        )
                else:
                    with suppress(TelegramBadRequest):
                        await bot.send_message(
                            chat_id=user_id,
                            text=message_text,
                            entities=message_entities,
                            link_preview_options=types.LinkPreviewOptions(
                                is_disabled=True
                            ),
                        )

    with suppress(TelegramBadRequest):
        await message.answer(text=admin_message)
