from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import Message

from app.repositories import GenerationTaskRepository, TransactionRepository, UserRepository
from app.services.image_generation import ImageGenerationService

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.photo)
async def handle_photo(
    message: Message,
    user_repo: UserRepository,
    transaction_repo: TransactionRepository,
    task_repo: GenerationTaskRepository,
) -> None:
    user = await user_repo.get_or_create_user(
        message.from_user.id,
        message.from_user.username if message.from_user else None,
    )
    if user.balance <= 0:
        await message.answer("❌ Недостаточно токенов. Используйте /buy")
        return

    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"

    progress = await message.answer("⏳ Обрабатываю фото...")

    service = ImageGenerationService()
    try:
        response = await service.undress(photo_url)
    except Exception:
        logger.exception("Failed to start generation")
        await progress.edit_text("❌ Ошибка API. Попробуйте позже.")
        return

    if not response or "task_id" not in response:
        await progress.edit_text("❌ Ошибка при запуске генерации")
        return

    task_id = response["task_id"]
    await task_repo.create_task(user_id=user.id, task_id=task_id, photo_url=photo_url)
    await user_repo.update_balance(user.chat_id, -1, reason="Generation started")
    await transaction_repo.create(
        user_id=user.id,
        amount=-1,
        reason="generation",
        payment_method="balance",
        external_id=task_id,
    )

    result = await service.wait_for_completion(task_id)
    if not result:
        await progress.edit_text("❌ Превышено время ожидания. Токен возвращен.")
        await user_repo.update_balance(user.chat_id, 1, reason="Generation timeout refund")
        await task_repo.update_status(task_id, status="failed", error_message="timeout")
        return

    status = result.get("status")
    if status == "completed":
        await task_repo.update_status(task_id, status="completed", result_url=result.get("result_url"))
        await progress.delete()
        await message.answer_photo(result.get("result_url"), caption="✅ Готово!")
    else:
        error = result.get("error", "unknown error")
        await task_repo.update_status(task_id, status="failed", error_message=error)
        await user_repo.update_balance(user.chat_id, 1, reason="Generation failed refund")
        await progress.edit_text(f"❌ Ошибка генерации: {error}")
