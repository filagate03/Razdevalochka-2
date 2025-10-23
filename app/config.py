from __future__ import annotations

from functools import lru_cache
from typing import List

import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
    )

    bot_token: str = Field(..., alias="BOT_TOKEN")
    admins: List[int] = Field(default_factory=list, alias="ADMINS")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    price_buy_rub: int = Field(18, alias="PRICE_BUY_RUB")
    price_sell_rub: int = Field(40, alias="PRICE_SELL_RUB")
    stars_packs: List[int] | str = Field(default_factory=lambda: [1, 3, 5, 10], alias="STARS_PACKS")

    image_api_token: str | None = Field(default=None, alias="IMAGE_API_TOKEN")
    image_webhook_url: str | None = Field(default=None, alias="IMAGE_WEBHOOK_URL")
    crypto_bot_token: str | None = Field(default=None, alias="CRYPTO_BOT_TOKEN")

    payment_card_ru: str = Field("", alias="PAYMENT_CARD_RU")
    payment_card_name: str = Field("", alias="PAYMENT_CARD_NAME")
    payment_card_intl: str = Field("", alias="PAYMENT_CARD_INTL")
    payment_card_intl_name: str = Field("", alias="PAYMENT_CARD_INTL_NAME")
    crypto_wallet_btc: str = Field("", alias="CRYPTO_WALLET_BTC")

    database_url: str = Field("sqlite+aiosqlite:///app.db", alias="DATABASE_URL")

    @field_validator("admins", mode="before")
    @classmethod
    def parse_admins(cls, value: str | List[int] | None) -> List[int]:
        if not value:
            return []
        if isinstance(value, list):
            return [int(v) for v in value]
        return [int(v.strip()) for v in str(value).split(",") if v.strip()]

    @field_validator("stars_packs", mode="before")
    @classmethod
    def parse_stars(cls, value: str | List[int] | None) -> List[int]:
        if value is None:
            return [1, 3, 5, 10]
        if isinstance(value, list):
            return [int(v) for v in value]
        text = str(value).strip()
        if not text:
            return [1, 3, 5, 10]
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = []
            else:
                if isinstance(parsed, list):
                    return [int(v) for v in parsed]
        return [int(v.strip()) for v in text.split(",") if v.strip()]

    def get_stars_packs_list(self) -> List[int]:
        if isinstance(self.stars_packs, list):
            return self.stars_packs
        if isinstance(self.stars_packs, str):
            text = self.stars_packs.strip()
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = []
                else:
                    if isinstance(parsed, list):
                        return [int(v) for v in parsed]
            return [int(v.strip()) for v in text.split(",") if v.strip()]
        return [1, 3, 5, 10]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
