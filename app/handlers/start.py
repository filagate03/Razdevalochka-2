from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from ..keyboards.common import main_menu
from ..services.billing import BillingService

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, billing_service: BillingService):
    await billing_service.get_or_create_user(
        message.chat.id,
        message.from_user.username if message.from_user else None,
    )
    await message.answer(
        "Привет! Это инфраструктура токенов. Используй меню ниже для управления балансом.",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "Доступные команды:\n"
        "/start — регистрация и главное меню\n"
        "/help — показать эту справку\n"
        "/buy — открыть способы пополнения\n"
        "/pricing — информация о токенах\n"
        "/health — статус (для админов)\n"
    )
    await message.answer(text)
