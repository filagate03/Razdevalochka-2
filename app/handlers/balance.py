from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..config import get_settings
from ..keyboards.common import back_to_main_keyboard
from ..services.billing import BillingService

router = Router()


@router.message(Command("pricing"))
async def cmd_pricing(message: Message):
    settings = get_settings()
    text = (
        "💵 Справочная информация:\n"
        f"• Покупка: {settings.price_buy_rub}₽ за токен\n"
        f"• Продажа: {settings.price_sell_rub}₽ за токен\n"
        "Финальная стоимость зависит от выбранного метода оплаты."
    )
    await message.answer(text, reply_markup=back_to_main_keyboard())


@router.message(Command("balance"))
async def show_balance(message: Message, billing_service: BillingService):
    user = await billing_service.get_user(message.chat.id)
    balance = user.balance if user else 0
    await message.answer(
        f"💼 Ваш баланс: <b>{balance}</b> токенов",
        reply_markup=back_to_main_keyboard(),
    )


@router.message(Command("history"))
async def history(message: Message, billing_service: BillingService):
    user = await billing_service.get_user(message.chat.id)
    if not user:
        await message.answer("📭 История пуста. Сначала выполните /start.")
        return
    transactions = await billing_service.list_user_history(user)
    if not transactions:
        await message.answer("📭 История пуста", reply_markup=back_to_main_keyboard())
        return
    lines = ["🧾 Последние операции:"]
    for txn in transactions[:10]:
        sign = "➕" if txn.amount > 0 else "➖"
        lines.append(
            f"{txn.created_at:%Y-%m-%d %H:%M} | {sign}{abs(txn.amount)} | {txn.type.value}"
        )
    await message.answer("\n".join(lines), reply_markup=back_to_main_keyboard())


@router.message(Command("support"))
async def support(message: Message):
    await message.answer(
        "🤝 Поддержка: @hunt_tg и @berkyt помогут с любыми вопросами.",
        reply_markup=back_to_main_keyboard(),
    )
