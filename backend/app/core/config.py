"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import List, Optional
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "realestate"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = Field(..., min_length=32)
    api_v1_prefix: str = "/api/v1"

    # Moderation / Admin Approval
    auto_approve_listings: bool = False  # Require admin approval for all listings
    auto_approve_users: bool = False  # Require admin approval for all users

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = Field(..., min_length=1)
    postgres_db: str = "real_estate"
    database_url: Optional[str] = None

    @property
    def async_database_url(self) -> str:
        """Build async database URL."""
        if self.database_url:
            return self.database_url
        password = quote_plus(self.postgres_password)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Build sync database URL for Alembic."""
        password = quote_plus(self.postgres_password)
        return (
            f"postgresql://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: Optional[str] = None

    @property
    def redis_connection_url(self) -> str:
        """Build Redis connection URL."""
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Meilisearch
    meilisearch_host: str = "http://localhost:7700"
    meilisearch_api_key: str = ""

    # PR10 — read-path backend selector. "postgres" uses the
    # _apply_filters SQL path (source of truth); "meili" tries Meilisearch
    # first and falls back to Postgres on ANY failure. Default is
    # intentionally "postgres" so rollback is just an env-var flip.
    search_backend: str = Field(default="postgres", pattern="^(postgres|meili)$")

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Telegram Bot (single unified bot)
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_webhook_secret: str = ""

    # Admin notification chat IDs (comma-separated Telegram chat IDs)
    admin_chat_ids_str: str = Field("", alias="ADMIN_CHAT_IDS")

    @property
    def admin_chat_ids(self) -> list[int]:
        """Parse admin chat IDs from comma-separated string."""
        if not self.admin_chat_ids_str or not self.admin_chat_ids_str.strip():
            return []
        return [int(x.strip()) for x in self.admin_chat_ids_str.split(",") if x.strip()]

    # Telegram Parser
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_session_name: str = "realestate_parser"

    @field_validator("telegram_api_id", mode="before")
    @classmethod
    def parse_telegram_api_id(cls, v):
        """Parse telegram_api_id, allow empty string."""
        if v == "" or v is None:
            return None
        return int(v)

    # OpenAI
    openai_api_key: str = ""

    # Google Gemini
    gemini_api_key: str = ""

    # Translation provider: "openai", "gemini", or "ollama"
    translation_provider: str = "openai"

    # Ollama (local LLM via Docker)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # AWS S3 (optional - for cloud storage)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "eu-central-1"
    s3_bucket_name: str = "realestate-images"
    cloudfront_domain: str = ""

    # Local file uploads
    upload_dir: str = "uploads"

    # Sentry
    sentry_dsn: Optional[str] = None

    # CORS
    cors_origins: List[str] = ["https://t.me", "https://web.telegram.org"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # Admin Panel Credentials
    admin_username: str = Field(..., min_length=1)
    admin_password: str = Field(..., min_length=8)

    # Rate Limiting
    rate_limit_default: int = 100
    rate_limit_auth: int = 10
    rate_limit_search: int = 30

    # Exchange Rate
    exchange_rate_api_url: str = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"
    exchange_rate_fallback: int = 12800


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
