from __future__ import annotations

from collections.abc import Iterable

from ..config import Settings, get_settings
from ..db import session_scope
from ..models import AdminMember, ManualTopUpStatus, User
from ..repositories import (
    AdminRepository,
    ManualTopUpRepository,
    TransactionRepository,
    UserRepository,
)


class AdminService:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()

    async def is_admin(self, user_id: int | None, username: str | None) -> bool:
        if user_id and user_id in self._settings.admins:
            return True
        if not user_id and not username:
            return False
        normalized = username.strip().lstrip("@") if username else None
        async with session_scope() as session:
            admin_repo = AdminRepository(session)
            if user_id:
                admin = await admin_repo.get_by_chat_id(user_id)
                if admin:
                    return True
            if normalized:
                admin = await admin_repo.get_by_username(normalized)
                if admin:
                    return True
        return False

    async def ensure_initial_admins(self, usernames: Iterable[str]) -> None:
        async with session_scope() as session:
            admin_repo = AdminRepository(session)
            for username in usernames:
                cleaned = username.strip().lstrip("@")
                if not cleaned:
                    continue
                await admin_repo.ensure_username(cleaned)

    async def sync_user_record(self, user: User) -> None:
        if not user:
            return
        username = user.username or ""
        async with session_scope() as session:
            admin_repo = AdminRepository(session)
            admin = await admin_repo.get_by_chat_id(user.chat_id)
            if admin:
                await admin_repo.attach_user(admin, user)
                return
            if username:
                admin = await admin_repo.get_by_username(username)
                if admin:
                    await admin_repo.attach_user(admin, user)

    async def list_admins(self) -> list[AdminMember]:
        async with session_scope() as session:
            admin_repo = AdminRepository(session)
            return await admin_repo.list_all()

    async def add_admin_by_username(
        self,
        username: str,
        *,
        added_by: int | None = None,
    ) -> AdminMember:
        cleaned = username.strip().lstrip("@")
        if not cleaned:
            raise ValueError("Username must not be empty")
        async with session_scope() as session:
            admin_repo = AdminRepository(session)
            added_by_id = None
            if added_by is not None:
                inviter = await admin_repo.get_by_chat_id(added_by)
                if inviter:
                    added_by_id = inviter.id
            return await admin_repo.ensure_username(cleaned, added_by_id=added_by_id)

    async def remove_admin_by_username(self, username: str) -> bool:
        async with session_scope() as session:
            admin_repo = AdminRepository(session)
            admin = await admin_repo.get_by_username(username.strip().lstrip("@"))
            if not admin:
                return False
            await admin_repo.remove(admin)
            return True

    async def remove_admin_target(self, token: str) -> bool:
        identifier = token.strip()
        if not identifier:
            return False
        async with session_scope() as session:
            admin_repo = AdminRepository(session)
            admin: AdminMember | None = None
            if identifier.startswith("user:"):
                admin = await admin_repo.get_by_username(identifier.split(":", 1)[1])
            elif identifier.startswith("chat:"):
                value = identifier.split(":", 1)[1]
                try:
                    admin = await admin_repo.get_by_chat_id(int(value))
                except ValueError:
                    admin = None
            elif identifier.startswith("id:"):
                value = identifier.split(":", 1)[1]
                try:
                    admin = await admin_repo.get_by_id(int(value))
                except ValueError:
                    admin = None
            else:
                admin = await admin_repo.get_by_username(identifier)
            if not admin:
                return False
            await admin_repo.remove(admin)
            return True

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

    async def list_users_page(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None = None,
    ) -> tuple[list[User], bool]:
        async with session_scope() as session:
            user_repo = UserRepository(session)
            return await user_repo.list_page(page=page, page_size=page_size, query=query)

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
