from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..services.integrations import IntegrationService

router = Router()


@router.message(Command("generate"))
async def generate_demo(message: Message, integration_service: IntegrationService):
    args = message.text.split(maxsplit=1) if message.text else []
    prompt = args[1] if len(args) == 2 else "demo"

    if not integration_service.image_ready:
        await message.answer(
            "⚠️ Токен генератора изображений не настроен. Укажите IMAGE_API_TOKEN в .env, "
            "чтобы включить интеграцию."
        )
        return

    status_message = await message.answer("🎨 Запускаем генерацию…")
    async for update in integration_service.simulate_generation(prompt):
        await status_message.edit_text(update)

