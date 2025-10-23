from __future__ import annotations

import logging

from ..db import session_scope
from ..models import ManualTopUpMethod, ManualTopUpStatus, TransactionType, User
from ..repositories import ManualTopUpRepository, TransactionRepository, UserRepository


logger = logging.getLogger(__name__)


class BillingService:
    async def get_or_create_user(self, chat_id: int, username: str | None) -> User:
        async with session_scope() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create(chat_id=chat_id, username=username)
            return user

    async def get_user(self, chat_id: int) -> User | None:
        async with session_scope() as session:
            user_repo = UserRepository(session)
            return await user_repo.get_by_chat_id(chat_id)

    async def add_transaction(self, user: User, amount: int, t_type: TransactionType, description: str | None) -> None:
        async with session_scope() as session:
            user_repo = UserRepository(session)
            transaction_repo = TransactionRepository(session)
            db_user = await user_repo.get_by_id(user.id)
            if not db_user:
                raise ValueError("User not found")
            await user_repo.adjust_balance(db_user, amount)
            await transaction_repo.add(user_id=db_user.id, amount=amount, type_=t_type, description=description)
            user.balance = db_user.balance

    async def create_manual_topup(
        self,
        user: User,
        method: ManualTopUpMethod,
        amount: int,
        comment: str | None = None,
    ):
        async with session_scope() as session:
            topup_repo = ManualTopUpRepository(session)
            return await topup_repo.create(user.id, method, amount, comment)

    async def list_user_history(self, user: User, limit: int = 50):
        async with session_scope() as session:
            transaction_repo = TransactionRepository(session)
            return await transaction_repo.list_by_user(user_id=user.id, limit=limit)

    async def list_user_topups(self, user: User):
        async with session_scope() as session:
            topup_repo = ManualTopUpRepository(session)
            return await topup_repo.list_by_user(user.id)

    async def approve_manual_topup(self, topup_id: int, amount: int | None = None) -> tuple[ManualTopUpStatus, int | None]:
        async with session_scope() as session:
            topup_repo = ManualTopUpRepository(session)
            user_repo = UserRepository(session)
            transaction_repo = TransactionRepository(session)
            topup = await topup_repo.get(topup_id)
            if not topup:
                return ManualTopUpStatus.REJECTED, None
            if topup.status != ManualTopUpStatus.PENDING:
                logger.warning(
                    "Attempt to approve manual topup with status %s (id=%s)",
                    topup.status,
                    topup_id,
                )
                return topup.status, None

            final_amount = amount if amount is not None else topup.amount

            updated = await topup_repo.update_status(
                topup.id,
                ManualTopUpStatus.APPROVED,
                amount=final_amount,
            )
            topup = updated or topup

            user = await user_repo.get_by_id(topup.user_id)
            if user:
                await user_repo.adjust_balance(user, final_amount)
                await transaction_repo.add(
                    user.id,
                    final_amount,
                    TransactionType.MANUAL,
                    f"Topup #{topup_id} approved",
                )
            return ManualTopUpStatus.APPROVED, final_amount

    async def reject_manual_topup(self, topup_id: int) -> ManualTopUpStatus:
        async with session_scope() as session:
            topup_repo = ManualTopUpRepository(session)
            await topup_repo.update_status(topup_id, ManualTopUpStatus.REJECTED)
            return ManualTopUpStatus.REJECTED

    async def list_pending_topups(self):
        async with session_scope() as session:
            topup_repo = ManualTopUpRepository(session)
            return await topup_repo.list_pending()

    async def export_transactions_csv(self) -> str:
        async with session_scope() as session:
            transaction_repo = TransactionRepository(session)
            return await transaction_repo.export_csv()

    async def adjust_balance(self, user: User, amount: int, reason: str) -> None:
        async with session_scope() as session:
            user_repo = UserRepository(session)
            transaction_repo = TransactionRepository(session)
            db_user = await user_repo.get_by_id(user.id)
            if not db_user:
                raise ValueError("User not found")
            await user_repo.adjust_balance(db_user, amount)
            await transaction_repo.add(db_user.id, amount, TransactionType.ADJUSTMENT, reason)
            user.balance = db_user.balance

    async def total_turnover(self) -> int:
        async with session_scope() as session:
            transaction_repo = TransactionRepository(session)
            return await transaction_repo.get_total_balance()


__all__ = ["BillingService"]
