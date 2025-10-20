from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..models import User


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users")],
            [InlineKeyboardButton(text="📬 Заявки", callback_data="admin:requests")],
            [InlineKeyboardButton(text="📣 Рассылка", callback_data="admin:broadcast")],
            [InlineKeyboardButton(text="📊 Экспорт CSV", callback_data="admin:export")],
            [InlineKeyboardButton(text="🧩 Интеграции", callback_data="admin:integrations")],
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


def admin_user_list_keyboard(
    users: list[User],
    *,
    page: int,
    has_more: bool,
    has_query: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for user in users:
        username = f"@{user.username}" if user.username else "без username"
        label = f"{user.id} · {username}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"admin_user:select:{user.id}",
                )
            ]
        )

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"admin_users:page:{page - 1}")
        )
    if has_more:
        nav_row.append(
            InlineKeyboardButton(text="➡️", callback_data=f"admin_users:page:{page + 1}")
        )
    if nav_row:
        rows.append(nav_row)

    search_row = [InlineKeyboardButton(text="🔍 Поиск", callback_data="admin_users:search")]
    if has_query:
        search_row.append(InlineKeyboardButton(text="❌ Сброс", callback_data="admin_users:clear"))
    rows.append(search_row)

    rows.append([InlineKeyboardButton(text="🏠 В меню", callback_data="admin:home")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ +1", callback_data=f"admin_user_adjust:{user_id}:add:1"),
                InlineKeyboardButton(text="➕ +5", callback_data=f"admin_user_adjust:{user_id}:add:5"),
                InlineKeyboardButton(text="➕ +10", callback_data=f"admin_user_adjust:{user_id}:add:10"),
            ],
            [
                InlineKeyboardButton(text="➖ -1", callback_data=f"admin_user_adjust:{user_id}:sub:1"),
                InlineKeyboardButton(text="➖ -5", callback_data=f"admin_user_adjust:{user_id}:sub:5"),
                InlineKeyboardButton(text="➖ -10", callback_data=f"admin_user_adjust:{user_id}:sub:10"),
            ],
            [
                InlineKeyboardButton(text="✏️ Своя сумма", callback_data=f"admin_user:custom:{user_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ К списку", callback_data="admin_user:back")],
        ]
    )


__all__ = [
    "admin_main_keyboard",
    "manual_request_keyboard",
    "admin_user_list_keyboard",
    "admin_user_actions_keyboard",
]
