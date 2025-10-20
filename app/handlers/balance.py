from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..config import get_settings
from ..services.billing import BillingService

router = Router()


@router.message(Command("pricing"))
async def cmd_pricing(message: Message):
    settings = get_settings()
    text = (
        "💰 Текущие параметры:\n"
        f"• Покупка: {settings.price_buy_rub}₽ за токен\n"
        f"• Продажа: {settings.price_sell_rub}₽ за токен\n"
        "Реальные сделки проходят через Telegram Stars и ручные заявки."
    )
    await message.answer(text)


@router.message(F.text.casefold() == "мой баланс")
@router.message(Command("balance"))
async def show_balance(message: Message, billing_service: BillingService):
    user = await billing_service.get_user(message.chat.id)
    balance = user.balance if user else 0
    await message.answer(f"💼 Ваш баланс: <b>{balance}</b> токенов")


@router.message(F.text.casefold() == "история операций")
async def history(message: Message, billing_service: BillingService):
    user = await billing_service.get_user(message.chat.id)
    if not user:
        await message.answer("Пользователь не найден")
        return
    transactions = await billing_service.list_user_history(user)
    if not transactions:
        await message.answer("📭 История пуста")
        return
    lines = ["🧾 Последние операции:"]
    for txn in transactions[:10]:
        sign = "+" if txn.amount > 0 else ""
        emoji = "➕" if txn.amount > 0 else "➖"
        lines.append(
            f"{txn.created_at:%Y-%m-%d %H:%M} | {emoji}{abs(txn.amount)} | {txn.type.value}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text.casefold() == "поддержка")
async def support(message: Message):
    await message.answer("🤝 Свяжитесь с менеджером через @support_username")
