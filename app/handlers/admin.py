from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message

from ..keyboards.admin import (
    admin_main_keyboard,
    admin_admins_keyboard,
    admin_user_actions_keyboard,
    admin_user_list_keyboard,
    manual_request_keyboard,
)
from ..models import ManualTopUpStatus, User
from ..services.admin import AdminService
from ..services.billing import BillingService
from ..services.integrations import IntegrationService
from ..services.users import UserService

router = Router()

PAGE_SIZE = 5


class AdminStates(StatesGroup):
    waiting_for_user_query = State()
    waiting_for_broadcast = State()
    waiting_for_custom_amount = State()
    waiting_for_admin_username = State()


async def respond_with_panel(
    message: Message,
    state: FSMContext,
    text: str,
    markup,
) -> Message:
    try:
        updated = await message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        updated = await message.answer(text, reply_markup=markup)
    await state.update_data(
        panel_chat_id=updated.chat.id,
        panel_message_id=updated.message_id,
    )
    return updated


async def edit_panel_from_state(
    state: FSMContext,
    bot: Bot,
    *,
    text: str,
    markup,
) -> None:
    data = await state.get_data()
    chat_id = data.get("panel_chat_id")
    message_id = data.get("panel_message_id")
    if not chat_id or not message_id:
        return
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup,
        )
    except TelegramBadRequest:
        pass


async def build_user_list_payload(
    admin_service: AdminService,
    *,
    page: int,
    query: str | None,
) -> tuple[str, InlineKeyboardMarkup]:
    users, has_more = await admin_service.list_users_page(
        page=page,
        page_size=PAGE_SIZE,
        query=query,
    )
    header = "👥 Управление пользователями"
    if query:
        header += f"\n🔎 Фильтр: <b>{query}</b>"

    if users:
        body_lines = [
            "• {id} · {username} · {balance}🪙".format(
                id=user.id,
                username=f"@{user.username}" if user.username else str(user.chat_id),
                balance=user.balance,
            )
            for user in users
        ]
        body = "\n".join(body_lines)
    else:
        body = "Пока нет пользователей по текущему фильтру."

    text = f"{header}\n\n{body}"
    markup = admin_user_list_keyboard(
        users,
        page=page,
        has_more=has_more,
        has_query=bool(query),
    )
    return text, markup


async def render_user_list(
    *,
    message: Message | None,
    bot: Bot | None,
    state: FSMContext,
    admin_service: AdminService,
    page: int,
) -> None:
    data = await state.get_data()
    query = data.get("admin_user_query")
    text, markup = await build_user_list_payload(
        admin_service,
        page=page,
        query=query,
    )
    if message:
        await respond_with_panel(message, state, text, markup)
    elif bot:
        await edit_panel_from_state(state, bot, text=text, markup=markup)
    await state.update_data(admin_user_page=page)


async def render_user_detail(
    *,
    message: Message | None,
    bot: Bot | None,
    state: FSMContext,
    billing_service: BillingService,
    user: User,
) -> None:
    transactions = await billing_service.list_user_history(user, limit=5)
    lines = [
        "👤 <b>{}</b>".format(user.username or user.chat_id),
        f"🆔 ID: {user.id}",
        f"💬 Username: @{user.username}" if user.username else "💬 Username: —",
        f"💰 Баланс: <b>{user.balance}</b> токенов",
        "",
        "🧾 Последние операции:",
    ]
    if transactions:
        for txn in transactions[:5]:
            sign = "➕" if txn.amount > 0 else "➖"
            lines.append(
                f"{txn.created_at:%d.%m %H:%M} · {sign}{abs(txn.amount)} · {txn.type.value}"
            )
    else:
        lines.append("История ещё пуста.")
    lines.append("\nВыберите действие ниже, чтобы скорректировать баланс.")

    text = "\n".join(lines)
    markup = admin_user_actions_keyboard(user.id)
    if message:
        await respond_with_panel(message, state, text, markup)
    elif bot:
        await edit_panel_from_state(state, bot, text=text, markup=markup)
    await state.update_data(selected_user_id=user.id)


