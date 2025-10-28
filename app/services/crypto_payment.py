from __future__ import annotations

import logging
from typing import Dict, Optional

from aiocryptopay import AioCryptoPay, Networks

from app.config import get_settings


logger = logging.getLogger(__name__)


class CryptoPaymentService:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AioCryptoPay(token=settings.crypto_bot_token, network=Networks.MAIN_NET)

    async def create_invoice(self, amount: float, currency: str = "USDT", description: str = "") -> Optional[Dict[str, str]]:
        try:
            invoice = await self._client.create_invoice(asset=currency, amount=amount, description=description, expires_in=3600)
            return {
                "invoice_id": invoice.invoice_id,
                "amount": invoice.amount,
                "currency": invoice.asset,
                "pay_url": invoice.bot_invoice_url,
            }
        except Exception:  # pragma: no cover
            logger.exception("Failed to create CryptoBot invoice")
            return None

    async def check_invoice(self, invoice_id: int) -> bool:
        try:
            invoices = await self._client.get_invoices(invoice_ids=[invoice_id])
            if invoices:
                return invoices[0].status == "paid"
        except Exception:  # pragma: no cover
            logger.exception("Failed to check CryptoBot invoice %s", invoice_id)
        return False

    async def get_app_info(self) -> Optional[Dict[str, str]]:
        try:
            info = await self._client.get_me()
            return {"name": info.name, "payment_bot": info.payment_processing_bot_username}
        except Exception:  # pragma: no cover
            logger.exception("Failed to get CryptoBot app info")
            return None


__all__ = ["CryptoPaymentService"]
