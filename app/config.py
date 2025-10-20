from __future__ import annotations

from functools import lru_cache
from typing import List

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
    stars_packs: List[int] = Field(default_factory=lambda: [1, 3, 5, 10], alias="STARS_PACKS")

    database_url: str = Field("sqlite+aiosqlite:///./app.db", alias="DATABASE_URL")

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
    def parse_stars(cls, value: str | List[int]) -> List[int]:
        if isinstance(value, list):
            return [int(v) for v in value]
        return [int(v.strip()) for v in str(value).split(",") if v.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
