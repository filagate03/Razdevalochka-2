from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery

from ..models import TransactionType

router = Router()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def payment_success(message: Message):
    billing_service = message.bot.get("billing_service")
    stars_service = message.bot.get("stars_service")
    if not billing_service or not stars_service:
        await message.answer("Сервис недоступен")
        return
    payload = message.successful_payment.invoice_payload
    pack = stars_service.get_pack(payload)
    if not pack:
        await message.answer("Не удалось определить пакет")
        return
    user = await billing_service.get_or_create_user(
        message.chat.id,
        message.from_user.username if message.from_user else None,
    )
    await billing_service.add_transaction(user, pack.amount, TransactionType.STARS, "Telegram Stars")
    await message.answer(f"Платеж успешен! Начислено {pack.amount} токенов")
