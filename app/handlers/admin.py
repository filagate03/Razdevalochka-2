from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.repositories import UserRepository

router = Router()


@router.message(Command("add_admin"))
async def add_admin(message: Message, user_repo: UserRepository, is_admin: bool) -> None:
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Использование: /add_admin <chat_id>")
        return
    try:
        chat_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат chat_id")
        return
    user = await user_repo.get_by_chat_id(chat_id)
    if not user:
        await message.answer("❌ Пользователь не найден. Он должен запустить бота.")
        return
    await user_repo.set_admin(chat_id, True)
    await message.answer(f"✅ Пользователь {chat_id} назначен администратором")


@router.message(Command("remove_admin"))
async def remove_admin(message: Message, user_repo: UserRepository, is_admin: bool) -> None:
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("❌ Использование: /remove_admin <chat_id>")
        return
    try:
        chat_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат chat_id")
        return
    if chat_id == message.from_user.id:
        await message.answer("❌ Нельзя удалить себя из администраторов")
        return
    await user_repo.set_admin(chat_id, False)
    await message.answer(f"✅ Пользователь {chat_id} удален из администраторов")


@router.message(Command("admins"))
async def list_admins(message: Message, user_repo: UserRepository, is_admin: bool) -> None:
    if not is_admin:
        await message.answer("❌ У вас нет прав администратора")
        return
    admins = await user_repo.get_all_admins()
    if not admins:
        await message.answer("📋 Администраторов не найдено")
        return
    lines = ["📋 Список администраторов:"]
    for admin in admins:
        username = f"@{admin.username}" if admin.username else "без username"
        lines.append(f"• {admin.chat_id} ({username})")
    await message.answer("\n".join(lines))
