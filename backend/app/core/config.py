from __future__ import annotations

import json
from functools import lru_cache
from typing import List, Literal

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
    # Kept as a plain string: pydantic-settings JSON-decodes complex types from
    # env vars before validators run, so a comma-separated ALLOWED_ORIGINS
    # would crash a List[str] field. Use allowed_origins_list.
    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def allowed_origins_list(self) -> List[str]:
        raw = self.allowed_origins.strip()
        # Accept the JSON-array form the old List[str] field required, so
        # existing deployments don't silently get mangled origins.
        if raw.startswith("["):
            try:
                return [str(o).strip() for o in json.loads(raw)]
            except ValueError:
                pass
        return [o.strip() for o in raw.split(",") if o.strip()]

    # Database
    database_url: str = "postgresql+asyncpg://fifa_user:fifa_pass@localhost:5432/fifa2026"

    # Sync URL for Alembic (uses psycopg2 driver)
    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "")

    # Redis
    redis_url: str = "redis://localhost:6379/0"

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
