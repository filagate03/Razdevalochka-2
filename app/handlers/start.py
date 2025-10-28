from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.repositories import UserRepository

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, user_repo: UserRepository) -> None:
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        return
    await user_repo.get_or_create_user(
        message.from_user.id,
        message.from_user.username if message.from_user else None,
    )
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Отправьте фото для обработки или используйте /buy для пополнения токенов."
    )
