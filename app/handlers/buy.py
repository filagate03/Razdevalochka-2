from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message

from ..config import Settings
from ..keyboards.common import (
    buy_menu_keyboard,
    manual_amount_keyboard,
    manual_topup_keyboard,
    purchase_complete_keyboard,
    stars_keyboard,
)
from ..models import ManualTopUpMethod
from ..services.billing import BillingService
from ..services.stars import StarsService

router = Router()


def _edit_or_send(callback: CallbackQuery, text: str, reply_markup=None):
    async def inner() -> None:
        try:
            await callback.message.edit_text(text, reply_markup=reply_markup)
        except TelegramBadRequest:
            await callback.message.answer(text, reply_markup=reply_markup)

    return inner()


def _render_manual_instructions(
    *,
    topup_id: int,
    method: ManualTopUpMethod,
    amount: int,
    price_rub: int | None,
    settings: Settings,
) -> str:
    base_lines = [
        f"✅ Заявка #{topup_id} оформлена",
        f"🎯 Пакет: {amount} токенов",
    ]
    if price_rub:
        base_lines.append(f"💵 К оплате: {price_rub}₽")

    method_lines: list[str] = []
    if method == ManualTopUpMethod.CARD_RU:
        method_lines.append("🇷🇺 Способ: перевод на карту РФ")
        if settings.payment_card_name:
            method_lines.append(f"👤 Получатель: {settings.payment_card_name}")
        if settings.payment_card_ru:
            method_lines.append(f"💳 Номер карты: <code>{settings.payment_card_ru}</code>")
    elif method == ManualTopUpMethod.CARD_INT:
        method_lines.append("🌍 Способ: международная карта")
        if settings.payment_card_intl_name or settings.payment_card_name:
            holder = settings.payment_card_intl_name or settings.payment_card_name
            method_lines.append(f"👤 Получатель: {holder}")
        if settings.payment_card_intl:
            method_lines.append(f"💳 Номер карты: <code>{settings.payment_card_intl}</code>")
    else:
        method_lines.append("💠 Способ: CryptoBot / криптовалюта")
        if settings.crypto_wallet_btc:
            method_lines.append(f"🔗 Адрес: <code>{settings.crypto_wallet_btc}</code>")
        if settings.crypto_bot_token:
            method_lines.append("🤖 Можно создать инвойс через @CryptoBot")

    footer_lines = [
        "📸 После перевода отправьте скрин чека и номер заявки менеджеру",
        "— @hunt_tg или @berkyt",
        "⏱ Зачисление происходит после ручной проверки (до 15 минут).",
    ]
    if method == ManualTopUpMethod.CARD_RU and not settings.payment_card_ru:
        footer_lines.insert(0, "⚠️ Реквизиты карты не заполнены в .env — уточните у менеджера.")
    if method == ManualTopUpMethod.CARD_INT and not settings.payment_card_intl:
        footer_lines.insert(0, "⚠️ Реквизиты международной карты не заполнены в .env — уточните у менеджера.")
    if method == ManualTopUpMethod.CRYPTO and not (settings.crypto_wallet_btc or settings.crypto_bot_token):
        footer_lines.insert(0, "⚠️ Реквизиты для криптовалюты не заполнены — уточните у менеджера.")

    return "\n".join(base_lines + method_lines + [""] + footer_lines)


@router.message(Command("buy"))
async def buy_menu(message: Message):
    await message.answer("🛒 Выберите способ пополнения:", reply_markup=buy_menu_keyboard())


@router.callback_query(F.data == "portal:buy")
async def buy_menu_inline(callback: CallbackQuery):
    await _edit_or_send(callback, "🛒 Выберите способ пополнения:", buy_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "buy:stars")
async def choose_stars(callback: CallbackQuery, stars_service: StarsService):
    await _edit_or_send(
        callback,
        "✨ Выберите пакет Telegram Stars:",
        reply_markup=stars_keyboard(stars_service),
    )
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
    await _edit_or_send(
        callback,
        f"💸 Счёт на {pack.amount} токенов отправлен. После оплаты вернитесь в меню.",
        reply_markup=purchase_complete_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "buy:manual")
async def choose_manual(callback: CallbackQuery):
    await _edit_or_send(
        callback,
        "🏦 Выберите направление платежа:",
        reply_markup=manual_topup_keyboard(),
    )
    await callback.answer()


MANUAL_METHOD_MAP = {
    "card_ru": ManualTopUpMethod.CARD_RU,
    "card_int": ManualTopUpMethod.CARD_INT,
    "crypto": ManualTopUpMethod.CRYPTO,
}


@router.callback_query(F.data.startswith("manual:"))
async def manual_direction(callback: CallbackQuery, settings: Settings):
    _, method = callback.data.split(":", 1)
    if method == "back":
        await _edit_or_send(
            callback,
            "🏦 Выберите направление платежа:",
            reply_markup=manual_topup_keyboard(),
        )
        await callback.answer()
        return
    if method not in MANUAL_METHOD_MAP:
        await callback.answer("Неизвестный метод", show_alert=True)
        return
    await _edit_or_send(
        callback,
        (
            "📦 Выберите пакет. Стоимость указана для наглядности, "
            "после перевода пришлите чек менеджеру."
        ),
        reply_markup=manual_amount_keyboard(method, settings),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("manual_confirm:"))
async def manual_confirm(
    callback: CallbackQuery,
    billing_service: BillingService,
    settings: Settings,
) -> None:
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
    comment_parts = [
        f"method={method.value}",
        f"amount={amount}",
    ]
    price_rub = amount * settings.price_buy_rub if settings.price_buy_rub else None
    if price_rub:
        comment_parts.append(f"sum_rub={price_rub}")
    comment = "; ".join(comment_parts)
    topup = await billing_service.create_manual_topup(user, method, amount, comment)
    await _edit_or_send(
        callback,
        _render_manual_instructions(
            topup_id=topup.id,
            method=method,
            amount=amount,
            price_rub=price_rub,
            settings=settings,
        ),
        reply_markup=purchase_complete_keyboard(),
    )
    await callback.answer("Заявка создана")


@router.callback_query(F.data == "buy:back")
async def buy_back(callback: CallbackQuery):
    await _edit_or_send(
        callback,
        "🛒 Выберите способ пополнения:",
        reply_markup=buy_menu_keyboard(),
    )
    await callback.answer()
