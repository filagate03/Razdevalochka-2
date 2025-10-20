from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..keyboards.common import generation_prompt_keyboard, portal_main_keyboard
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

    status_message = await message.answer(
        "🎨 Запускаем генерацию…",
        reply_markup=generation_prompt_keyboard(),
    )
    last_update = "🎨 Запускаем генерацию…"
    async for update in integration_service.simulate_generation(prompt):
        last_update = update
        await status_message.edit_text(update, reply_markup=generation_prompt_keyboard())
    await status_message.edit_text(
        f"{last_update}\n\nВыберите следующий шаг ниже.",
        reply_markup=portal_main_keyboard(),
    )

