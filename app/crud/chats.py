from db.common import async_session
from db.models import Chats, Subscriptions
from sqlalchemy import delete, insert, select


async def chat_exists(chat_id: int) -> bool:
    async with async_session() as session, session.begin():
        db_chat = await session.scalar(select(Chats).where(Chats.id == chat_id))
        if db_chat:
            return True
        return False


async def get_chat_owner(chat_id: int) -> int | None:
    async with async_session() as session, session.begin():
        db_chat = await session.scalar(select(Chats).where(Chats.id == chat_id))
        if not db_chat:
            return None
        return db_chat.user_id


async def add_chat(chat_id: int, user_id: int) -> bool:
    async with async_session() as session, session.begin():
        db_chat = await session.scalar(select(Chats).where(Chats.id == chat_id))
        if db_chat:
            return False

        await session.execute(insert(Chats).values({"id": chat_id, "user_id": user_id}))
        return True


async def remove_chats(chat_ids: list[int]) -> None:
    async with async_session() as session, session.begin():
        await session.execute(
            delete(Subscriptions).where(Subscriptions.chat_id.in_(chat_ids))
        )
        await session.execute(delete(Chats).where(Chats.id.in_(chat_ids)))


async def get_user_chats(user_id: int) -> list[int]:
    async with async_session() as session, session.begin():
        db_chats = await session.scalars(select(Chats).where(Chats.user_id == user_id))
        return [chat.id for chat in db_chats]


async def get_users_chats() -> dict[int, list[int]]:
    async with async_session() as session, session.begin():
        db_chats = await session.scalars(select(Chats))

        result = {}
        for chat in db_chats:
            if chat.user_id not in result:
                result[chat.user_id] = []
            if chat.id != chat.user_id:
                result[chat.user_id].append(chat.id)
        return result
