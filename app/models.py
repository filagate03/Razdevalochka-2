from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class TransactionType(str, enum.Enum):
    MANUAL = "manual"
    STARS = "stars"
    ADJUSTMENT = "adjustment"
    SYSTEM = "system"


class ManualTopUpStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ManualTopUpMethod(str, enum.Enum):
    CARD_RU = "card_ru"
    CARD_INT = "card_int"
    CRYPTO = "crypto"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(32), index=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow)

    transactions: Mapped[list[Transaction]] = relationship(back_populates="user", cascade="all, delete-orphan")
    topups: Mapped[list[ManualTopUp]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    amount: Mapped[int] = mapped_column(Integer)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, native_enum=False))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="transactions")


class ManualTopUp(Base):
    __tablename__ = "manual_topups"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    method: Mapped[ManualTopUpMethod] = mapped_column(Enum(ManualTopUpMethod, native_enum=False))
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[ManualTopUpStatus] = mapped_column(Enum(ManualTopUpStatus, native_enum=False), default=ManualTopUpStatus.PENDING, index=True)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="topups")


__all__ = [
    "User",
    "Transaction",
    "ManualTopUp",
    "TransactionType",
    "ManualTopUpStatus",
    "ManualTopUpMethod",
]
