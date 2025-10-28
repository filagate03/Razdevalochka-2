from __future__ import annotations

from app.config import get_settings


def calculate_stars_price(tokens: int, discount: float = 0) -> int:
    settings = get_settings()
    price_rub = tokens * settings.price_sell_rub
    price_rub_discounted = price_rub * (1 - discount / 100)
    stars = int(price_rub_discounted / 1.8)
    return max(stars, 1)


def calculate_crypto_price(tokens: int, discount: float = 0) -> float:
    settings = get_settings()
    price_rub = tokens * settings.price_sell_rub
    price_rub_discounted = price_rub * (1 - discount / 100)
    price_usd = round(price_rub_discounted / 95, 2)
    return price_usd


def calculate_referral_bonus(tokens_purchased: int) -> int:
    return int(tokens_purchased * 0.10)


__all__ = [
    "calculate_stars_price",
    "calculate_crypto_price",
    "calculate_referral_bonus",
]
