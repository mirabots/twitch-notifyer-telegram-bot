from typing import Any

from sqlalchemy import delete, insert, select

from app.db.common import async_session, get_model_dict
from app.db.models import Chats, Streamers, Subscriptions, Users


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


async def create_dump() -> dict[str, list[dict[str, Any]]]:
    dump = {}
    tables = (
        ("users", Users),
        ("chats", Chats),
        ("streamers", Streamers),
        ("subscriptions", Subscriptions),
    )
    async with async_session() as session, session.begin():
        for table_name, table_model in tables:
            rows = await session.scalars(select(table_model))
            dump[table_name] = [get_model_dict(row) for row in rows]
    return dump


async def restore_dump(dump: dict[str, list[dict[str, Any]]]) -> None:
    tables = {
        "users": Users,
        "chats": Chats,
        "streamers": Streamers,
        "subscriptions": Subscriptions,
    }
    async with async_session() as session, session.begin():
        for table, table_dump in dump.items():
            await session.execute(delete(tables[table]))
            if table_dump:
                await session.execute(insert(tables[table]).values(table_dump))
