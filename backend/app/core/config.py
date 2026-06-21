from __future__ import annotations

from functools import lru_cache
from typing import List, Literal, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    secret_key: str = "insecure-dev-key"
    api_v1_prefix: str = "/api/v1"
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, v: Union[str, list]) -> List[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    # Database
    database_url: str = "postgresql+asyncpg://fifa_user:fifa_pass@localhost:5432/fifa2026"

    # Sync URL for Alembic (uses psycopg2 driver)
    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_checkpoint_url: str = "redis://localhost:6379/1"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection_match_reports: str = "match_reports"
    chroma_collection_team_profiles: str = "team_profiles"
    chroma_collection_wc_history: str = "world_cup_history"

    # LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    # Rate limits
    rate_limit_per_minute: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
