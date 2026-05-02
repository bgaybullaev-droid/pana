"""Redis connection and utilities."""

from typing import Optional

import redis.asyncio as redis

from app.core.config import settings

# Redis client (lazy initialization)
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_connection_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def redis_client() -> redis.Redis:
    """Dependency to get Redis client."""
    return await get_redis()


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


# Cache key patterns
class CacheKeys:
    """Redis cache key patterns."""

    @staticmethod
    def listing(listing_id: str) -> str:
        """Key for listing cache."""
        return f"listing:{listing_id}"

    @staticmethod
    def listing_views(listing_id: str) -> str:
        """Key for listing view counter."""
        return f"listing:{listing_id}:views"

    @staticmethod
    def user_session(user_id: str) -> str:
        """Key for user session data."""
        return f"user:{user_id}:session"

    @staticmethod
    def refresh_token(user_id: str, token_id: str) -> str:
        """Key for refresh token."""
        return f"refresh_token:{user_id}:{token_id}"

    @staticmethod
    def exchange_rate() -> str:
        """Key for USD/UZS exchange rate."""
        return "rate:usd_uzs"

    @staticmethod
    def districts_list() -> str:
        """Key for districts list."""
        return "districts:list"

    @staticmethod
    def rate_limit(key: str) -> str:
        """Key for rate limiting."""
        return f"rate_limit:{key}"

    @staticmethod
    def seller_otp(phone: str) -> str:
        """Key for seller OTP code."""
        return f"seller_otp:{phone}"

    @staticmethod
    def seller_otp_attempts(phone: str) -> str:
        """Key for seller OTP verification attempts."""
        return f"seller_otp_attempts:{phone}"

    @staticmethod
    def registration_attempts(telegram_id: int) -> str:
        """Key for bot registration rate limiting."""
        return f"bot:reg_attempts:{telegram_id}"

    @staticmethod
    def analytics_event(date: str, event: str) -> str:
        """Key for registration analytics counters."""
        return f"analytics:reg:{date}:{event}"

    @staticmethod
    def notification_daily_count(user_id: str, date: str) -> str:
        """Key for daily notification counter per user."""
        return f"notif_daily:{user_id}:{date}"
