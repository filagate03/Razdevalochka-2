from __future__ import annotations

import asyncio
from typing import AsyncIterator


class IntegrationService:
    def __init__(
        self,
        *,
        image_token: str | None = None,
        image_webhook: str | None = None,
        crypto_bot_token: str | None = None,
    ) -> None:
        self._image_token = image_token
        self._image_webhook = image_webhook
        self._crypto_bot_token = crypto_bot_token

    @property
    def image_ready(self) -> bool:
        return bool(self._image_token)

    @property
    def image_webhook(self) -> str | None:
        return self._image_webhook

    @property
    def crypto_ready(self) -> bool:
        return bool(self._crypto_bot_token)

    async def simulate_generation(self, prompt: str) -> AsyncIterator[str]:
        yield "🌀 Отправляем запрос в генератор…"
        await asyncio.sleep(1)
        yield "🎨 Изображение создаётся, подождите пару секунд…"
        await asyncio.sleep(1)
        result_hint = (
            "✅ Готово! Замените этот шаг реальным вызовом API и выдачей ссылки на файл."
        )
        yield f"{result_hint}\n\nЗапрос: <i>{prompt}</i>"


__all__ = ["IntegrationService"]
