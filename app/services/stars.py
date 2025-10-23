from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..config import get_settings


@dataclass(frozen=True)
class StarsPack:
    amount: int
    currency: str = "XTR"

    @property
    def payload(self) -> str:
        return f"pack:{self.amount}"

    def to_labeled_price(self) -> dict:
        return {
            "label": f"{self.amount} токенов",
            "amount": self.amount,
        }


class StarsService:
    def __init__(self, packs: Iterable[int] | None = None):
        settings = get_settings()
        pack_values = list(packs or settings.get_stars_packs_list())
        self._packs = [StarsPack(amount=p) for p in sorted(pack_values)]

    @property
    def packs(self) -> list[StarsPack]:
        return self._packs

    def get_pack(self, payload: str) -> StarsPack | None:
        if not payload.startswith("pack:"):
            return None
        try:
            amount = int(payload.split(":", 1)[1])
        except (IndexError, ValueError):
            return None
        for pack in self._packs:
            if pack.amount == amount:
                return pack
        return None


__all__ = ["StarsService", "StarsPack"]
