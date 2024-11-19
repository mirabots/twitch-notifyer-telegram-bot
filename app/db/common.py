import sys
from typing import Any

from common.config import cfg
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

_engine = create_async_engine(cfg.DB_CONNECTION_STRING)
async_session = async_sessionmaker(_engine, expire_on_commit=False)


async def check_db() -> None:
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1;"))
            cfg.logger.info("Successfully connected to database")
    except Exception as e:
        cfg.logger.error(f"Failed to connect to database: {str(e)}")
        sys.exit(1)


def get_model_dict(model: Any) -> dict[str, Any]:
    return {
        column.name: getattr(model, column.name) for column in model.__table__.columns
    }
