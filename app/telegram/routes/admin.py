from contextlib import suppress
from copy import copy

from aiogram import Bot, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.common.config import cfg
from app.crud import admin as crud_admin
from app.crud import chats as crud_chats
from app.crud import subscriptions as crud_subs
from app.telegram.commands import COMMANDS_ADMIN
from app.telegram.utils.callbacks import (
    CallbackChooseUserRemove,
    CallbackUsersAction,
    get_choosed_callback_text,
)
from app.telegram.utils.forms import FormUserAdd
from app.telegram.utils.keyboards import (
    get_keyboard_abort,
    get_keyboard_users,
    get_keyboard_users_actions,
)
from app.twitch import functions as twitch

router = Router()


@router.message(Command("admin"))
async def admin_commands_handler(message: types.Message):
    message_text = "Available admin commands:"
    for command, description in COMMANDS_ADMIN.items():
        message_text += f"\n● {description}\n○ {command}"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.message(Command("streamers"))
async def streamers_handler(message: types.Message):
    streamers = await crud_admin.get_all_streamers()
    if not streamers:
        message_text = "No streamers"
    else:
        streamers_with_names = await twitch.get_streamers_names(streamers)
        message_text = f"Streamers ({len(streamers_with_names)}):"
        for streamer_name in sorted(
            list(streamers_with_names.values()), key=lambda name: name.lower()
        ):
            message_text += f"\n● {streamer_name}"

    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


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
    cfg.logger.info("Reloading secrets")
    error = await cfg.load_secrets_async()
    if error:
        cfg.logger.error(error)
        with suppress(TelegramBadRequest):
            await message.answer(text=error)
            return

    no_secrets = cfg.apply_secrets(get_db=False)
    if no_secrets:
        cfg.logger.error(f"No secrets found: {no_secrets}")
        with suppress(TelegramBadRequest):
            await message.answer(text=f"No secrets found:\n{str(no_secrets)}")
            return
    cfg.logger.info("Secrets were reloaded")
    with suppress(TelegramBadRequest):
        await message.answer(text="Reloaded")


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


@router.message(Command("users"))
async def users_handler(message: types.Message, bot: Bot):
    allowed_users = copy(cfg.TELEGRAM_ALLOWED)
    users_channels = await crud_admin.get_users_chats()
    message_text = f"Users ({len(allowed_users)}):"
    for user_id, user_channels in users_channels.items():
        user_info = await bot.get_chat(user_id)
        message_text += f"\n● {user_info.username} ({len(user_channels)+1})"
        allowed_users.remove(user_info.username.lower())
        if user_channels:
            message_text += ". Channels:\n○ ["
            for channel_id in user_channels:
                channel_info = await bot.get_chat(channel_id)
                message_text += f"{channel_info.title}, "
            message_text = message_text.rstrip(", ")
            message_text += "]"

    for user_name in allowed_users:
        message_text += f"\n● {user_name}"

    with suppress(TelegramBadRequest):
        main_keyboard = get_keyboard_users_actions()
        main_keyboard.adjust(2)
        abort_keyboard = get_keyboard_abort("usrs", "End")
        main_keyboard.attach(abort_keyboard)
        await message.answer(text=message_text, reply_markup=main_keyboard.as_markup())


@router.callback_query(CallbackUsersAction.filter(F.action == "Add"))
async def user_add_handler(callback: types.CallbackQuery, state: FSMContext):
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)

        abort_keyboard = get_keyboard_abort("usra")
        sended_message = await callback.message.answer(
            text="Enter telegram user name to add:",
            reply_markup=abort_keyboard.as_markup(),
        )

        await state.set_data(
            {
                "outgoing_form_message_id": sended_message.message_id,
            }
        )
        await state.set_state(FormUserAdd.user_name)


@router.message(FormUserAdd.user_name)
async def user_add_name_form(
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

    user_name = message.text.rstrip().lower()
    if user_name in cfg.TELEGRAM_ALLOWED:
        with suppress(TelegramBadRequest):
            await message.answer(text="User exists")
            return

    await state.clear()

    update_result = await cfg.update_telegram_allowed(user_name.lower(), "add")
    with suppress(TelegramBadRequest):
        message_text = "User added"
        if update_result:
            message_text = f"Adding error:\n{update_result}"
        await message.answer(text=message_text)


@router.callback_query(CallbackUsersAction.filter(F.action == "Remove"))
async def user_remove_choose_handler(callback: types.CallbackQuery, bot: Bot):
    with suppress(TelegramBadRequest):
        await callback.message.edit_reply_markup(reply_markup=None)

        allowed_users = copy(cfg.TELEGRAM_ALLOWED)
        users_db = await crud_admin.get_users()
        users = {}
        for user_id in users_db:
            user_info = await bot.get_chat(user_id)
            allowed_users.remove(user_info.username.lower())
            users[user_info.username] = user_id
        for user_name in allowed_users:
            users[user_name] = None

        main_keyboard = get_keyboard_users(users)
        main_keyboard.adjust(2)
        abort_keyboard = get_keyboard_abort("usrr")
        main_keyboard.attach(abort_keyboard)
        await callback.message.answer(
            text="Choose user to remove:",
            reply_markup=main_keyboard.as_markup(),
        )


@router.callback_query(CallbackChooseUserRemove.filter())
async def user_remove_handler(
    callback: types.CallbackQuery, callback_data: CallbackChooseUserRemove, bot: Bot
):
    user_name = get_choosed_callback_text(
        callback.message.reply_markup.inline_keyboard, callback.data
    )
    user_id = callback_data.user_id

    message_text = "User removed"
    if user_id == cfg.BOT_OWNER_ID:
        message_text = "Can't remove owner"
    elif not user_id:
        message_text = "User(0) removed"
        update_result = await cfg.update_telegram_allowed(user_name.lower(), "remove")
        if update_result:
            message_text = f"Removing user(0) error:\n{update_result}"
    else:
        update_result = await cfg.update_telegram_allowed(user_name.lower(), "remove")
        if update_result:
            message_text = f"Removing user error:\n{update_result}"
        else:
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
