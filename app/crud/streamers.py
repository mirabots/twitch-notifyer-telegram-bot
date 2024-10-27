from sqlalchemy import delete, insert, select, update

from app.db.common import async_session
from app.db.models import Streamers


async def get_all_streamers() -> list[str]:
    async with async_session() as session, session.begin():
        db_streamers = await session.scalars(select(Streamers))
        return [streamer.id for streamer in db_streamers]


async def check_streamer(streamer_id: str) -> bool:
    async with async_session() as session, session.begin():
        db_streamer = await session.scalar(
            select(Streamers).where(Streamers.id == streamer_id)
        )
        if not db_streamer:
            return None
        return db_streamer.name


async def add_streamer(
    streamer_id: str, streamer_name: str, subscription_id: str
) -> bool:
    async with async_session() as session, session.begin():
        db_streamer = await session.scalar(
            select(Streamers).where(Streamers.id == streamer_id)
        )
        if db_streamer:
            return False

        await session.execute(
            insert(Streamers).values(
                {
                    "id": streamer_id,
                    "name": streamer_name,
                    "subscription_id": subscription_id,
                }
            )
        )
        return True


async def update_streamer_name(streamer_id: str, streamer_name: str) -> None:
    async with async_session() as session, session.begin():
        await session.execute(
            update(Streamers)
            .where(Streamers.id == streamer_id)
            .values(name=streamer_name)
        )


async def check_duplicate_event_message(streamer_id: str, message_id: str) -> bool:
    async with async_session() as session, session.begin():
        db_streamer = await session.scalar(
            select(Streamers).where(
                Streamers.id == streamer_id, Streamers.last_message == message_id
            )
        )
        if db_streamer:
            return True

        await session.execute(
            update(Streamers)
            .where(Streamers.id == streamer_id)
            .values(last_message=message_id)
        )
        return False


async def remove_streamer(streamer_id: str) -> None:
    async with async_session() as session, session.begin():
        await session.execute(delete(Streamers).where(Streamers.id == streamer_id))
