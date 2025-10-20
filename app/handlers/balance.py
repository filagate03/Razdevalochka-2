from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..config import get_settings

router = Router()


def _get_billing(message: Message):
    return message.bot.get("billing_service")


@router.message(Command("pricing"))
async def cmd_pricing(message: Message):
    settings = get_settings()
    text = (
        "Текущие параметры:\n"
        f"• Рекомендованная цена покупки: {settings.price_buy_rub}₽ за токен\n"
        f"• Рекомендованная цена продажи: {settings.price_sell_rub}₽ за токен\n"
        "Фактические продажи осуществляются через Telegram Stars или по заявкам."
    )
    await message.answer(text)


@router.message(F.text.casefold() == "мой баланс")
@router.message(Command("balance"))
async def show_balance(message: Message):
    billing_service = _get_billing(message)
    if not billing_service:
        await message.answer("Сервис временно недоступен")
        return
    user = await billing_service.get_user(message.chat.id)
    balance = user.balance if user else 0
    await message.answer(f"Ваш баланс: {balance} токенов")


@router.message(F.text.casefold() == "история операций")
async def history(message: Message):
    billing_service = _get_billing(message)
    if not billing_service:
        await message.answer("Сервис временно недоступен")
        return
    user = await billing_service.get_user(message.chat.id)
    if not user:
        await message.answer("Пользователь не найден")
        return
    transactions = await billing_service.list_user_history(user)
    if not transactions:
        await message.answer("История пуста")
        return
    lines = ["Последние операции:"]
    for txn in transactions[:10]:
        sign = "+" if txn.amount > 0 else ""
        lines.append(f"{txn.created_at:%Y-%m-%d %H:%M} | {sign}{txn.amount} | {txn.type.value}")
    await message.answer("\n".join(lines))


@router.message(F.text.casefold() == "поддержка")
async def support(message: Message):
    await message.answer("Свяжитесь с менеджером через @support_username")
