from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from ..services.stars import StarsService


def main_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="Мой баланс"), KeyboardButton(text="Купить токены")],
        [KeyboardButton(text="История операций"), KeyboardButton(text="Поддержка")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def stars_keyboard(stars_service: StarsService) -> InlineKeyboardMarkup:
    rows = []
    for pack in stars_service.packs:
        rows.append([
            InlineKeyboardButton(
                text=f"{pack.amount} токенов",
                callback_data=f"stars:pack:{pack.amount}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def manual_topup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="РФ карты", callback_data="manual:card_ru")],
            [InlineKeyboardButton(text="Международные", callback_data="manual:card_int")],
            [InlineKeyboardButton(text="Криптовалюта", callback_data="manual:crypto")],
        ]
    )


def buy_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Telegram Stars", callback_data="buy:stars")],
            [InlineKeyboardButton(text="Ручное пополнение", callback_data="buy:manual")],
            [InlineKeyboardButton(text="Внешняя ссылка", url="https://example.com/pay")],
        ]
    )


def manual_amount_keyboard(method: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 токен", callback_data=f"manual_confirm:{method}:1")],
            [InlineKeyboardButton(text="3 токена", callback_data=f"manual_confirm:{method}:3")],
            [InlineKeyboardButton(text="5 токенов", callback_data=f"manual_confirm:{method}:5")],
            [InlineKeyboardButton(text="10 токенов", callback_data=f"manual_confirm:{method}:10")],
        ]
    )


__all__ = [
    "main_menu",
    "stars_keyboard",
    "manual_topup_keyboard",
    "buy_menu_keyboard",
    "manual_amount_keyboard",
]
