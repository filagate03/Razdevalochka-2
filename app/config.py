from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    bot_token: str = Field(..., env="BOT_TOKEN")
    admins: List[int] = Field(default_factory=list, env="ADMINS")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    price_buy_rub: int = Field(18, env="PRICE_BUY_RUB")
    price_sell_rub: int = Field(40, env="PRICE_SELL_RUB")
    stars_packs: List[int] = Field(default_factory=lambda: [1, 3, 5, 10], env="STARS_PACKS")

    database_url: str = Field("sqlite+aiosqlite:///./app.db", env="DATABASE_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("admins", pre=True)
    def parse_admins(cls, value: str | List[int] | None) -> List[int]:
        if not value:
            return []
        if isinstance(value, list):
            return [int(v) for v in value]
        return [int(v.strip()) for v in str(value).split(",") if v.strip()]

    @validator("stars_packs", pre=True)
    def parse_stars(cls, value: str | List[int]) -> List[int]:
        if isinstance(value, list):
            return [int(v) for v in value]
        return [int(v.strip()) for v in str(value).split(",") if v.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
