from datetime import datetime

from sqlalchemy import MetaData
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.types import BIGINT, JSON, TIMESTAMP, Text

SCHEMA = "tntb"
Base = declarative_base(metadata=MetaData(schema=SCHEMA))


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    limit: Mapped[int] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(nullable=True)


class Chats(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    user_id: Mapped[int] = mapped_column(BIGINT, nullable=False)


class Streamers(Base):
    __tablename__ = "streamers"

    id: Mapped[str] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(nullable=False)
    subscription_id: Mapped[str] = mapped_column(nullable=False)
    last_message: Mapped[str] = mapped_column(nullable=True)
    last_message_timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class Subscriptions(Base):
    __tablename__ = "subscriptions"

    chat_id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    streamer_id: Mapped[str] = mapped_column(primary_key=True)
    message_template: Mapped[str] = mapped_column(Text, nullable=True)
    picture_mode: Mapped[str] = mapped_column(nullable=False)
    picture_id: Mapped[str] = mapped_column(nullable=True)
    restreams_links: Mapped[list[str]] = mapped_column(JSON, nullable=True)
