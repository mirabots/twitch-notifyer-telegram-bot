from db.models import Chats, Streamers
from db.utils import async_session
from sqlalchemy import select


async def get_all_chats() -> dict[int, list[int]]:
    async with async_session() as session:
        async with session.begin():
            db_chats = await session.scalars(select(Chats))

            result = {}
            for chat in db_chats:
                if chat.owner_id not in result:
                    result[chat.owner_id] = []
                if chat.id != chat.owner_id:
                    result[chat.owner_id].append(chat.id)

            return result


async def get_all_streamers() -> list[str]:
    async with async_session() as session:
        async with session.begin():
            db_streamers = await session.scalars(select(Streamers))
            return [streamer.id for streamer in db_streamers]
