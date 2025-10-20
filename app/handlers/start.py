from __future__ import annotations

from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..config import get_settings
from ..keyboards.common import (
    back_to_main_keyboard,
    generation_prompt_keyboard,
    portal_main_keyboard,
)
from ..services.admin import AdminService
from ..services.billing import BillingService
from ..services.integrations import IntegrationService

router = Router()


class PortalStates(StatesGroup):
    waiting_prompt = State()


def _home_text() -> str:
    return (
        "✨ Добро пожаловать в инфраструктуру токенов!\n"
        "Все разделы открываются в одном сообщении — просто нажимайте кнопки ниже."
    )


async def _respond(
    message: Message,
    *,
    text: str,
    markup,
    edit: bool = False,
) -> None:
    try:
        if edit:
            await message.edit_text(text, reply_markup=markup)
        else:
            await message.answer(text, reply_markup=markup)
    except TelegramBadRequest:
        await message.answer(text, reply_markup=markup)


async def _ensure_user(
    *,
    billing_service: BillingService,
    admin_service: AdminService,
    chat_id: int,
    username: str | None,
) -> None:
    user = await billing_service.get_or_create_user(chat_id, username)
    await admin_service.sync_user_record(user)


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    billing_service: BillingService,
    admin_service: AdminService,
    state: FSMContext,
):
    await state.clear()
    await _ensure_user(
        billing_service=billing_service,
        admin_service=admin_service,
        chat_id=message.chat.id,
        username=message.from_user.username if message.from_user else None,
    )
    await _respond(message, text=_home_text(), markup=portal_main_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "ℹ️ Основные действия теперь доступны через кнопки в /start:\n"
        "• 💰 Баланс — текущее количество токенов\n"
        "• 🛒 Пополнить — Stars, ручные заявки и внешняя ссылка\n"
        "• 🧾 История — последние операции\n"
        "• 🎨 Генерация — демо сценарий с обновлением одного сообщения\n"
        "• 🆘 Поддержка — контакты команды\n"
        "Команды /pricing и /buy также работают для быстрого доступа."
    )
    await message.answer(text)


@router.callback_query(F.data == "portal:home")
async def portal_home(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _respond(callback.message, text=_home_text(), markup=portal_main_keyboard(), edit=True)
    await callback.answer()


@router.callback_query(F.data == "portal:balance")
async def portal_balance(
    callback: CallbackQuery,
    billing_service: BillingService,
    admin_service: AdminService,
):
    await _ensure_user(
        billing_service=billing_service,
        admin_service=admin_service,
        chat_id=callback.from_user.id,
        username=callback.from_user.username,
    )
    user = await billing_service.get_user(callback.from_user.id)
    balance = user.balance if user else 0
    text = f"💼 Ваш баланс: <b>{balance}</b> токенов"
    await _respond(callback.message, text=text, markup=back_to_main_keyboard(), edit=True)
    await callback.answer()


@router.callback_query(F.data == "portal:history")
async def portal_history(
    callback: CallbackQuery,
    billing_service: BillingService,
    admin_service: AdminService,
):
    await _ensure_user(
        billing_service=billing_service,
        admin_service=admin_service,
        chat_id=callback.from_user.id,
        username=callback.from_user.username,
    )
    user = await billing_service.get_user(callback.from_user.id)
    if not user:
        text = "📭 История пуста. Пополните счёт, чтобы увидеть операции."
    else:
        transactions = await billing_service.list_user_history(user, limit=10)
        if not transactions:
            text = "📭 История пуста. Пополните счёт, чтобы увидеть операции."
        else:
            lines = ["🧾 Последние операции:"]
            for txn in transactions:
                sign = "➕" if txn.amount > 0 else "➖"
                lines.append(
                    f"{txn.created_at:%d.%m %H:%M} · {sign}{abs(txn.amount)} · {txn.type.value}"
                )
            text = "\n".join(lines)
    await _respond(callback.message, text=text, markup=back_to_main_keyboard(), edit=True)
    await callback.answer()


@router.callback_query(F.data == "portal:pricing")
async def portal_pricing(callback: CallbackQuery):
    settings = get_settings()
    text = (
        "💵 Справочная информация:\n"
        f"• Покупка: {settings.price_buy_rub}₽ за токен\n"
        f"• Продажа: {settings.price_sell_rub}₽ за токен\n"
        "Точные значения зависят от выбранного способа оплаты."
    )
    await _respond(callback.message, text=text, markup=back_to_main_keyboard(), edit=True)
    await callback.answer()


@router.callback_query(F.data == "portal:support")
async def portal_support(callback: CallbackQuery):
    text = (
        "🤝 Поддержка на связи!\n"
        "Пишите менеджерам: @hunt_tg или @berkyt."
    )
    await _respond(callback.message, text=text, markup=back_to_main_keyboard(), edit=True)
    await callback.answer()


@router.callback_query(F.data == "portal:generate")
async def portal_generate(
    callback: CallbackQuery,
    integration_service: IntegrationService,
    state: FSMContext,
):
    if not integration_service.image_ready:
        await callback.answer("Интеграция генерации не настроена", show_alert=True)
        return
    await state.set_state(PortalStates.waiting_prompt)
    await state.update_data(
        portal_message_id=callback.message.message_id,
        portal_chat_id=callback.message.chat.id,
    )
    await _respond(
        callback.message,
        text=(
            "🎨 Отправьте описание изображения следующим сообщением.\n"
            "Мы покажем прогресс прямо здесь."
        ),
        markup=generation_prompt_keyboard(),
        edit=True,
    )
    await callback.answer("Жду описание")


@router.message(PortalStates.waiting_prompt)
async def handle_generation_prompt(
    message: Message,
    state: FSMContext,
    integration_service: IntegrationService,
):
    prompt = (message.text or "").strip()
    if not prompt:
        await message.answer("Пожалуйста, отправьте текстовое описание.")
        return
    data = await state.get_data()
    portal_chat_id = data.get("portal_chat_id", message.chat.id)
    portal_message_id = data.get("portal_message_id")

    if not portal_message_id:
        sent = await message.answer("🎨 Запрос принят, готовим генерацию…", reply_markup=generation_prompt_keyboard())
        portal_message_id = sent.message_id
        portal_chat_id = sent.chat.id
        await state.update_data(portal_message_id=portal_message_id, portal_chat_id=portal_chat_id)

    progress_markup = generation_prompt_keyboard()
    last_text = ""
    async for update in integration_service.simulate_generation(prompt):
        last_text = update
        try:
            await message.bot.edit_message_text(
                chat_id=portal_chat_id,
                message_id=portal_message_id,
                text=update,
                reply_markup=progress_markup,
            )
        except TelegramBadRequest:
            break

    final_text = f"{last_text}\n\nВыберите следующий шаг ниже."
    try:
        await message.bot.edit_message_text(
            chat_id=portal_chat_id,
            message_id=portal_message_id,
            text=final_text,
            reply_markup=portal_main_keyboard(),
        )
    except TelegramBadRequest:
        await message.answer(final_text, reply_markup=portal_main_keyboard())
    await state.clear()
