from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationTask, Referral, Transaction, User


class UserRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def get_or_create_user(self, chat_id: int, username: str | None = None) -> User:
        async with self._session_factory() as session:
            user = await self._get_by_chat_id(session, chat_id)
            if user is None:
                user = User(chat_id=chat_id, username=username)
                session.add(user)
                await session.commit()
                await session.refresh(user)
            else:
                if username and user.username != username:
                    user.username = username
                    await session.commit()
            return user

    async def _get_by_chat_id(self, session: AsyncSession, chat_id: int) -> User | None:
        result = await session.execute(select(User).where(User.chat_id == chat_id))
        return result.scalar_one_or_none()

    async def get_by_chat_id(self, chat_id: int) -> User | None:
        async with self._session_factory() as session:
            return await self._get_by_chat_id(session, chat_id)

    async def get_by_id(self, user_id: int) -> User | None:
        async with self._session_factory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

    async def update_balance(self, chat_id: int, amount: int, reason: str | None = None) -> User | None:
        async with self._session_factory() as session:
            user = await self._get_by_chat_id(session, chat_id)
            if not user:
                return None
            user.balance += amount
            user.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(user)
            return user

    async def set_admin(self, chat_id: int, is_admin: bool) -> User | None:
        async with self._session_factory() as session:
            user = await self._get_by_chat_id(session, chat_id)
            if not user:
                return None
            user.is_admin = is_admin
            await session.commit()
            await session.refresh(user)
            return user

    async def get_all_admins(self) -> List[User]:
        async with self._session_factory() as session:
            result = await session.execute(select(User).where(User.is_admin.is_(True)).order_by(User.created_at))
            return list(result.scalars().all())

    async def set_referrer(self, chat_id: int, referrer_id: int) -> None:
        async with self._session_factory() as session:
            user = await self._get_by_chat_id(session, chat_id)
            if user:
                user.referrer_id = referrer_id
                await session.commit()


class TransactionRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(
        self,
        *,
        user_id: int,
        amount: int,
        reason: str,
        payment_method: str | None = None,
        external_id: str | None = None,
    ) -> Transaction:
        async with self._session_factory() as session:
            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                reason=reason,
                payment_method=payment_method,
                external_id=external_id,
            )
            session.add(transaction)
            await session.commit()
            await session.refresh(transaction)
            return transaction

    async def get_by_external_id(self, external_id: str) -> Transaction | None:
        async with self._session_factory() as session:
            result = await session.execute(select(Transaction).where(Transaction.external_id == external_id))
            return result.scalar_one_or_none()


class GenerationTaskRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create_task(
        self,
        *,
        user_id: int,
        task_id: str,
        photo_url: str,
        collection_id: str | None = None,
    ) -> GenerationTask:
        async with self._session_factory() as session:
            task = GenerationTask(
                user_id=user_id,
                task_id=task_id,
                photo_url=photo_url,
                collection_id=collection_id,
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task

    async def update_status(
        self,
        task_id: str,
        *,
        status: str,
        result_url: str | None = None,
        error_message: str | None = None,
    ) -> GenerationTask | None:
        async with self._session_factory() as session:
            result = await session.execute(select(GenerationTask).where(GenerationTask.task_id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                return None
            task.status = status
            task.result_url = result_url
            task.error_message = error_message
            if status in {"completed", "failed"}:
                task.completed_at = datetime.utcnow()
            await session.commit()
            await session.refresh(task)
            return task


class ReferralRepository:
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(self, referrer_id: int, referee_id: int) -> Referral:
        async with self._session_factory() as session:
            referral = Referral(referrer_id=referrer_id, referee_id=referee_id)
            session.add(referral)
            await session.commit()
            await session.refresh(referral)
            return referral

    async def get_by_referee(self, referee_id: int) -> Referral | None:
        async with self._session_factory() as session:
            result = await session.execute(select(Referral).where(Referral.referee_id == referee_id))
            return result.scalar_one_or_none()

    async def get_by_referrer(self, referrer_id: int) -> List[Referral]:
        async with self._session_factory() as session:
            result = await session.execute(select(Referral).where(Referral.referrer_id == referrer_id))
            return list(result.scalars().all())

    async def mark_first_bonus_given(self, referral_id: int) -> None:
        async with self._session_factory() as session:
            result = await session.execute(select(Referral).where(Referral.id == referral_id))
            referral = result.scalar_one_or_none()
            if referral:
                referral.first_purchase_bonus_given = True
                await session.commit()

    async def update_earned(self, referral_id: int, tokens: int) -> None:
        async with self._session_factory() as session:
            result = await session.execute(select(Referral).where(Referral.id == referral_id))
            referral = result.scalar_one_or_none()
            if referral:
                referral.total_earned += tokens
                await session.commit()


__all__ = [
    "UserRepository",
    "TransactionRepository",
    "GenerationTaskRepository",
    "ReferralRepository",
]
