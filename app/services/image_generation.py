from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional

import aiohttp

from app.config import get_settings


logger = logging.getLogger(__name__)


class ImageGenerationService:
    """Client for the grtkniv.net image generation API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.image_api_url.rstrip("/")
        self._token = settings.image_api_token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def get_collections(self) -> Optional[List[Dict[str, str]]]:
        url = f"{self._base_url}/api/imageGenerations/collections"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("Loaded %s image collections", len(data))
                        return data
                    logger.error("Collections request failed: %s %s", response.status, await response.text())
            except Exception:  # pragma: no cover - network errors
                logger.exception("Failed to load collections")
        return None

    async def _post(self, endpoint: str, payload: Dict[str, str]) -> Optional[Dict[str, str]]:
        url = f"{self._base_url}{endpoint}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url,
                    headers=self._headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    logger.error("%s request failed: %s %s", endpoint, response.status, await response.text())
            except Exception:  # pragma: no cover
                logger.exception("Request to %s failed", endpoint)
        return None

    async def undress(self, photo_url: str, collection_id: str | None = None) -> Optional[Dict[str, str]]:
        payload: Dict[str, str] = {"photo_url": photo_url}
        if collection_id:
            payload["collection_id"] = collection_id
        return await self._post("/api/imageGenerations/undress", payload)

    async def change_position(self, photo_url: str, position: str) -> Optional[Dict[str, str]]:
        payload = {"photo_url": photo_url, "position": position}
        return await self._post("/api/imageGenerations/position", payload)

    async def check_status(self, task_id: str) -> Optional[Dict[str, str]]:
        url = f"{self._base_url}/api/imageGenerations/status/{task_id}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        return await response.json()
                    logger.error("Status request failed: %s %s", response.status, await response.text())
            except Exception:  # pragma: no cover
                logger.exception("Failed to check status for %s", task_id)
        return None

    async def wait_for_completion(
        self,
        task_id: str,
        *,
        max_attempts: int = 60,
        interval: int = 5,
    ) -> Optional[Dict[str, str]]:
        for attempt in range(max_attempts):
            status = await self.check_status(task_id)
            if status:
                state = status.get("status")
                if state in {"completed", "failed"}:
                    return status
            await asyncio.sleep(interval)
        return {"status": "failed", "error": "Timeout"}


__all__ = ["ImageGenerationService"]
