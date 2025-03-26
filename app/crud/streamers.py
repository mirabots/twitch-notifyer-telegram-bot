from datetime import datetime, timedelta, timezone

from db.common import async_session
from db.models import Streamers
from sqlalchemy import delete, insert, select, update


async def get_all_streamers() -> dict[str, str]:
    async with async_session() as session, session.begin():
        db_streamers = await session.scalars(select(Streamers))
        return {streamer.id: streamer.name for streamer in db_streamers}


async def check_streamer(streamer_id: str) -> str | None:
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
                    "last_message_timestamp": datetime.fromisoformat(
                        "1970-01-01 00:00+00:00"
                    ),
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


async def check_passed_delay_event_message(streamer_id: str, delay: int) -> bool:
    async with async_session() as session, session.begin():
        db_streamer = await session.scalar(
            select(Streamers).where(Streamers.id == streamer_id)
        )
        last_timestamp = db_streamer.last_message_timestamp
        current_timestamp = datetime.now(timezone.utc)

        await session.execute(
            update(Streamers)
            .where(Streamers.id == streamer_id)
            .values(last_message_timestamp=current_timestamp)
        )

        if current_timestamp - last_timestamp > timedelta(seconds=delay):
            # await session.execute(
            #     update(Streamers)
            #     .where(Streamers.id == streamer_id)
            #     .values(last_message_timestamp=current_timestamp)
            # )

            return True
        return False


async def remove_streamer(streamer_id: str) -> None:
    async with async_session() as session, session.begin():
        await session.execute(delete(Streamers).where(Streamers.id == streamer_id))
