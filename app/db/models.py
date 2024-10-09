from sqlalchemy import MetaData
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.types import BIGINT, Text

SCHEMA = "tntb"
Base = declarative_base(metadata=MetaData(schema=SCHEMA))


class Chats(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    owner_id: Mapped[int] = mapped_column(BIGINT, nullable=False)


class Streamers(Base):
    __tablename__ = "streamers"

    id: Mapped[str] = mapped_column(primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(nullable=False)
    subscription_id: Mapped[str] = mapped_column(nullable=False)
    last_message: Mapped[str]


class Subscriptions(Base):
    __tablename__ = "subscriptions"

    chat_id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    streamer_id: Mapped[str] = mapped_column(primary_key=True)
    message_template: Mapped[str] = mapped_column(Text)
