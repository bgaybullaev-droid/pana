"""Block F V2.0 F5b — seller-facing AI feedback endpoint.

Single route, ``POST /ai-feedback``. Authenticated user submits one
"👎 Не нравится текст" row pointing at a listing (and optionally the
specific AI generation that produced the text they're complaining
about). Rate-limited to 30 submissions/min/user via a sliding Redis
counter — anything beyond that returns 429 and the row is dropped.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.db.models import AIGenerationFeedback, Listing, User
from app.db.redis import get_redis
from app.schemas.ai_quality import AIFeedbackCreate, AIFeedbackResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-feedback", tags=["AI Feedback"])

# Sliding-window rate limit. Keyed on `aifb:rl:<user_id>`; auto-expires
# after 60s so concurrent requests never see a stale counter.
_RATE_LIMIT_PER_MIN = 30
_RATE_WINDOW_SECONDS = 60


async def _check_rate_limit(user_id: str) -> None:
    """Atomic INCR + EXPIRE. Raises 429 when over the limit. Fail-soft
    on Redis outage so a transient cache problem never blocks the
    quality-feedback channel."""
    try:
        client = await get_redis()
        key = f"aifb:rl:{user_id}"
        # INCR returns the new value; first hit also sets EXPIRE.
        new_value = await client.incr(key)
        if new_value == 1:
            await client.expire(key, _RATE_WINDOW_SECONDS)
        if new_value > _RATE_LIMIT_PER_MIN:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "rate_limited", "retry_after_s": _RATE_WINDOW_SECONDS},
            )
    except HTTPException:
        raise
    except Exception:
        logger.warning("ai_feedback.rate_limit_check_failed user=%s", user_id)


@router.post(
    "",
    response_model=AIFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback on AI-generated listing text",
)
async def submit_ai_feedback(
    payload: AIFeedbackCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIFeedbackResponse:
    """Insert one ``ai_generation_feedback`` row attributed to
    ``current_user``. The associated listing is verified to exist; the
    optional ``generation_id`` is **not** verified here — it's a soft
    pointer (FK ``ON DELETE SET NULL``) that's allowed to drift if the
    underlying generation row gets pruned by F5b's 90-day cron."""
    await _check_rate_limit(str(current_user.id))

    # Verify the listing exists. We don't gate on ownership: any
    # authenticated user can flag bad text on any listing — admins can
    # decide what to do with cross-account reports.
    listing = (
        await db.execute(select(Listing).where(Listing.id == payload.listing_id))
    ).scalar_one_or_none()
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "listing_not_found"},
        )

    row = AIGenerationFeedback(
        generation_id=payload.generation_id,
        listing_id=payload.listing_id,
        user_id=current_user.id,
        category=payload.category,
        comment=payload.comment,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    logger.info(
        "ai_feedback.submitted user=%s listing=%s category=%s",
        current_user.id,
        payload.listing_id,
        payload.category,
    )
    return AIFeedbackResponse.model_validate(row)
