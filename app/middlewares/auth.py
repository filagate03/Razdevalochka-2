from __future__ import annotations

import time
from typing import Any, Callable, Dict, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, Update

from ..config import get_settings


class AdminFilterMiddleware(BaseMiddleware):
    def __init__(self):
        self._settings = get_settings()

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            data["is_admin"] = event.from_user and event.from_user.id in self._settings.admins
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
