from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пользователи", callback_data="admin:users")],
            [InlineKeyboardButton(text="Заявки", callback_data="admin:requests")],
            [InlineKeyboardButton(text="Рассылка", callback_data="admin:broadcast")],
            [InlineKeyboardButton(text="Экспорт CSV", callback_data="admin:export")],
        ]
    )


def manual_request_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data=f"admin_request:approve:{request_id}"),
                InlineKeyboardButton(text="Отклонить", callback_data=f"admin_request:reject:{request_id}"),
            ]
        ]
    )


__all__ = ["admin_main_keyboard", "manual_request_keyboard"]
