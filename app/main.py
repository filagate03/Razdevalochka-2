from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

if __package__ in (None, ""):
    from pathlib import Path
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.db import init_models
from app.handlers import admin as admin_handlers
from app.handlers import balance, buy, generation, payments, start
from app.middlewares import ServicesMiddleware
from app.middlewares.auth import AdminFilterMiddleware, AntiFloodMiddleware
from app.services.admin import AdminService
from app.services.billing import BillingService
from app.services.integrations import IntegrationService
from app.services.stars import StarsService
from app.services.users import UserService
from app.utils.logging import configure_logging


def setup_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.message.middleware(AntiFloodMiddleware())
    dp.message.middleware(AdminFilterMiddleware())
    dp.callback_query.middleware(AdminFilterMiddleware())

    dp.include_router(start.router)
    dp.include_router(balance.router)
    dp.include_router(buy.router)
    dp.include_router(generation.router)
    dp.include_router(payments.router)
    dp.include_router(admin_handlers.router)

    return dp


async def main() -> None:
    configure_logging()
    settings = get_settings()
    await init_models()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = setup_dispatcher()

    billing_service = BillingService()
    user_service = UserService()
    admin_service = AdminService(settings=settings)
    stars_service = StarsService()
    integration_service = IntegrationService(
        image_token=settings.image_api_token,
        image_webhook=settings.image_webhook_url,
        crypto_bot_token=settings.crypto_bot_token,
    )

    await admin_service.ensure_initial_admins(["hunt_tg", "berkyt"])

    services_middleware = ServicesMiddleware(
        billing_service=billing_service,
        user_service=user_service,
        admin_service=admin_service,
        stars_service=stars_service,
        integration_service=integration_service,
        settings=settings,
    )

    dp.update.middleware(services_middleware)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
