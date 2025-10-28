from __future__ import annotations

import logging
from typing import Dict, Optional

from aiocryptopay import AioCryptoPay, Networks

from app.config import get_settings


logger = logging.getLogger(__name__)


class CryptoPaymentService:
    """Wrapper around :mod:`aiocryptopay` with graceful error handling."""

    def __init__(self) -> None:
        settings = get_settings()
        self._token = settings.crypto_bot_token
        self._network = Networks.MAIN_NET

    def _new_client(self) -> AioCryptoPay:
        return AioCryptoPay(token=self._token, network=self._network)

    async def create_invoice(
        self,
        amount: float,
        currency: str = "USDT",
        description: str = "",
    ) -> Optional[Dict[str, str]]:
        client = self._new_client()
        try:
            invoice = await client.create_invoice(
                asset=currency,
                amount=amount,
                description=description,
                expires_in=3600,
            )
        except Exception:
            logger.exception("CryptoPay: failed to create invoice")
            return None
        finally:
            await client.close()

        if not invoice:
            return None

        return {
            "invoice_id": int(invoice.invoice_id),
            "amount": float(invoice.amount),
            "currency": invoice.asset,
            "pay_url": invoice.bot_invoice_url,
        }

    async def check_invoice(self, invoice_id: int) -> bool:
        client = self._new_client()
        try:
            invoices = await client.get_invoices(invoice_ids=[invoice_id])
        except Exception:
            logger.exception("CryptoPay: failed to fetch invoices")
            return False
        finally:
            await client.close()

        if not invoices:
            return False

        status = getattr(invoices[0], "status", None)
        return status == "paid"

    async def get_app_info(self) -> Optional[Dict[str, str]]:
        client = self._new_client()
        try:
            app = await client.get_me()
        except Exception:
            logger.exception("CryptoPay: failed to load app info")
            return None
        finally:
            await client.close()

        return {
            "name": getattr(app, "name", ""),
            "payment_bot": getattr(app, "payment_processing_bot_username", ""),
        }


__all__ = ["CryptoPaymentService"]
