from common.config import cfg
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

_engine = create_async_engine(cfg.DB_CONNECTION_STRING)
async_session = async_sessionmaker(_engine, expire_on_commit=False)


async def check_db() -> None:
    try:
        async with async_session() as session:
            select_version = text("SELECT version();")
            if "sqlite+aiosqlite:///" in cfg.DB_CONNECTION_STRING:
                select_version = text("SELECT sqlite_version();")
            answer = await session.execute(select_version)
            print(
                f"INFO:\t  Successfully connecting to database.\n\t  {answer.first()}",
                flush=True,
            )
    except Exception as e:
        print(f"ERROR:\t  Failed to connect to database:\n{str(e)}", flush=True)
        raise
