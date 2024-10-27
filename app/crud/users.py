from sqlalchemy import delete, insert, select, update

from app.db.common import async_session
from app.db.models import Users


async def get_users() -> dict[int, dict[str, int | str | None]]:
    async with async_session() as session, session.begin():
        users = await session.scalars(select(Users))
        return {user.id: {"limit": user.limit, "name": user.name} for user in users}


async def add_user(id: int, limit: int | None, name: str | None) -> None:
    async with async_session() as session, session.begin():
        await session.execute(
            insert(Users).values({"id": id, "limit": limit, "name": name})
        )


async def remove_user(id: int) -> None:
    async with async_session() as session, session.begin():
        await session.execute(delete(Users).where(Users.id == id))


async def update_user(id: int, data: dict[str, int | str | None]) -> None:
    async with async_session() as session, session.begin():
        await session.execute(update(Users).where(Users.id == id).values(data))
