from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, Update

from ..config import get_settings
from ..services.admin import AdminService


class AdminFilterMiddleware(BaseMiddleware):
    def __init__(self):
        self._settings = get_settings()

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        subject = None
        if isinstance(event, Message):
            subject = event.from_user
        elif isinstance(event, CallbackQuery):
            subject = event.from_user
        if subject:
            chat_id = subject.id
            username = subject.username
            is_admin = chat_id in self._settings.admins
            if not is_admin:
                admin_service: AdminService | None = data.get("admin_service")
                if admin_service:
                    is_admin = await admin_service.is_admin(chat_id, username)
            data["is_admin"] = is_admin
        return await handler(event, data)


class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.0):
        self.rate_limit = rate_limit
        self._storage: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            now = time.monotonic()
            user_id = event.from_user.id
            last_time = self._storage.get(user_id, 0.0)
            if now - last_time < self.rate_limit:
                return
            self._storage[user_id] = now
        return await handler(event, data)


__all__ = ["AdminFilterMiddleware", "AntiFloodMiddleware"]
