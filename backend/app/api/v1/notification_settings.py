"""PR-A — Notification Settings endpoints.

Backs the frontend's `shared/api/notificationSettings.ts`
(see docs/system-blueprint.md §10 Option A).

Shape contract (frontend-driven):

    GET  /api/v1/notification-settings -> NotificationSettingsResponse
    PUT  /api/v1/notification-settings -> NotificationSettingsResponse

Distinct from `/api/v1/notifications/preferences` (which exposes the
filter-preset columns on the same underlying model). Both endpoints
read/write the same `notification_preferences` row; they just project
different columns. Updates from either side are safe — no column
overlap.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.db.models import NotificationPreferences, User
from app.schemas.common import UTCDateTime

router = APIRouter()


_ALLOWED_TIME_WINDOWS = {"morning", "afternoon", "evening"}


class NotificationSettingsResponse(BaseModel):
    """The `NotificationSettings` shape the frontend already expects."""

    daily_limit: int
    time_windows: List[str]
    sources: Dict[str, bool]
    paused: bool
    updated_at: Optional[UTCDateTime] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, m: NotificationPreferences) -> "NotificationSettingsResponse":
        return cls(
            daily_limit=m.daily_limit,
            time_windows=list(m.time_windows or []),
            sources={
                "saved_searches": bool(m.source_saved_searches),
                "seller_follows": bool(m.source_seller_follows),
                "ai_recs": bool(m.source_ai_recs),
            },
            paused=bool(m.paused),
            updated_at=m.updated_at,
        )


class NotificationSettingsUpdate(BaseModel):
    """Partial update — each field independently optional."""

    daily_limit: Optional[int] = Field(None, ge=0, le=100)
    time_windows: Optional[List[str]] = None
    sources: Optional[Dict[str, bool]] = None
    paused: Optional[bool] = None

    @field_validator("time_windows")
    @classmethod
    def _validate_time_windows(cls, v):
        if v is None:
            return v
        bad = [x for x in v if x not in _ALLOWED_TIME_WINDOWS]
        if bad:
            raise ValueError(
                f"time_windows elements must be in {sorted(_ALLOWED_TIME_WINDOWS)}; "
                f"got invalid: {bad}"
            )
        # De-dupe preserving order.
        seen: set = set()
        out: List[str] = []
        for e in v:
            if e not in seen:
                out.append(e)
                seen.add(e)
        return out

    @field_validator("sources")
    @classmethod
    def _validate_sources(cls, v):
        if v is None:
            return v
        allowed = {"saved_searches", "seller_follows", "ai_recs"}
        bad = [k for k in v.keys() if k not in allowed]
        if bad:
            raise ValueError(
                f"sources keys must be in {sorted(allowed)}; got unknown: {bad}"
            )
        for k, val in v.items():
            if not isinstance(val, bool):
                raise ValueError(f"sources.{k} must be boolean")
        return v


async def _get_or_create_prefs(db: AsyncSession, user_id) -> NotificationPreferences:
    """Return the user's NotificationPreferences row, creating a default
    one on first access. Does NOT commit — the caller is responsible so
    an insert can be batched with an update."""
    result = await db.execute(
        select(NotificationPreferences).where(
            NotificationPreferences.user_id == user_id
        )
    )
    prefs = result.scalar_one_or_none()
    if prefs is not None:
        return prefs
    prefs = NotificationPreferences(user_id=user_id)
    db.add(prefs)
    await db.flush()
    return prefs


@router.get("", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _get_or_create_prefs(db, current_user.id)
    await db.commit()
    return NotificationSettingsResponse.from_model(prefs)


@router.put("", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    data: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = await _get_or_create_prefs(db, current_user.id)

    if data.daily_limit is not None:
        prefs.daily_limit = data.daily_limit
    if data.time_windows is not None:
        prefs.time_windows = data.time_windows
    if data.sources is not None:
        if "saved_searches" in data.sources:
            prefs.source_saved_searches = data.sources["saved_searches"]
        if "seller_follows" in data.sources:
            prefs.source_seller_follows = data.sources["seller_follows"]
        if "ai_recs" in data.sources:
            prefs.source_ai_recs = data.sources["ai_recs"]
    if data.paused is not None:
        prefs.paused = data.paused
        # Keep legacy `enabled` flag in sync so the older fanout consumer
        # (which reads `enabled`) respects the pause.
        prefs.enabled = not data.paused

    await db.commit()
    await db.refresh(prefs)
    return NotificationSettingsResponse.from_model(prefs)
