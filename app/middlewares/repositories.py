from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.repositories import GenerationTaskRepository, ReferralRepository, TransactionRepository, UserRepository


class RepositoryMiddleware(BaseMiddleware):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__()
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_repo = UserRepository(self.session_factory)
        transaction_repo = TransactionRepository(self.session_factory)
        referral_repo = ReferralRepository(self.session_factory)
        task_repo = GenerationTaskRepository(self.session_factory)

        data.setdefault("user_repo", user_repo)
        data.setdefault("transaction_repo", transaction_repo)
        data.setdefault("referral_repo", referral_repo)
        data.setdefault("task_repo", task_repo)

        return await handler(event, data)
