import time
from contextlib import suppress

from aiogram import Bot, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import IS_ADMIN, IS_NOT_MEMBER, ChatMemberUpdatedFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils import formatting

from app.common.config import cfg
from app.common.utils import get_logger, levelDEBUG, levelINFO
from app.crud import chats as crud_chats
from app.crud import subscriptions as crud_subs
from app.telegram.utils.callbacks import CallbackAbort
from app.twitch import functions as twitch

router = Router()
logger = get_logger(levelDEBUG if cfg.ENV == "dev" else levelINFO)


@router.message(Command("start"))
async def start_handler(message: types.Message):
    chat_id = message.chat.id
    owner_id = message.from_user.id

    logger.info(
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

    logger.info(
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

    logger.info(f"Stop: {owner_id=} {message.from_user.username=} {time.asctime()}")

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

    logger.info(
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
