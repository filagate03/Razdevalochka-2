from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..config import Settings
from ..services.stars import StarsService


def portal_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Баланс", callback_data="portal:balance"),
                InlineKeyboardButton(text="🛒 Пополнить", callback_data="portal:buy"),
            ],
            [
                InlineKeyboardButton(text="🧾 История", callback_data="portal:history"),
                InlineKeyboardButton(text="🎨 Генерация", callback_data="portal:generate"),
            ],
            [
                InlineKeyboardButton(text="ℹ️ Прайс", callback_data="portal:pricing"),
                InlineKeyboardButton(text="🆘 Поддержка", callback_data="portal:support"),
            ],
        ]
    )


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data="portal:home")]]
    )


def stars_keyboard(stars_service: StarsService) -> InlineKeyboardMarkup:
    rows = []
    for pack in stars_service.packs:
        rows.append([
            InlineKeyboardButton(
                text=f"{pack.amount} токенов",
                callback_data=f"stars:pack:{pack.amount}",
            )
        ])
    rows.append(
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="buy:back"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="portal:home"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def manual_topup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Карта РФ", callback_data="manual:card_ru")],
            [InlineKeyboardButton(text="🌍 Международная карта", callback_data="manual:card_int")],
            [InlineKeyboardButton(text="💠 CryptoBot", callback_data="manual:crypto")],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="buy:back"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="portal:home"),
            ],
        ]
    )


def buy_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✨ Telegram Stars", callback_data="buy:stars")],
            [InlineKeyboardButton(text="🏦 Ручное пополнение", callback_data="buy:manual")],
            [InlineKeyboardButton(text="🔗 Внешняя ссылка", url="https://example.com/pay")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="portal:home")],
        ]
    )


def manual_amount_keyboard(method: str, settings: Settings) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for amount in sorted(settings.get_stars_packs_list()):
        price_rub = amount * settings.price_buy_rub if settings.price_buy_rub else None
        price_label = (
            f"{amount} токенов"
            if price_rub is None
            else f"{amount} токенов · {price_rub}₽"
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=price_label,
                    callback_data=f"manual_confirm:{method}:{amount}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="manual:back"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="portal:home"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def purchase_complete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Купить ещё", callback_data="portal:buy")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="portal:home")],
        ]
    )


def generation_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="portal:home")]]
    )


__all__ = [
    "portal_main_keyboard",
    "back_to_main_keyboard",
    "stars_keyboard",
    "manual_topup_keyboard",
    "buy_menu_keyboard",
    "manual_amount_keyboard",
    "purchase_complete_keyboard",
    "generation_prompt_keyboard",
]
