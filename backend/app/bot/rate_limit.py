"""Block D (FU3) — admin-managed, Redis-backed per-user rate limiter.

The two spammy bot surfaces — in-chat search (``/search`` + free text) and
Inline Mode — are throttled per Telegram user so one person can't hammer the
search backend (parser + Meilisearch) faster than a human ever would.

Design:

* **Fixed window in Redis.** ``INCR`` + ``EXPIRE`` on the first hit; one
  round-trip in the common case. Good enough for abuse control — we don't
  need the precision (or cost) of a sliding log.
* **Admin-managed config.** Caps, on/off toggles and the "too many requests"
  message live in the ``bot_rate_limit_settings`` table (one row), edited from
  the admin panel. The bot reads them through a short-TTL Redis cache
  (``bot:rl:config``) so an edit propagates within ~a minute even across the
  separate bot process; the admin API also write-throughs that cache for
  instant effect.
* **Fail-open.** Redis is non-fatal for the bot (see ``bot/main.py`` health
  probe). Any Redis/DB error in the limiter lets the request through rather
  than locking every user out — availability beats strict enforcement here.
* **No middleware.** The bot has no middleware catalog and inline handlers run
  without the DB-session middleware, so each call site invokes :func:`hit`
  directly and the config loader opens its own session when it needs the DB.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass

from app.db.redis import get_redis

logger = logging.getLogger(__name__)

# Hardcoded last-resort defaults. Mirror the migration seed so the limiter
# still behaves sanely if both Redis and the DB row are unreachable.
DEFAULT_LIMIT_MESSAGES: dict[str, str] = {
    "ru": "Слишком много запросов. Подождите минуту и попробуйте снова.",
    "uz": "So'rovlar juda ko'p. Bir daqiqa kuting va qayta urinib ko'ring.",
    "uz_cyrl": "Сўровлар жуда кўп. Бир дақиқа кутиб, қайта уриниб кўринг.",
}

# Redis key for the cached config blob; TTL bounds staleness if a write-through
# from the admin API is ever missed (e.g. admin process couldn't reach Redis).
_CONFIG_CACHE_KEY = "bot:rl:config"
_CONFIG_CACHE_TTL = 60  # seconds

# Per-user fixed-window counter key, namespaced by scope ("search" / "inline").
_HIT_KEY = "bot:rl:{scope}:{user_id}"


@dataclass(frozen=True)
class RateLimitConfig:
    """Snapshot of the admin-managed limiter settings."""

    search_enabled: bool = True
    search_limit: int = 10
    search_window_sec: int = 60
    inline_enabled: bool = True
    inline_limit: int = 30
    inline_window_sec: int = 60
    limit_message_ru: str = DEFAULT_LIMIT_MESSAGES["ru"]
    limit_message_uz: str = DEFAULT_LIMIT_MESSAGES["uz"]
    limit_message_uz_cyrl: str = DEFAULT_LIMIT_MESSAGES["uz_cyrl"]

    def for_scope(self, scope: str) -> tuple[bool, int, int]:
        """Return ``(enabled, limit, window_sec)`` for ``"search"`` / ``"inline"``."""
        if scope == "inline":
            return self.inline_enabled, self.inline_limit, self.inline_window_sec
        return self.search_enabled, self.search_limit, self.search_window_sec

    def message(self, lang: str) -> str:
        """Localized limit message; unknown locales fall back to Russian."""
        if lang == "uz":
            return self.limit_message_uz
        if lang == "uz_cyrl":
            return self.limit_message_uz_cyrl
        return self.limit_message_ru

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, raw: str) -> "RateLimitConfig":
        data = json.loads(raw)
        # Keep only known fields so an old/new cache blob can't crash construction.
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)


_DEFAULT_CONFIG = RateLimitConfig()


async def _load_config_from_db() -> RateLimitConfig:
    """Read the singleton settings row from Postgres (defaults if unseeded)."""
    from sqlalchemy import select

    from app.db.database import async_session_maker
    from app.db.models import BotRateLimitSettings

    async with async_session_maker() as session:
        row = (
            await session.execute(
                select(BotRateLimitSettings).where(BotRateLimitSettings.id == 1)
            )
        ).scalar_one_or_none()

    if row is None:
        return _DEFAULT_CONFIG
    return RateLimitConfig(
        search_enabled=row.search_enabled,
        search_limit=row.search_limit,
        search_window_sec=row.search_window_sec,
        inline_enabled=row.inline_enabled,
        inline_limit=row.inline_limit,
        inline_window_sec=row.inline_window_sec,
        limit_message_ru=row.limit_message_ru,
        limit_message_uz=row.limit_message_uz,
        limit_message_uz_cyrl=row.limit_message_uz_cyrl,
    )


async def _load_config() -> RateLimitConfig:
    """Resolve the active config: Redis cache → DB → hardcoded defaults.

    Never raises: any failure degrades to the previous layer and finally to
    :data:`_DEFAULT_CONFIG`, so the limiter (and thus search) keeps working.
    """
    # 1) Fast path: cached JSON blob.
    try:
        redis = await get_redis()
        cached = await redis.get(_CONFIG_CACHE_KEY)
        if cached:
            return RateLimitConfig.from_json(cached)
    except Exception:
        logger.warning("bot.rate_limit: redis config read failed", exc_info=True)
        return _DEFAULT_CONFIG

    # 2) Cache miss: load the singleton row and warm the cache for next time.
    try:
        config = await _load_config_from_db()
    except Exception:
        logger.warning("bot.rate_limit: db config read failed", exc_info=True)
        return _DEFAULT_CONFIG

    try:
        redis = await get_redis()
        await redis.set(_CONFIG_CACHE_KEY, config.to_json(), ex=_CONFIG_CACHE_TTL)
    except Exception:
        logger.warning("bot.rate_limit: config cache write failed", exc_info=True)
    return config


async def hit(scope: str, user_id: int) -> bool:
    """Register one request and report whether it is allowed.

    Returns ``True`` when the caller should proceed (within the limit, the
    scope is disabled, or anything went wrong → fail-open) and ``False`` only
    when the user has provably exceeded the configured limit for ``scope``.
    """
    try:
        config = await _load_config()
        enabled, limit, window = config.for_scope(scope)
        if not enabled or limit <= 0:
            return True
        redis = await get_redis()
        key = _HIT_KEY.format(scope=scope, user_id=user_id)
        count = await redis.incr(key)
        if count == 1:
            # First hit in this window — arm the TTL so the bucket resets.
            await redis.expire(key, window)
        return count <= limit
    except Exception:
        logger.warning(
            "bot.rate_limit: hit failed scope=%s — failing open", scope, exc_info=True
        )
        return True


async def limit_message(lang: str) -> str:
    """The (admin-editable) "too many requests" message for ``lang``.

    Used by both the in-chat search reply and the inline rate-limit card.
    Always returns a non-empty string (config value or hardcoded default).
    """
    try:
        config = await _load_config()
    except Exception:
        config = _DEFAULT_CONFIG
    return config.message(lang)


async def publish_config_cache(config: RateLimitConfig) -> None:
    """Write-through the bot's Redis cache from the admin API.

    Called after a successful settings update so the change takes effect
    immediately instead of waiting out :data:`_CONFIG_CACHE_TTL`.
    """
    redis = await get_redis()
    await redis.set(_CONFIG_CACHE_KEY, config.to_json(), ex=_CONFIG_CACHE_TTL)
