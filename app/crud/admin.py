from sqlalchemy import select

from app.db.common import async_session
from app.db.models import Chats, Streamers


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


async def get_all_streamers() -> list[str]:
    async with async_session() as session, session.begin():
        db_streamers = await session.scalars(select(Streamers))
        return [streamer.id for streamer in db_streamers]
