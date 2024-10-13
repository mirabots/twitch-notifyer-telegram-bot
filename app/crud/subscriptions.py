from sqlalchemy import delete, insert, join, select, update

from app.db.common import async_session
from app.db.models import Chats, Streamers, Subscriptions


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
            update(Subscriptions)
            .where(
                Subscriptions.streamer_id == streamer_id,
            )
            .values(name=streamer_name)
        )


async def subscribe_to_streamer(chat_id: int, streamer_id: str) -> bool:
    async with async_session() as session, session.begin():
        db_active_subscription = await session.scalar(
            select(Subscriptions).where(
                Subscriptions.chat_id == chat_id,
                Subscriptions.streamer_id == streamer_id,
            )
        )
        if db_active_subscription:
            return False

        await session.execute(
            insert(Subscriptions).values(
                {"chat_id": chat_id, "streamer_id": streamer_id}
            )
        )
        return True


async def unsubscribe_from_streamer(chat_id: int, streamer_id: str) -> None:
    async with async_session() as session, session.begin():
        await session.execute(
            delete(Subscriptions).where(
                Subscriptions.chat_id == chat_id,
                Subscriptions.streamer_id == streamer_id,
            )
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


async def get_subscribed_chats(streamer_id: str) -> list[dict[str, int | str]]:
    async with async_session() as session, session.begin():
        db_subscriptions = await session.scalars(
            select(Subscriptions).where(Subscriptions.streamer_id == streamer_id)
        )
        return [
            {"id": sub.chat_id, "template": sub.message_template}
            for sub in db_subscriptions
        ]


async def get_subscriptions(chat_id: int) -> list[str]:
    async with async_session() as session, session.begin():
        db_subscriptions = await session.scalars(
            select(Subscriptions).where(Subscriptions.chat_id == chat_id)
        )
        return [streamer.streamer_id for streamer in db_subscriptions]


async def remove_unsubscribed_streamers() -> list[str]:
    async with async_session() as session, session.begin():
        db_subscribed_streamers = (
            await session.execute(select(Subscriptions.streamer_id).distinct())
        ).fetchall()
        subscribed_streamer_ids = [
            streamer.streamer_id for streamer in db_subscribed_streamers
        ]

        db_unsubscribed_streamers = await session.scalars(
            delete(Streamers)
            .where(Streamers.id.notin_(subscribed_streamer_ids))
            .returning(Streamers)
        )
        return [streamer.subscription_id for streamer in db_unsubscribed_streamers]


async def change_template(chat_id: int, streamer_id: str, new_template: str) -> None:
    async with async_session() as session, session.begin():
        await session.execute(
            update(Subscriptions)
            .where(
                Subscriptions.chat_id == chat_id,
                Subscriptions.streamer_id == streamer_id,
            )
            .values(message_template=new_template)
        )


async def get_subscribed_users(streamer_id: str) -> list[int]:
    async with async_session() as session, session.begin():
        chats = await session.scalars(
            select(Chats)
            .select_from(join(Chats, Subscriptions, Chats.id == Subscriptions.chat_id))
            .where(Subscriptions.streamer_id == streamer_id)
        )
        return set([chat.user_id for chat in chats])


async def remove_streamer(streamer_id: str) -> None:
    async with async_session() as session, session.begin():
        await session.execute(delete(Streamers).where(Streamers.id == streamer_id))


async def remove_streamer_subscriptions(streamer_id: str) -> None:
    async with async_session() as session, session.begin():
        await session.execute(
            delete(Subscriptions).where(Subscriptions.streamer_id == streamer_id)
        )
