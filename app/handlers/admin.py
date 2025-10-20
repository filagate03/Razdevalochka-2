from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from ..config import get_settings
from ..keyboards.admin import admin_main_keyboard, manual_request_keyboard
from ..models import ManualTopUpStatus
from ..services.admin import AdminService
from ..services.billing import BillingService
from ..services.users import UserService

router = Router()


class AdminStates(StatesGroup):
    waiting_for_user_query = State()
    waiting_for_broadcast = State()


def is_admin(message: Message) -> bool:
    settings = get_settings()
    return bool(message.from_user and message.from_user.id in settings.admins)


@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    await state.clear()
    await message.answer("Админ-панель:", reply_markup=admin_main_keyboard())


@router.callback_query(F.data.startswith("admin:"))
async def admin_menu(
    callback: CallbackQuery,
    state: FSMContext,
    billing_service: BillingService,
):
    if not is_admin(callback.message):
        await callback.answer("Нет доступа", show_alert=True)
        return
    action = callback.data.split(":", 1)[1]
    if action == "users":
        await state.set_state(AdminStates.waiting_for_user_query)
        await callback.message.answer("Введите username или ID пользователя")
    elif action == "requests":
        pending = await billing_service.list_pending_topups()
        if not pending:
            await callback.message.answer("Нет заявок в ожидании")
        for request in pending:
            await callback.message.answer(
                f"Заявка #{request.id}\nПользователь: {request.user_id}\nМетод: {request.method.value}\nСумма: {request.amount}\nСтатус: {request.status.value}",
                reply_markup=manual_request_keyboard(request.id),
            )
    elif action == "broadcast":
        await state.set_state(AdminStates.waiting_for_broadcast)
        await callback.message.answer("Отправьте текст рассылки")
    elif action == "export":
        csv_content = await billing_service.export_transactions_csv()
        file = BufferedInputFile(csv_content.encode("utf-8"), filename="transactions.csv")
        await callback.message.answer_document(file, caption="Экспорт операций")
    await callback.answer()


@router.message(AdminStates.waiting_for_user_query)
async def process_user_query(
    message: Message,
    state: FSMContext,
    billing_service: BillingService,
    admin_service: AdminService,
):
    if not is_admin(message):
        return
    query = message.text.strip()
    user = await admin_service.find_user(query)
    if not user:
        await message.answer("Пользователь не найден")
        return
    transactions = await billing_service.list_user_history(user)
    lines = [
        f"ID: {user.id}",
        f"Chat ID: {user.chat_id}",
        f"Username: @{user.username}" if user.username else "Username: —",
        f"Баланс: {user.balance}",
        "Последние операции:",
    ]
    for txn in transactions[:5]:
        sign = "+" if txn.amount > 0 else ""
        lines.append(f"{txn.created_at:%Y-%m-%d %H:%M} | {sign}{txn.amount} | {txn.type.value}")
    await message.answer("\n".join(lines))
    await message.answer("Используйте команду /adjust <user_id> <amount> <reason> для корректировки баланса")
    await state.clear()


@router.message(Command("adjust"))
async def adjust_balance(
    message: Message,
    billing_service: BillingService,
    user_service: UserService,
):
    if not is_admin(message):
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
    await message.answer(f"Баланс обновлен. Новый баланс: {user.balance}")


@router.callback_query(F.data.startswith("admin_request:"))
async def process_request(
    callback: CallbackQuery,
    billing_service: BillingService,
):
    if not is_admin(callback.message):
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
            await callback.message.answer(f"Заявка #{req_id} подтверждена. Начислено {amount} токенов")
        else:
            await callback.message.answer("Заявка не найдена")
    elif action == "reject":
        await billing_service.reject_manual_topup(req_id)
        await callback.message.answer(f"Заявка #{req_id} отклонена")
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(
    message: Message,
    state: FSMContext,
    user_service: UserService,
):
    if not is_admin(message):
        return
    users = await user_service.list_all()
    count = 0
    for user in users:
        try:
            await message.bot.send_message(user.chat_id, message.text)
            count += 1
        except Exception:
            continue
    await message.answer(f"Рассылка завершена. Отправлено {count} сообщений")
    await state.clear()


@router.message(Command("health"))
async def health_check(message: Message, billing_service: BillingService):
    if not is_admin(message):
        return
    total = await billing_service.total_turnover()
    await message.answer(f"OK. Оборот операций: {total}")
