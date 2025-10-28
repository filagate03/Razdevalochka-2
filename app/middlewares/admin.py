from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.config import get_settings
from app.repositories import UserRepository


class AdminMiddleware(BaseMiddleware):
    def __init__(self, user_repo: UserRepository) -> None:
        super().__init__()
        self.user_repo = user_repo
        self.settings = get_settings()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            data["is_admin"] = False
            return await handler(event, data)
        db_user = await self.user_repo.get_by_chat_id(user.id)
        is_admin_db = db_user.is_admin if db_user else False
        fallback_admins = set(self.settings.admins)
        is_admin_env = user.id in fallback_admins
        if is_admin_env and db_user and not db_user.is_admin:
            await self.user_repo.set_admin(user.id, True)
            is_admin_db = True
        data["is_admin"] = is_admin_db or is_admin_env
        return await handler(event, data)
