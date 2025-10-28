from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import aiohttp

from app.config import get_settings


logger = logging.getLogger(__name__)


class CryptoPaymentService:
    """Minimal async client for the CryptoBot Crypto Pay API."""

    _BASE_URL = "https://pay.crypt.bot/api"

    def __init__(self) -> None:
        settings = get_settings()
        self._token = settings.crypto_bot_token

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Crypto-Pay-API-Token": self._token,
        }

    async def _post(self, path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a POST request to the Crypto Pay API."""
        url = f"{self._BASE_URL}{path}"
        timeout = aiohttp.ClientTimeout(total=15)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=self._headers()) as response:
                    data = await response.json(content_type=None)
        except Exception:  # pragma: no cover - network/serialization failures
            logger.exception("CryptoPay API request failed: %s", path)
            return None

        if not data or not data.get("ok"):
            logger.error("CryptoPay API responded with error on %s: %s", path, data)
            return None

        result = data.get("result")
        if not isinstance(result, dict):
            logger.error("CryptoPay API unexpected payload on %s: %s", path, data)
            return None
        return result

    async def create_invoice(
        self,
        amount: float,
        currency: str = "USDT",
        description: str = "",
    ) -> Optional[Dict[str, str]]:
        payload: Dict[str, Any] = {
            "asset": currency,
            "amount": amount,
            "description": description,
            "expires_in": 3600,
        }
        result = await self._post("/createInvoice", payload)
        if not result:
            return None

        try:
            return {
                "invoice_id": str(result["invoice_id"]),
                "amount": str(result["amount"]),
                "currency": str(result["asset"]),
                "pay_url": str(result["bot_invoice_url"]),
            }
        except KeyError:  # pragma: no cover - schema mismatch
            logger.error("Unexpected invoice payload: %s", result)
            return None

    async def check_invoice(self, invoice_id: int) -> bool:
        payload = {"invoice_ids": [invoice_id]}
        result = await self._post("/getInvoices", payload)
        if not result:
            return False

        invoices = result.get("items")
        if isinstance(invoices, list) and invoices:
            status = invoices[0].get("status")
            return status == "paid"
        logger.error("Invoice %s not found in response: %s", invoice_id, result)
        return False

    async def get_app_info(self) -> Optional[Dict[str, str]]:
        result = await self._post("/getMe", {})
        if not result:
            return None

        return {
            "name": str(result.get("name", "")),
            "payment_bot": str(result.get("payment_processing_bot_username", "")),
        }


__all__ = ["CryptoPaymentService"]