async def render_admins_panel(
    *,
    message: Message | None,
    bot: Bot | None,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    admins = await admin_service.list_admins()
    if admins:
        lines = ["🛡 Список администраторов:"]
        for admin in admins:
            username = f"@{admin.username}" if admin.username else "(без username)"
            suffix = f" · {admin.chat_id}" if admin.chat_id else ""
            lines.append(f"• {username}{suffix}")
        text = "\n".join(lines)
    else:
        text = "🛡 Пока нет назначенных администраторов. Добавьте username, чтобы выдать права."
    markup = admin_admins_keyboard(admins)
    if message:
        await respond_with_panel(message, state, text, markup)
    elif bot:
        await edit_panel_from_state(state, bot, text=text, markup=markup)


@router.callback_query(F.data == "admin:admins")
async def admin_admins(
    callback: CallbackQuery,
    state: FSMContext,
    admin_service: AdminService,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await render_admins_panel(
        message=callback.message,
        bot=None,
        state=state,
        admin_service=admin_service,
    )
    await callback.answer()


@router.callback_query(F.data == "admin:admins:add")
async def admin_admins_add(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_admin_username)
    await callback.message.answer(
        "🆕 Отправьте username нового администратора (например, @hunt_tg)."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:admins:remove:"))
async def admin_admins_remove(
    callback: CallbackQuery,
    admin_service: AdminService,
    state: FSMContext,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    token = callback.data.split(":", 3)[-1]
    removed = await admin_service.remove_admin_target(token)
    if removed:
        await render_admins_panel(
            message=None,
            bot=callback.bot,
            state=state,
            admin_service=admin_service,
        )
        await callback.answer("Администратор удалён")
    else:
        await callback.answer("Не удалось найти администратора", show_alert=True)


@router.callback_query(F.data == "admin:admins:noop")
async def admin_admins_noop(callback: CallbackQuery, is_admin: bool):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
    else:
        await callback.answer()


@router.message(AdminStates.waiting_for_admin_username)
async def admin_admins_handle_username(
    message: Message,
    state: FSMContext,
    admin_service: AdminService,
    is_admin: bool,
):
    if not is_admin:
        return
    raw_username = (message.text or "").strip()
    if not raw_username:
        await message.answer("Введите username нового администратора.")
        return
    try:
        admin = await admin_service.add_admin_by_username(
            raw_username,
            added_by=message.from_user.id if message.from_user else None,
        )
    except ValueError:
        await message.answer("Имя пользователя должно быть в формате @username")
        return
    mention = f"@{admin.username}" if admin.username else "Администратор"
    await message.answer(f"✅ {mention} добавлен.")
    await render_admins_panel(
        message=None,
        bot=message.bot,
        state=state,
        admin_service=admin_service,
    )
    await state.set_state(None)


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        return
    await state.clear()
    await message.answer("🛠 Админ-панель:", reply_markup=admin_main_keyboard())


@router.callback_query(F.data == "admin:home")
async def admin_home(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("🛠 Админ-панель:", reply_markup=admin_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin:users")
async def admin_users(
    callback: CallbackQuery,
    state: FSMContext,
    admin_service: AdminService,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.update_data(admin_user_query=None)
    await render_user_list(
        message=callback.message,
        bot=None,
        state=state,
        admin_service=admin_service,
        page=0,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_users:page:"))
async def admin_users_page(
    callback: CallbackQuery,
    state: FSMContext,
    admin_service: AdminService,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, _, page_str = callback.data.split(":", 2)
    page = int(page_str)
    await render_user_list(
        message=callback.message,
        bot=None,
        state=state,
        admin_service=admin_service,
        page=page,
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users:search")
async def admin_users_search(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_user_query)
    await callback.message.answer("🔍 Введите username, ID или chat_id пользователя")
    await callback.answer()


@router.callback_query(F.data == "admin_users:clear")
async def admin_users_clear(
    callback: CallbackQuery,
    state: FSMContext,
    admin_service: AdminService,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.update_data(admin_user_query=None)
    await render_user_list(
        message=callback.message,
        bot=None,
        state=state,
        admin_service=admin_service,
        page=0,
    )
    await callback.answer("Фильтр сброшен")


@router.message(AdminStates.waiting_for_user_query)
async def handle_user_search(
    message: Message,
    state: FSMContext,
    admin_service: AdminService,
    is_admin: bool,
):
    if not is_admin:
        return
    query = message.text.strip()
    await state.update_data(admin_user_query=query or None)
    await render_user_list(
        message=None,
        bot=message.bot,
        state=state,
        admin_service=admin_service,
        page=0,
    )
    await message.answer("🔎 Фильтр обновлён")
    await state.set_state(None)


@router.callback_query(F.data.startswith("admin_user:select:"))
async def admin_user_select(
    callback: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
    billing_service: BillingService,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, _, user_id_str = callback.data.split(":", 2)
    user = await user_service.get_by_id(int(user_id_str))
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    await render_user_detail(
        message=callback.message,
        bot=None,
        state=state,
        billing_service=billing_service,
        user=user,
    )
    await callback.answer()


@router.callback_query(F.data == "admin_user:back")
async def admin_user_back(
    callback: CallbackQuery,
    state: FSMContext,
    admin_service: AdminService,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    page = (await state.get_data()).get("admin_user_page", 0)
    await render_user_list(
        message=callback.message,
        bot=None,
        state=state,
        admin_service=admin_service,
        page=page,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user:custom:"))
async def admin_user_custom(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, _, user_id_str = callback.data.split(":", 2)
    await state.set_state(AdminStates.waiting_for_custom_amount)
    await state.update_data(custom_user_id=int(user_id_str))
    await callback.message.answer(
        "✏️ Укажите сумму и причину через пробел, например: <code>15 бонус за отзыв</code>"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_custom_amount)
async def admin_user_custom_amount(
    message: Message,
    state: FSMContext,
    billing_service: BillingService,
    user_service: UserService,
    is_admin: bool,
):
    if not is_admin:
        return
    data = await state.get_data()
    user_id = data.get("custom_user_id")
    if not user_id:
        await message.answer("Не удалось определить пользователя")
        await state.clear()
        return
    parts = message.text.split(maxsplit=1)
    try:
        amount = int(parts[0])
    except (ValueError, IndexError):
        await message.answer("Сумма должна быть целым числом")
        return
    reason = parts[1] if len(parts) > 1 else "Admin panel custom adjust"
    user = await user_service.get_by_id(user_id)
    if not user:
        await message.answer("Пользователь не найден")
        await state.clear()
        return
    await billing_service.adjust_balance(user, amount, reason)
    await message.answer(f"✅ Баланс обновлён. Новый баланс: {user.balance}")
    await render_user_detail(
        message=None,
        bot=message.bot,
        state=state,
        billing_service=billing_service,
        user=user,
    )
    await state.update_data(custom_user_id=None)
    await state.set_state(None)


@router.callback_query(F.data.startswith("admin_user_adjust:"))
async def admin_user_adjust(
    callback: CallbackQuery,
    billing_service: BillingService,
    user_service: UserService,
    state: FSMContext,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, _, payload = callback.data.split(":", 2)
    user_id_str, direction, amount_str = payload.split(":")
    user = await user_service.get_by_id(int(user_id_str))
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    amount = int(amount_str)
    if direction == "sub":
        amount = -amount
    await billing_service.adjust_balance(user, amount, "Admin panel quick adjust")
    await render_user_detail(
        message=callback.message,
        bot=None,
        state=state,
        billing_service=billing_service,
        user=user,
    )
    await callback.answer("Баланс обновлён")


@router.callback_query(F.data == "admin:requests")
async def admin_requests(
    callback: CallbackQuery,
    billing_service: BillingService,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    pending = await billing_service.list_pending_topups()
    if not pending:
        await callback.message.answer("📭 Нет заявок в ожидании")
    for request in pending:
        await callback.message.answer(
            "\n".join(
                [
                    f"📨 Заявка #{request.id}",
                    f"👤 Пользователь: {request.user_id}",
                    f"💳 Метод: {request.method.value}",
                    f"💰 Сумма: {request.amount}",
                    f"📌 Статус: {request.status.value}",
                ]
            ),
            reply_markup=manual_request_keyboard(request.id),
        )
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast(
    callback: CallbackQuery,
    state: FSMContext,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer("📣 Отправьте текст рассылки")
    await callback.answer()


@router.callback_query(F.data == "admin:export")
async def admin_export(
    callback: CallbackQuery,
    billing_service: BillingService,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    csv_content = await billing_service.export_transactions_csv()
    file = BufferedInputFile(csv_content.encode("utf-8"), filename="transactions.csv")
    await callback.message.answer_document(file, caption="📊 Экспорт операций")
    await callback.answer()


@router.callback_query(F.data == "admin:integrations")
async def admin_integrations(
    callback: CallbackQuery,
    integration_service: IntegrationService,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    lines = ["🧩 Статус интеграций:"]
    lines.append(
        "• Генератор изображений: "
        + ("✅ настроен" if integration_service.image_ready else "⚠️ не настроен")
    )
    if integration_service.image_webhook:
        lines.append(f"  ↳ Webhook: {integration_service.image_webhook}")
    lines.append(
        "• Криптобот: "
        + ("✅ токен указан" if integration_service.crypto_ready else "⚠️ токен отсутствует")
    )
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=admin_main_keyboard()
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    is_admin: bool,
):
    if not is_admin:
        return
    users = await user_service.list_all()
    count = 0
    for user in users:
        try:
            await message.bot.send_message(user.chat_id, message.text)
            count += 1
        except Exception:
            continue
    await message.answer(f"✅ Рассылка завершена. Отправлено {count} сообщений")
    await state.set_state(None)


@router.callback_query(F.data.startswith("admin_request:"))
async def process_request(
    callback: CallbackQuery,
    billing_service: BillingService,
    is_admin: bool,
):
    if not is_admin:
        await callback.answer("Нет доступа", show_alert=True)
        return
    _, action, req_id_str = callback.data.split(":", 2)
    try:
        req_id = int(req_id_str)
    except ValueError:
        await callback.answer("Ошибка", show_alert=True)
        return
    if action == "approve":
        status, amount = await billing_service.approve_manual_topup(req_id)
        if status == ManualTopUpStatus.APPROVED:
            await callback.message.answer(
                f"✅ Заявка #{req_id} подтверждена. Начислено {amount} токенов"
            )
        else:
            await callback.message.answer("Не удалось обработать заявку")
    elif action == "reject":
        await billing_service.reject_manual_topup(req_id)
        await callback.message.answer(f"🚫 Заявка #{req_id} отклонена")
    await callback.answer()


@router.message(Command("adjust"))
async def adjust_balance(
    message: Message,
    billing_service: BillingService,
    user_service: UserService,
    is_admin: bool,
):
    if not is_admin:
        return
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("Использование: /adjust <user_id> <amount> <reason>")
        return
    _, user_id_str, amount_str, reason = parts
    try:
        user_id = int(user_id_str)
        amount = int(amount_str)
    except ValueError:
        await message.answer("ID и сумма должны быть числами")
        return
    user = await user_service.get_by_id(user_id)
    if not user:
        await message.answer("Пользователь не найден")
        return
    await billing_service.adjust_balance(user, amount, reason)
    await message.answer(f"✅ Баланс обновлён. Новый баланс: {user.balance}")


@router.message(Command("health"))
async def health_check(message: Message, billing_service: BillingService, is_admin: bool):
    if not is_admin:
        return
    total = await billing_service.total_turnover()
    await message.answer(f"🩺 OK. Оборот операций: {total}")
