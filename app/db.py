from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False, future=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(_get_engine(), expire_on_commit=False, class_=AsyncSession)
    return _session_factory


@asynccontextmanager
async def session_scope():
    """Provide a transactional scope around a series of operations."""

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create database schema if it does not exist."""

    engine = _get_engine()
    async with engine.begin() as conn:
        from app import models  # ensure models are imported

        await conn.run_sync(models.Base.metadata.create_all)


__all__ = ["Base", "session_scope", "get_session_factory", "init_db"]
