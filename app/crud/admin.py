from typing import Any

from db.common import async_session, get_model_dict
from db.models import Chats, Streamers, Subscriptions, Users
from sqlalchemy import delete, insert, select


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
