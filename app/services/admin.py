from __future__ import annotations

from collections.abc import Iterable

from ..db import session_scope
from ..models import ManualTopUpStatus, User
from ..repositories import ManualTopUpRepository, TransactionRepository, UserRepository


class AdminService:
    async def find_user(self, query: str) -> User | None:
        async with session_scope() as session:
            user_repo = UserRepository(session)
            if query.isdigit():
                user = await user_repo.get_by_id(int(query))
                if user:
                    return user
                user = await user_repo.get_by_chat_id(int(query))
                if user:
                    return user
            if query.startswith("@"):
                query = query[1:]
            users = await user_repo.list_all()
            for user in users:
                if user.username and user.username.lower() == query.lower():
                    return user
            return None

    async def list_users(self) -> Iterable[User]:
        async with session_scope() as session:
            user_repo = UserRepository(session)
            return await user_repo.list_all()

    async def pending_topups(self):
        async with session_scope() as session:
            topup_repo = ManualTopUpRepository(session)
            return await topup_repo.list_pending()

    async def set_topup_status(self, topup_id: int, status: ManualTopUpStatus):
        async with session_scope() as session:
            topup_repo = ManualTopUpRepository(session)
            return await topup_repo.update_status(topup_id, status)

    async def export_transactions_csv(self) -> str:
        async with session_scope() as session:
            transaction_repo = TransactionRepository(session)
            return await transaction_repo.export_csv()


__all__ = ["AdminService"]
