from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from io import StringIO
import csv

from sqlalchemy import Select, cast, func, or_, select, update
from sqlalchemy.sql.sqltypes import String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    AdminMember,
    BotSettings,
    ManualTopUp,
    ManualTopUpMethod,
    ManualTopUpStatus,
    Transaction,
    TransactionType,
    User,
)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, chat_id: int, username: str | None) -> User:
        stmt: Select = select(User).where(User.chat_id == chat_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            user = User(chat_id=chat_id, username=username)
            self.session.add(user)
            await self.session.flush()
        else:
            if username and user.username != username:
                user.username = username
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_chat_id(self, chat_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.chat_id == chat_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> Iterable[User]:
        result = await self.session.execute(select(User).order_by(User.created_at))
        return result.scalars().all()

    async def list_page(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None = None,
    ) -> tuple[list[User], bool]:
        base_stmt = select(User).order_by(User.created_at)
        if query:
            normalized = query.strip()
            if normalized.startswith("@"):
                normalized = normalized[1:]
            lowered = normalized.lower()
            pattern = f"%{lowered}%"
            conditions = [func.lower(User.username).like(pattern)]
            if normalized.isdigit():
                value = int(normalized)
                conditions.extend([User.chat_id == value, User.id == value])
            else:
                like_pattern = f"%{normalized}%"
                conditions.extend(
                    [
                        cast(User.chat_id, String).like(like_pattern),
                        cast(User.id, String).like(like_pattern),
                    ]
                )
            base_stmt = base_stmt.where(or_(*conditions))
        stmt = base_stmt.offset(page * page_size).limit(page_size + 1)
        result = await self.session.execute(stmt)
        users = list(result.scalars().all())
        has_more = len(users) > page_size
        return users[:page_size], has_more

    async def adjust_balance(self, user: User, amount: int) -> User:
        user.balance += amount
        await self.session.flush()
        return user


class TransactionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, user_id: int, amount: int, type_: TransactionType, description: str | None) -> Transaction:
        transaction = Transaction(user_id=user_id, amount=amount, type=type_, description=description)
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def list_by_user(self, user_id: int, limit: int = 50) -> list[Transaction]:
        stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def export_csv(self) -> str:
        stmt = select(
            Transaction.id,
            Transaction.user_id,
            Transaction.amount,
            Transaction.type,
            Transaction.description,
            Transaction.created_at,
        ).order_by(Transaction.created_at)
        result = await self.session.execute(stmt)
        rows = result.all()

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "user_id", "amount", "type", "description", "created_at"])
        for row in rows:
            writer.writerow(row)
        return buffer.getvalue()

    async def get_total_balance(self) -> int:
        stmt = select(func.sum(Transaction.amount))
        result = await self.session.execute(stmt)
        value = result.scalar()
        return int(value or 0)


class ManualTopUpRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_id: int, method: ManualTopUpMethod, amount: int, comment: str | None) -> ManualTopUp:
        topup = ManualTopUp(user_id=user_id, method=method, amount=amount, comment=comment)
        self.session.add(topup)
        await self.session.flush()
        return topup

    async def list_pending(self) -> list[ManualTopUp]:
        stmt = (
            select(ManualTopUp)
            .where(ManualTopUp.status == ManualTopUpStatus.PENDING)
            .options(selectinload(ManualTopUp.user))
            .order_by(ManualTopUp.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        topup_id: int,
        status: ManualTopUpStatus,
        *,
        amount: int | None = None,
    ) -> ManualTopUp | None:
        values = {"status": status, "updated_at": datetime.utcnow()}
        if amount is not None:
            values["amount"] = amount
        stmt = (
            update(ManualTopUp)
            .where(ManualTopUp.id == topup_id)
            .values(**values)
            .returning(ManualTopUp)
        )
        result = await self.session.execute(stmt)
        topup = result.scalar_one_or_none()
        return topup

    async def get(self, topup_id: int) -> ManualTopUp | None:
        result = await self.session.execute(select(ManualTopUp).where(ManualTopUp.id == topup_id))
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> list[ManualTopUp]:
        stmt = select(ManualTopUp).where(ManualTopUp.user_id == user_id).order_by(ManualTopUp.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[AdminMember]:
        result = await self.session.execute(select(AdminMember).order_by(AdminMember.created_at))
        return list(result.scalars().all())

    async def get_by_username(self, username: str) -> AdminMember | None:
        normalized = username.lstrip("@")
        result = await self.session.execute(
            select(AdminMember).where(func.lower(AdminMember.username) == func.lower(normalized))
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, admin_id: int) -> AdminMember | None:
        result = await self.session.execute(select(AdminMember).where(AdminMember.id == admin_id))
        return result.scalar_one_or_none()

    async def get_by_chat_id(self, chat_id: int) -> AdminMember | None:
        result = await self.session.execute(select(AdminMember).where(AdminMember.chat_id == chat_id))
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> AdminMember | None:
        result = await self.session.execute(select(AdminMember).where(AdminMember.user_id == user_id))
        return result.scalar_one_or_none()

    async def ensure_username(self, username: str, *, added_by_id: int | None = None) -> AdminMember:
        normalized = username.lstrip("@")
        admin = await self.get_by_username(normalized)
        if admin is None:
            admin = AdminMember(username=normalized, added_by_id=added_by_id)
            self.session.add(admin)
            await self.session.flush()
        return admin

    async def attach_user(self, admin: AdminMember, user: User) -> AdminMember:
        admin.user_id = user.id
        admin.chat_id = user.chat_id
        if not admin.username and user.username:
            admin.username = user.username
        await self.session.flush()
        return admin

    async def detach_user(self, admin: AdminMember) -> AdminMember:
        admin.user_id = None
        admin.chat_id = None
        await self.session.flush()
        return admin

    async def remove(self, admin: AdminMember) -> None:
        await self.session.delete(admin)


class BotSettingsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self) -> BotSettings:
        result = await self.session.execute(select(BotSettings).limit(1))
        settings = result.scalar_one_or_none()
        if settings is None:
            settings = BotSettings(id=1)
            self.session.add(settings)
            await self.session.flush()
        return settings

    async def update_greeting(
        self,
        *,
        text: str | None = None,
        image_file_id: str | None = None,
    ) -> BotSettings:
        settings = await self.get()
        settings.greeting_text = text
        settings.greeting_image_file_id = image_file_id
        await self.session.flush()
        return settings


__all__ = [
    "UserRepository",
    "TransactionRepository",
    "ManualTopUpRepository",
    "AdminRepository",
    "BotSettingsRepository",
]
