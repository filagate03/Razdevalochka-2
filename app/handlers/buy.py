from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message

from ..keyboards.common import (
    buy_menu_keyboard,
    manual_amount_keyboard,
    manual_topup_keyboard,
    stars_keyboard,
)
from ..models import ManualTopUpMethod
from ..services.billing import BillingService
from ..services.stars import StarsService

router = Router()


@router.message(Command("buy"))
@router.message(F.text.casefold() == "купить токены")
async def buy_menu(message: Message):
    await message.answer("Выберите способ пополнения:", reply_markup=buy_menu_keyboard())


@router.callback_query(F.data == "buy:stars")
async def choose_stars(callback: CallbackQuery, stars_service: StarsService):
    await callback.message.answer("Выберите пакет:", reply_markup=stars_keyboard(stars_service))
    await callback.answer()


@router.callback_query(F.data.startswith("stars:pack:"))
async def send_invoice(callback: CallbackQuery, stars_service: StarsService):
    amount_str = callback.data.split(":")[-1]
    pack = stars_service.get_pack(f"pack:{amount_str}")
    if not pack:
        await callback.answer("Пакет не найден", show_alert=True)
        return
    prices = [LabeledPrice(label=f"{pack.amount} токенов", amount=pack.amount)]
    await callback.message.answer_invoice(
        title=f"Пакет {pack.amount}",
        description="Оплата через Telegram Stars",
        payload=pack.payload,
        provider_token="",
        currency=pack.currency,
        prices=prices,
    )
    await callback.answer()


@router.callback_query(F.data == "buy:manual")
async def choose_manual(callback: CallbackQuery):
    await callback.message.answer("Выберите направление платежа:", reply_markup=manual_topup_keyboard())
    await callback.answer()


MANUAL_METHOD_MAP = {
    "card_ru": ManualTopUpMethod.CARD_RU,
    "card_int": ManualTopUpMethod.CARD_INT,
    "crypto": ManualTopUpMethod.CRYPTO,
}


@router.callback_query(F.data.startswith("manual:"))
async def manual_direction(callback: CallbackQuery):
    _, method = callback.data.split(":", 1)
    if method not in MANUAL_METHOD_MAP:
        await callback.answer("Неизвестный метод", show_alert=True)
        return
    await callback.message.answer(
        "Выберите пакет, после оплаты менеджер начислит токены в течение 15 минут.",
        reply_markup=manual_amount_keyboard(method),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manual_confirm:"))
async def manual_confirm(callback: CallbackQuery, billing_service: BillingService):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Ошибка", show_alert=True)
        return
    _, method_key, amount_str = parts
    method = MANUAL_METHOD_MAP.get(method_key)
    if not method:
        await callback.answer("Неизвестный метод", show_alert=True)
        return
    try:
        amount = int(amount_str)
    except ValueError:
        await callback.answer("Ошибка", show_alert=True)
        return
    user = await billing_service.get_or_create_user(
        callback.message.chat.id,
        callback.from_user.username if callback.from_user else None,
    )
    topup = await billing_service.create_manual_topup(user, method, amount)
    await callback.message.answer(
        f"Заявка создана. Номер заявки: #{topup.id}. Менеджер свяжется с вами в течение 15 минут."
    )
    await callback.answer("Заявка создана")
