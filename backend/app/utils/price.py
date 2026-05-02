"""Price normalization utilities for currency-aware comparison."""

import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_usd_uzs_rate() -> float:
    """Get USD→UZS exchange rate from Redis, falling back to config.

    Returns:
        Exchange rate (e.g. 12800.0 means 1 USD = 12800 UZS).
    """
    try:
        from app.db.redis import get_redis

        redis = await get_redis()
        cached = await redis.get("rate:usd_uzs")
        if cached:
            return float(cached)
    except Exception as exc:
        logger.warning("Failed to read exchange rate from Redis: %s", exc)

    return float(settings.exchange_rate_fallback)


def normalize_price_to_usd(
    price: float,
    currency: str,
    usd_uzs_rate: float,
) -> Optional[float]:
    """Convert a price to USD equivalent for preference scoring.

    Returns:
        Price in USD, or None if currency is unknown/unsupported.
    """
    cur = (currency or "").upper()
    if cur == "USD":
        return price
    if cur == "UZS":
        if usd_uzs_rate > 0:
            return price / usd_uzs_rate
        return None
    # Unknown currency — caller should skip price scoring
    return None
