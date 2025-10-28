from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from app.config import get_settings
from app.db import get_session_factory, init_db
from app.handlers import admin, generate, payment, referral, start
from app.middlewares import AdminMiddleware, RepositoryMiddleware, ThrottlingMiddleware
from app.repositories import UserRepository
from app.services.image_generation import ImageGenerationService
from app.utils.logging import configure_logging


async def on_startup(bot: Bot) -> None:
    settings = get_settings()
    configure_logging()
    await init_db()
    if settings.use_webhook:
        webhook_url = f"{settings.webhook_host}{settings.webhook_path}"
        await bot.set_webhook(url=webhook_url, secret_token=settings.webhook_secret, drop_pending_updates=True)
        logging.getLogger(__name__).info("Webhook set: %s", webhook_url)
    service = ImageGenerationService()
    await service.get_collections()


async def on_shutdown(bot: Bot) -> None:
    settings = get_settings()
    if settings.use_webhook:
        await bot.delete_webhook()


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(referral.router)
    dp.include_router(admin.router)
    dp.include_router(payment.router)
    dp.include_router(generate.router)
    return dp


def create_app() -> web.Application:
    settings = get_settings()
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher()

    session_factory = get_session_factory()
    user_repo = UserRepository(session_factory)

    dp.update.middleware(RepositoryMiddleware(session_factory))
    dp.update.middleware(AdminMiddleware(user_repo))
    dp.update.middleware(ThrottlingMiddleware())

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=settings.webhook_secret)
    webhook_handler.register(app, path=settings.webhook_path)

    async def health(request):
        return web.Response(text="OK")

    app.router.add_get("/health", health)
    setup_application(app, dp, bot=bot)

    return app


def main() -> None:
    app = create_app()
    port = int(os.getenv("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
