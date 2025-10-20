from __future__ import annotations

from collections.abc import Iterable

from ..db import session_scope
from ..repositories import UserRepository


class UserService:
    async def get_or_create(self, chat_id: int, username: str | None):
        async with session_scope() as session:
            repo = UserRepository(session)
            return await repo.get_or_create(chat_id, username)

    async def get(self, chat_id: int):
        async with session_scope() as session:
            repo = UserRepository(session)
            return await repo.get_by_chat_id(chat_id)

    async def get_by_id(self, user_id: int):
        async with session_scope() as session:
            repo = UserRepository(session)
            return await repo.get_by_id(user_id)

    async def list_all(self) -> Iterable:
        async with session_scope() as session:
            repo = UserRepository(session)
            return await repo.list_all()


__all__ = ["UserService"]
