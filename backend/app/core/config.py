"""Application configuration using Pydantic Settings."""

from datetime import datetime
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
    # Block D D1: Mini App URL that the Menu Button opens (e.g.
    # "https://pana.uz"). When empty the Menu Button setup is
    # skipped silently — useful for dev environments without a TWA host.
    telegram_webapp_url: str = ""

    # Block D D4 (D4-Q1): subscription test-period flag.
    # During Phase-1 the Cabinet subscription is open to all sellers
    # (autopost, multi-phone, etc.). Flip this to False to enforce the
    # paid-only check via ``services.subscriptions``. Per DECISION_MATRIX,
    # the boundary date is product-controlled, not code-controlled.
    # PRODUCTION-SAFE DEFAULT: True (matches Phase-1 launch policy).
    cabinet_subscription_open_to_all: bool = True

    # Block D D1 — safety net for the uz_cyrl bot translations. The
    # initial file was produced by programmatic transliteration of
    # uz.json; quality is acceptable but not native-reviewed. Set this
    # to True to force every uz_cyrl bot string to fall back to ru
    # without a code deploy. Default False — uz_cyrl serves uz_cyrl.
    i18n_uz_cyrl_bot_fallback_to_ru: bool = False

    # Block F F1 — DRAFT listings older than this are purged by the
    # daily `purge_abandoned_drafts` Celery beat task (PR-F1a).
    f1_draft_lifetime_days: int = 7

    # Block F F5 — daily OpenAI spend ceiling (USD). When exceeded the
    # worker falls back to the structured-params template instead of
    # calling the API. Cap resets at UTC midnight.
    f5_openai_daily_budget_usd: int = 50

    # Block F F5 — quality threshold for the hourly admin alert.
    # Bad-feedback rate over rolling 24h that triggers a Telegram alert.
    f5_alert_bad_feedback_rate: float = 0.10

    # Block F F5 — p95 generation duration alert threshold (ms).
    f5_alert_p95_duration_ms: int = 8000

    # Block F F3 — public SEO host. Used for canonical URLs in HTML
    # rendering + sitemap absolute URLs. Empty in dev = SEO routes
    # return relative URLs (harmless for testing).
    f3_public_web_host: str = "https://pana.uz"

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

    # Block C — Test-period / monetization triggers (decision-pass G1 / C1).
    # ALL prices are in smallest-currency-unit per MONEY_STORAGE_DECISION:
    # for UZS, that's whole UZS (no kopeks).
    test_period_active: bool = True
    test_period_started_at: Optional[datetime] = None  # defaults to deploy time
    monetization_trigger_listings: int = 5_000
    monetization_trigger_days: int = 60
    free_listings_per_seller: int = 2
    extra_listing_price_uzs: int = 25_000
    cabinet_subscription_price_uzs: int = 99_000

    # Block C — Multi-phone (C4)
    multi_phone_enabled: bool = True
    multi_phone_max_additional: int = 3  # primary + 3 = 4 total

    # Block C — Payment provider env-var slots (C3 PR4 — Phase 2 will populate).
    # Empty in MVP; production secrets via secret manager.
    click_merchant_id: str = ""
    click_secret: str = ""
    click_webhook_url: str = ""
    payme_merchant_id: str = ""
    payme_key: str = ""
    payme_webhook_url: str = ""

    # Block C — C5 multi-account-detection signal thresholds (decision #28).
    similar_name_edit_distance_threshold: int = 2
    similar_name_suffix_chars: int = 4
    similar_name_registration_window_days: int = 7


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
