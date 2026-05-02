"""Post-PR-I — Activity log receiver.

Fire-and-forget analytics ingress. The frontend
`shared/api/activityLog.ts` sends one-shot `POST /api/v1/activity-log`
events on high-signal user actions (likes, views, searches, saved
searches). The frontend catches errors silently so a failure here
never blocks the UX.

This route stays intentionally thin:
  - Validates the payload shape.
  - Stamps it with `user_id` when authenticated (optional).
  - Emits a single structured log line at INFO level.
  - Returns 204.

A future PR can swap stdout logging for a dedicated `activity_log`
table or a Kafka producer without changing the wire contract.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from app.api.v1.deps import get_current_user_optional
from app.db.models import User

router = APIRouter()

logger = logging.getLogger("activity")


_ALLOWED_ACTIONS = {
    "like",
    "unlike",
    "view",
    "search",
    "save_search",
}


class ActivityLogPayload(BaseModel):
    """Mirrors `frontend/src/shared/api/types.ts::ActivityLogPayload`."""

    action: str = Field(..., max_length=30)
    listing_id: Optional[UUID] = None
    query: Optional[str] = Field(None, max_length=200)
    filters: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = Field(None, ge=0, le=3_600_000)
    property_type: Optional[str] = Field(None, max_length=30)


@router.post("", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def log_activity(
    payload: ActivityLogPayload,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Accept a single activity event, log it, return 204.

    Unknown actions are logged at WARNING but still accepted (forward-
    compat for new frontend event types). The frontend uses `.catch()`
    so any error here becomes a silent no-op for the user.
    """
    action = payload.action
    level = logging.INFO if action in _ALLOWED_ACTIONS else logging.WARNING

    logger.log(
        level,
        "activity user=%s action=%s listing=%s query=%s pt=%s dur_ms=%s ua=%s",
        str(current_user.id) if current_user else "anon",
        action,
        payload.listing_id,
        payload.query,
        payload.property_type,
        payload.duration_ms,
        request.headers.get("user-agent", "")[:80],
    )
    return None
