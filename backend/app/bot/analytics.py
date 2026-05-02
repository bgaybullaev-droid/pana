"""Registration funnel analytics using Redis counters."""

import logging
from datetime import date

from app.db.redis import CacheKeys, get_redis

logger = logging.getLogger(__name__)


async def track_event(event: str) -> None:
    """Track a registration funnel event.

    Events: started, step:{name}, completed, cancelled, abandoned
    Counters are stored per day with 90-day TTL.
    """
    try:
        r = await get_redis()
        today = date.today().isoformat()
        key = CacheKeys.analytics_event(today, event)
        await r.incr(key)
        await r.expire(key, 90 * 86400)  # Keep 90 days
    except Exception as e:
        logger.debug(f"Analytics tracking failed for {event}: {e}")


async def check_rate_limit(
    telegram_id: int, max_attempts: int = 3, window: int = 3600
) -> bool:
    """Check if a user has exceeded the registration rate limit.

    Args:
        telegram_id: User's Telegram ID
        max_attempts: Maximum allowed attempts in the window
        window: Time window in seconds (default 1 hour)

    Returns:
        True if rate-limited (too many attempts), False if OK
    """
    try:
        r = await get_redis()
        key = CacheKeys.registration_attempts(telegram_id)
        attempts = await r.incr(key)
        if attempts == 1:
            await r.expire(key, window)
        return attempts > max_attempts
    except Exception as e:
        logger.debug(f"Rate limit check failed for {telegram_id}: {e}")
        return False  # Allow on Redis failure
