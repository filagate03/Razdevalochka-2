from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    pass


def create_engine() -> AsyncEngine:
    settings = get_settings()
    database_url = settings.database_url
    if database_url.startswith("sqlite:///") and "+aiosqlite" not in database_url:
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )
    return engine


engine: AsyncEngine = create_engine()
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope():
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


__all__ = ["Base", "SessionFactory", "engine", "session_scope", "init_models"]
