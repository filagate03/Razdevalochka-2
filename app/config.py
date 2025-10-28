from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # Telegram
    bot_token: str = Field(..., alias="BOT_TOKEN")
    admins_raw: str | List[int] | None = Field(default=None, alias="ADMINS")

    # Logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # Economy
    price_buy_rub: int = Field(10, alias="PRICE_BUY_RUB")
    price_sell_rub: int = Field(35, alias="PRICE_SELL_RUB")
    stars_packs_raw: str | List[Dict[str, Any]] | None = Field(default=None, alias="STARS_PACKS")

    # Image generation API
    image_api_token: str = Field(..., alias="IMAGE_API_TOKEN")
    image_api_url: str = Field("https://api.grtkniv.net", alias="IMAGE_API_URL")
    image_cost_photo_usd: float = Field(0.08, alias="IMAGE_COST_PHOTO_USD")
    image_cost_video_usd: float = Field(0.20, alias="IMAGE_COST_VIDEO_USD")
    image_webhook_url: str | None = Field(default=None, alias="IMAGE_WEBHOOK_URL")

    # CryptoBot
    crypto_bot_token: str = Field(..., alias="CRYPTO_BOT_TOKEN")
    crypto_webhook_url: str | None = Field(default=None, alias="CRYPTO_WEBHOOK_URL")

    # Database
    database_url: str = Field("sqlite+aiosqlite:///app.db", alias="DATABASE_URL")

    # Webhook configuration
    use_webhook: bool = Field(True, alias="USE_WEBHOOK")
    webhook_host: str = Field("", alias="WEBHOOK_HOST")
    webhook_path: str = Field("/webhook/telegram", alias="WEBHOOK_PATH")
    webhook_secret: str = Field("", alias="WEBHOOK_SECRET")

    # Referral configuration
    referral_bonus_tokens: int = Field(2, alias="REFERRAL_BONUS_TOKENS")
    referral_commission_percent: int = Field(10, alias="REFERRAL_COMMISSION_PERCENT")

    # Manual payment details
    payment_card_ru: str | None = Field(default=None, alias="PAYMENT_CARD_RU")
    payment_card_name: str | None = Field(default=None, alias="PAYMENT_CARD_NAME")
    payment_card_intl: str | None = Field(default=None, alias="PAYMENT_CARD_INTL")
    payment_card_intl_name: str | None = Field(default=None, alias="PAYMENT_CARD_INTL_NAME")
    crypto_wallet_btc: str | None = Field(default=None, alias="CRYPTO_WALLET_BTC")

    @property
    def admins(self) -> List[int]:
        return self._admins

    @property
    def stars_packs(self) -> List[Dict[str, Any]]:
        return self._stars_packs

    @field_validator("admins_raw")
    @classmethod
    def _parse_admins(cls, value: str | List[int] | None) -> List[int]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [int(v) for v in value]
        return [int(v.strip()) for v in str(value).split(",") if v.strip()]

    @field_validator("stars_packs_raw")
    @classmethod
    def _parse_stars_packs(cls, value: str | List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [dict(item) for item in parsed]
        except json.JSONDecodeError:
            pass
        # fallback to comma-separated tokens list
        packs: List[Dict[str, Any]] = []
        for chunk in str(value).split(","):
            if chunk.strip():
                packs.append({"tokens": int(chunk.strip())})
        return packs

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(self, "_admins", self._parse_admins(self.admins_raw))
        object.__setattr__(self, "_stars_packs", self._parse_stars_packs(self.stars_packs_raw))


@lru_cache()
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
