import logging
import sys
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

from app.common.config import cfg

_engine = create_async_engine(cfg.DB_CONNECTION_STRING)
async_session = async_sessionmaker(_engine, expire_on_commit=False)


async def check_db(logger: logging.Logger) -> None:
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1;"))
            logger.info("Successfully connected to database")
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        sys.exit(1)


def get_model_dict(model: Any) -> dict[str, Any]:
    return {
        column.name: getattr(model, column.name) for column in model.__table__.columns
    }
