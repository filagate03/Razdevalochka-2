from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.repositories import ReferralRepository, TransactionRepository, UserRepository
from app.services.billing import calculate_crypto_price
from app.services.crypto_payment import CryptoPaymentService
from app.services.referral import ReferralService

router = Router()


def _buy_keyboard(tokens: int, invoice_id: int | None = None, pay_url: str | None = None) -> InlineKeyboardMarkup:
    buttons = []
    if pay_url:
        buttons.append([InlineKeyboardButton(text="💳 Оплатить в CryptoBot", url=pay_url)])
    if invoice_id is not None:
        buttons.append([
            InlineKeyboardButton(
                text="✅ Проверить оплату",
                callback_data=f"check_crypto_{invoice_id}_{tokens}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="buy_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("buy"))
async def buy_menu(message: Message) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="10 токенов", callback_data="buy_crypto_10")],
            [InlineKeyboardButton(text="25 токенов", callback_data="buy_crypto_25")],
            [InlineKeyboardButton(text="50 токенов", callback_data="buy_crypto_50")],
        ]
    )
    await message.answer("Выберите пакет токенов:", reply_markup=keyboard)


@router.callback_query(lambda c: c.data and c.data.startswith("buy_crypto_"))
async def buy_crypto(
    callback: CallbackQuery,
    user_repo: UserRepository,
) -> None:
    await user_repo.get_or_create_user(
        callback.from_user.id,
        callback.from_user.username if callback.from_user else None,
    )
    tokens = int(callback.data.split("_")[2])
    price_usd = calculate_crypto_price(tokens)

    crypto_service = CryptoPaymentService()
    invoice = await crypto_service.create_invoice(
        amount=price_usd,
        currency="USDT",
        description=f"Покупка {tokens} токенов",
    )
    if not invoice:
        await callback.answer("❌ Ошибка создания платежа", show_alert=True)
        return
    await callback.message.edit_text(
        "💰 Счет на оплату создан\n\n"
        f"Токенов: {tokens}\n"
        f"Сумма: {invoice['amount']} {invoice['currency']}\n\n"
        "Оплатите счет и вернитесь для проверки статуса.",
        reply_markup=_buy_keyboard(tokens, invoice["invoice_id"], invoice["pay_url"]),
    )


@router.callback_query(lambda c: c.data and c.data.startswith("check_crypto_"))
async def check_crypto_payment(
    callback: CallbackQuery,
    user_repo: UserRepository,
    transaction_repo: TransactionRepository,
    referral_repo: ReferralRepository,
) -> None:
    _, _, invoice_id_str, tokens_str = callback.data.split("_")
    invoice_id = int(invoice_id_str)
    tokens = int(tokens_str)

    crypto_service = CryptoPaymentService()
    paid = await crypto_service.check_invoice(invoice_id)
    if not paid:
        await callback.answer("⏳ Оплата еще не получена", show_alert=True)
        return

    user = await user_repo.get_or_create_user(
        callback.from_user.id,
        callback.from_user.username if callback.from_user else None,
    )
    existing = await transaction_repo.get_by_external_id(f"crypto_{invoice_id}")
    if existing:
        await callback.answer("✅ Оплата уже была учтена", show_alert=True)
        return

    await user_repo.update_balance(user.chat_id, tokens, reason="CryptoBot payment")
    await transaction_repo.create(
        user_id=user.id,
        amount=tokens,
        reason="purchase",
        payment_method="crypto",
        external_id=f"crypto_{invoice_id}",
    )

    referral_service = ReferralService(user_repo, referral_repo, transaction_repo)
    await referral_service.process_purchase(user.chat_id, tokens)

    await callback.message.edit_text(
        f"✅ Оплата получена! Начислено {tokens} токенов.",
        reply_markup=None,
    )
