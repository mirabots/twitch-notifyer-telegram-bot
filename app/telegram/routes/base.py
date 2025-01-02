from contextlib import suppress
from enum import Enum

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
from common.config import cfg
from crud import chats as crud_chats
from crud import subscriptions as crud_subs
from crud import users as crud_users
from telegram.utils.callbacks import CallbackAbort
from twitch import functions as twitch

router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.full_name + f" ({message.from_user.username})"

    message_text = "You are not allowed to use this bot"
    admin_message_text = ""
    if user_id in cfg.TELEGRAM_USERS:
        message_text = "Bot already started"
    else:
        join_code = message.text.removeprefix("/start").strip()
        if await cfg.check_invite_code(join_code):
            message_text = "Bot started, this chat was added\nUse /info for information"
            admin_message_text = f"User {user_name} joined"
            await crud_users.add_user(user_id, cfg.TELEGRAM_LIMIT_DEFAULT, user_name)
            await crud_chats.add_chat(chat_id, user_id)
            cfg.TELEGRAM_USERS[user_id] = {
                "limit": cfg.TELEGRAM_LIMIT_DEFAULT,
                "name": user_name,
            }
    cfg.logger.info(f"Start user: {user_id=} {user_name=} {chat_id=} {message_text=}")
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)
        if admin_message_text:
            await bot.send_message(
                chat_id=cfg.TELEGRAM_BOT_OWNER_ID, text=admin_message_text
            )


@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> ADMINISTRATOR))
async def start_channel_handler(event: types.ChatMemberUpdated, bot: Bot):
    if not cfg.BOT_ACTIVE:
        return
    if event.chat.type in ("group", "supergroup", "private"):
        return

    chat_id = event.chat.id
    chat_title = event.chat.title
    user_id = event.from_user.id
    user_name = event.from_user.full_name + f" ({event.from_user.username})"
    user_channel_status = (await bot.get_chat_member(chat_id, user_id)).status

    if (
        user_id not in cfg.TELEGRAM_USERS
        or user_channel_status != ChatMemberStatus.CREATOR
    ):
        cfg.logger.info(
            f"Start channel (REJECTED): {user_id=} {user_name=} {chat_id=} {chat_title=}"
        )
        await bot.leave_chat(chat_id)
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
    user_name = message.from_user.full_name + f" ({message.from_user.username})"

    cfg.logger.info(f"Stop user: {user_id=} {user_name=}")

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

    message_text = (
        "Bot stopped, owned chats/channels were leaved, streamers unsubscribed"
    )
    with suppress(TelegramBadRequest):
        await message.answer(text=message_text)
        await bot.send_message(
            chat_id=cfg.TELEGRAM_BOT_OWNER_ID, text=f"User {user_name} leaved"
        )


@router.my_chat_member(ChatMemberUpdatedFilter(ADMINISTRATOR >> IS_NOT_MEMBER))
async def stop_channel_handler(event: types.ChatMemberUpdated, bot: Bot):
    if not cfg.BOT_ACTIVE:
        return
    if event.chat.type in ("group", "supergroup", "private"):
        return

    chat_id = event.chat.id
    chat_title = event.chat.title
    user_id = event.from_user.id
    user_name = event.from_user.full_name + f" ({event.from_user.username})"
    user_channel_status = (await bot.get_chat_member(chat_id, user_id)).status

    if not (await crud_chats.chat_exists(chat_id)):
        return
    if (
        user_name not in cfg.TELEGRAM_USERS
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
        formatting.Bold("How to use bot:"),
        formatting.Text(
            "If you want to recieve notifications in channels (groups are not supported),",
            " you need to add bot to the channel ",
            formatting.TextLink("using this link", url=bot_channel_link),
            " (with only admin ",
            formatting.Italic("POST POSTS"),
            " permission) (can be found in command /channels later)",
        ),
        "For subscriptions list and limites info use /subscriptions",
        "For subscribing notifications use /subscribe command and choose bot chat or your channel",
        "You can test (/notification_test) your notifications and customize them",
        "Change message description via /template",
        (
            "Change notification picture mod: /picture and choose prefered view: "
            "Stream start screenshot, Own picture or Disabled"
        ),
        "Other commands can be found in command menu near text-input",
        marker="● ",
    )
    with suppress(TelegramBadRequest):
        await message.answer(**info.as_kwargs())


@router.callback_query(CallbackAbort.filter())
async def abort_handler(
    callback: types.CallbackQuery, callback_data: CallbackAbort, state: FSMContext
):
    await state.clear()

    class ACTONS_TEXTS(Enum):
        DEFAULT = "Operation was aborted"
        CHNLR = "Removing channel operation was aborted"
        SUBS = "Getting subscriptions operation was aborted"
        SUB = "Subscribe operation was aborted"
        UNSUB = "Unsubscribe operation was aborted"
        TMPLT = "Changing template operation was aborted"
        PCTR = "Changing picture mode operation was aborted"
        NTFCTN = "Testing notification operation was aborted"

        USRS = ""
        USRN = "Renaming user operation was aborted"
        USRR = "Removing user operation was aborted"
        USRSL = f"Current default limit: {cfg.TELEGRAM_LIMIT_DEFAULT}"
        USRSLD = "Changing default limit operation was aborted"
        USRL = "Changing user's limit operation was aborted"
        DUMPC = "Creating dump operation was aborted"
        DUMPR = "Restoring dump operation was aborted"
        BMSG = "Broadcast messaging operation was aborted"

        @classmethod
        def _missing_(cls, _):
            return cls.DEFAULT

    action_text = ACTONS_TEXTS[callback_data.action.upper()]

    if action_text.name == "USRS":
        with suppress(TelegramBadRequest):
            await callback.message.edit_reply_markup(reply_markup=None)
    else:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(text=action_text.value, reply_markup=None)
