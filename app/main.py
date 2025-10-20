from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from .config import get_settings
from .db import init_models
from .handlers import admin as admin_handlers
from .handlers import balance, buy, payments, start
from .middlewares.auth import AdminFilterMiddleware, AntiFloodMiddleware
from .services.admin import AdminService
from .services.billing import BillingService
from .services.stars import StarsService
from .services.users import UserService
from .utils.logging import configure_logging


def setup_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.middleware(AntiFloodMiddleware())
    dp.message.middleware(AdminFilterMiddleware())
    dp.callback_query.middleware(AdminFilterMiddleware())

    dp.include_router(start.router)
    dp.include_router(balance.router)
    dp.include_router(buy.router)
    dp.include_router(payments.router)
    dp.include_router(admin_handlers.router)

    return dp


async def main() -> None:
    configure_logging()
    settings = get_settings()
    await init_models()

    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)

    billing_service = BillingService()
    user_service = UserService()
    admin_service = AdminService()
    stars_service = StarsService()

    bot["billing_service"] = billing_service
    bot["user_service"] = user_service
    bot["admin_service"] = admin_service
    bot["stars_service"] = stars_service

    dp = setup_dispatcher()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
