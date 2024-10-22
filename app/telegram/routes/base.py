from contextlib import suppress

from aiogram import Bot, Router, types
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import (
    ADMINISTRATOR,
    IS_NOT_MEMBER,
    ChatMemberUpdatedFilter,
    Command,
)
from aiogram.fsm.context import FSMContext
from aiogram.utils import formatting

from app.common.config import cfg
from app.crud import chats as crud_chats
from app.crud import subscriptions as crud_subs
from app.telegram.utils.callbacks import CallbackAbort
from app.twitch import functions as twitch

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.username

    cfg.logger.info(f"Start user: {user_id=} {user_name=} {chat_id=}")

    chat_added = await crud_chats.add_chat(chat_id, user_id)
    message_text = (
        "Bot started, this chat was added\nUse /info for some information"
        if chat_added
        else "Bot already started"
    )
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> ADMINISTRATOR))
async def start_channel_handler(event: types.ChatMemberUpdated, bot: Bot):
    if not cfg.BOT_ACTIVE:
        return
    if event.chat.type in ("group", "supergroup", "private"):
        return

    chat_id = event.chat.id
    chat_title = event.chat.title
    user_id = event.from_user.id
    user_name = event.from_user.username
    user_channel_status = (await bot.get_chat_member(chat_id, user_id)).status

    if (
        not (await crud_chats.user_exists(user_id))
        or user_name not in cfg.TELEGRAM_ALLOWED
        or user_channel_status != ChatMemberStatus.CREATOR
    ):
        return

    cfg.logger.info(f"Start channel: {user_id=} {user_name=} {chat_id=} {chat_title=}")

    chat_added = await crud_chats.add_chat(chat_id, user_id)
    message_text = f"Notification\nChannel '{chat_title}' added"
    if not chat_added:
        message_text = f"Notification\nChannel '{chat_title}' exists"
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id=user_id, text=message_text)


@router.message(Command("stop"))
async def stop_handler(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.username

    cfg.logger.info(f"Stop user: {user_id=} {user_name=}")

    user_chats = await crud_chats.get_user_chats(user_id)
    if not user_chats:
        message_text = "Bot already stopped"
        await message.answer(text=message_text)
        return

    await crud_chats.remove_chats(user_chats)
    subscriptions = await crud_subs.remove_unsubscribed_streamers()
    for subscription_id in subscriptions:
        await twitch.unsubscribe_event(subscription_id)

    for chat_id in user_chats:
        if chat_id != user_id:
            await bot.leave_chat(chat_id)

    message_text = (
        "Bot stopped, owned chats/channels were leaved, streamers unsubscribed"
    )
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)


@router.my_chat_member(ChatMemberUpdatedFilter(ADMINISTRATOR >> IS_NOT_MEMBER))
async def stop_channel_handler(event: types.ChatMemberUpdated, bot: Bot):
    if not cfg.BOT_ACTIVE:
        return
    if event.chat.type in ("group", "supergroup", "private"):
        return

    chat_id = event.chat.id
    chat_title = event.chat.title
    user_id = event.from_user.id
    user_name = event.from_user.username
    user_channel_status = (await bot.get_chat_member(chat_id, user_id)).status

    if not (await crud_chats.chat_exists(chat_id)):
        return
    if (
        not (await crud_chats.user_exists(user_id))
        or user_name not in cfg.TELEGRAM_ALLOWED
        or user_channel_status != ChatMemberStatus.CREATOR
    ):
        chat_owner = await crud_chats.get_chat_owner(chat_id)
        message_text = f"Notification\nBot leaved from channel '{chat_title}' by '{user_name}'\n(but not deleted from bot)"
        with suppress(TelegramBadRequest):
            await bot.send_message(chat_id=chat_owner, text=message_text)
        return

    cfg.logger.info(f"Stop channel: {user_id=} {user_name=} {chat_id=} {chat_title=}")

    await crud_chats.remove_chats([chat_id])
    subscriptions = await crud_subs.remove_unsubscribed_streamers()
    for subscription_id in subscriptions:
        await twitch.unsubscribe_event(subscription_id)

    message_text = f"Notification\nBot leaved from channel '{chat_title}'"
    with suppress(TelegramBadRequest):
        await bot.send_message(chat_id=user_id, text=message_text)


@router.message(Command("info"))
async def info_handler(message: types.Message, bot: Bot):
    bot_name = (await bot.me()).username
    bot_channel_link = (
        f"tg://resolve?domain={bot_name}&startchannel&admin=post_messages"
    )

    info = formatting.as_marked_section(
        formatting.Bold("Here is simple instruction how to use bot:"),
        formatting.Text(
            "If you want to recieve notifications in channels, first of all, you need to add bot to the channel ",
            formatting.TextLink("using this link", url=bot_channel_link),
            " (with only admin ",
            formatting.Italic("POST POSTS"),
            " permission).",
        ),
        "Secondly, you need to add streamer subscription to chat/channel, using /subscribe command. That's all.",
        "Other commands (managing chats and streamers, changing notification text) can be found in command-menu near text-input.",
        marker="● ",
    )
    with suppress(TelegramBadRequest):
        await message.answer(**info.as_kwargs())


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
    if action == "pctr":
        action_text = "Changing picture mode"
    if action == "usrs":
        with suppress(TelegramBadRequest):
            await callback.message.edit_reply_markup(reply_markup=None)
            return
    if action == "usra":
        action_text = "Adding user"
    if action == "usrr":
        action_text = "Removing user"

    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text=f"{action_text} operation was aborted".lstrip().capitalize(),
            reply_markup=None,
        )
