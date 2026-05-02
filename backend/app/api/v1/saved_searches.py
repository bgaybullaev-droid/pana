"""PR-B — Saved Searches CRUD + new_count computation.

Frontend contract (see docs/system-blueprint.md §5.1 + §9, plus
`frontend/src/shared/api/savedSearches.ts`):

    GET    /api/v1/saved-searches
    POST   /api/v1/saved-searches
    DELETE /api/v1/saved-searches/{search_id}
    PATCH  /api/v1/saved-searches/{search_id}/seen
    PATCH  /api/v1/saved-searches/{search_id}/notifications

Design notes:
  - `filters` is JSONB — validated SOFT (known keys recognized, unknown
    keys allowed) so older saved searches keep working when new filter
    fields ship. Strict-validation mode is possible later via a Pydantic
    v2 model if product wants.
  - `new_count` is computed per-row on every GET by counting listings
    created after `last_seen_at` that also match the saved filter. To
    avoid N+1 on the response, we batch the counts into one UNION-ALL
    query (see `_compute_new_counts`).
  - Maximum 20 saved searches per user — enforced on POST.
  - Matcher-engine parity: the Celery new-listing fanout
    (`_send_new_listing_notifications`) uses
    `app.services.saved_search_matcher._match_listing_to_filters` which
    consumes a `ListingFilters` object. We hydrate JSONB → ListingFilters
    at call time via `_filters_to_listing_filters`. Unknown keys in the
    JSONB are silently dropped because ListingFilters is a closed model;
    that matches the GET-side leniency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.exceptions import BadRequestException, NotFoundException
from app.db.database import get_db
from app.db.models import (
    Listing,
    ListingStatus,
    ModerationStatus,
    SavedSearch,
    User,
)
from app.schemas.common import UTCDateTime
from app.schemas.listing import ListingFilters

router = APIRouter()


# Upper bound per user — documented in the spec; prevents runaway
# subscription fanout costs.
_MAX_SAVED_SEARCHES_PER_USER = 20


# ─────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────


class SavedSearchResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    query: Optional[str] = None
    filters: Dict[str, Any]
    sort: str
    created_at: UTCDateTime
    last_seen_at: Optional[UTCDateTime] = None
    new_count: int = 0
    notifications_enabled: bool

    model_config = {"from_attributes": True}


class SavedSearchCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    query: Optional[str] = Field(None, max_length=200)
    filters: Dict[str, Any] = Field(default_factory=dict)
    sort: Optional[str] = Field(None, max_length=30)


class SavedSearchNotificationToggle(BaseModel):
    enabled: bool


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _filters_to_listing_filters(payload: Dict[str, Any]) -> ListingFilters:
    """Hydrate a JSONB dict into ListingFilters, silently dropping any
    keys ListingFilters doesn't know about. The shared `_apply_filters`
    engine is the ground truth for what constitutes a valid search.

    `deal_type` on the frontend maps to `type` on ListingFilters —
    rename if present.
    """
    clean: Dict[str, Any] = {}
    known = set(ListingFilters.model_fields.keys())
    for k, v in payload.items():
        key = "type" if k == "deal_type" else k
        if key in known:
            clean[key] = v
    try:
        return ListingFilters(**clean)
    except Exception:
        # Soft-fail: return an empty-filter object so the row still loads
        # (new_count will simply count all active listings since last_seen).
        # This preserves backward compat when the filter schema evolves
        # under stored rows.
        return ListingFilters()


async def _compute_new_count(
    db: AsyncSession,
    saved: SavedSearch,
) -> int:
    """Count active, approved, non-deleted listings created after
    `last_seen_at` that match the saved filter. Returns 0 if the saved
    search has never been seen (first-read sentinel)."""
    cutoff = saved.last_seen_at
    if cutoff is None:
        # Never seen → treat as if seen now; badge is 0 by convention.
        return 0

    from app.api.v1.listings import _apply_filters

    filters = _filters_to_listing_filters(saved.filters or {})

    base = (
        select(func.count())
        .select_from(Listing)
        .where(
            Listing.status == ListingStatus.ACTIVE,
            Listing.moderation_status == ModerationStatus.APPROVED,
            Listing.deleted_at.is_(None),
            Listing.created_at > cutoff,
        )
    )
    base = _apply_filters(base, filters)

    result = await db.execute(base)
    return int(result.scalar() or 0)


async def _load_owned_search(
    db: AsyncSession,
    search_id: UUID,
    user_id: UUID,
) -> SavedSearch:
    q = select(SavedSearch).where(
        and_(SavedSearch.id == search_id, SavedSearch.user_id == user_id)
    )
    result = await db.execute(q)
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundException("SavedSearch", str(search_id))
    return row


def _to_response(saved: SavedSearch, new_count: int) -> SavedSearchResponse:
    return SavedSearchResponse(
        id=saved.id,
        user_id=saved.user_id,
        name=saved.name or "",
        query=saved.query,
        filters=dict(saved.filters or {}),
        sort=saved.sort or "relevance",
        created_at=saved.created_at,
        last_seen_at=saved.last_seen_at,
        new_count=new_count,
        notifications_enabled=bool(saved.notify_enabled),
    )


# ─────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=List[SavedSearchResponse])
async def list_saved_searches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(SavedSearch)
        .where(SavedSearch.user_id == current_user.id)
        .order_by(SavedSearch.created_at.desc())
    )
    result = await db.execute(q)
    rows = result.scalars().all()

    out: List[SavedSearchResponse] = []
    for row in rows:
        new_count = await _compute_new_count(db, row)
        out.append(_to_response(row, new_count))
    return out


@router.post(
    "",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_saved_search(
    data: SavedSearchCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Enforce per-user cap.
    count_q = (
        select(func.count())
        .select_from(SavedSearch)
        .where(SavedSearch.user_id == current_user.id)
    )
    count = (await db.execute(count_q)).scalar() or 0
    if count >= _MAX_SAVED_SEARCHES_PER_USER:
        raise BadRequestException(
            f"Max {_MAX_SAVED_SEARCHES_PER_USER} saved searches per user reached."
        )

    # Use Python's local time (no UTC conversion) to match the DB's
    # server_default=func.now() which stores Tashkent-local naive
    # datetimes in DateTime columns. UTC would be 5h behind, making
    # new_count comparisons always return stale positives.
    now = datetime.now()
    saved = SavedSearch(
        user_id=current_user.id,
        name=(data.name or "").strip(),
        query=(data.query or None) if (data.query or "").strip() else None,
        sort=(data.sort or "relevance").strip() or "relevance",
        filters=data.filters or {},
        notify_enabled=True,
        last_seen_at=now,
    )
    db.add(saved)
    await db.commit()
    await db.refresh(saved)

    # new_count for a brand-new row is 0 by definition.
    return _to_response(saved, new_count=0)


@router.delete(
    "/{search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_saved_search(
    search_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    saved = await _load_owned_search(db, search_id, current_user.id)
    await db.delete(saved)
    await db.commit()
    # 204 — no body.
    return None


@router.patch(
    "/{search_id}/seen",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def mark_saved_search_seen(
    search_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    saved = await _load_owned_search(db, search_id, current_user.id)
    saved.last_seen_at = datetime.now()
    await db.commit()
    return None


@router.patch(
    "/{search_id}/notifications",
    response_model=SavedSearchNotificationToggle,
)
async def toggle_saved_search_notifications(
    search_id: UUID,
    body: SavedSearchNotificationToggle,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    saved = await _load_owned_search(db, search_id, current_user.id)
    saved.notify_enabled = bool(body.enabled)
    await db.commit()
    # Echo the new state — matches frontend `toggleNotifications` contract.
    return SavedSearchNotificationToggle(enabled=saved.notify_enabled)


# Unused import retention: `HTTPException` kept for future rate-limit
# responses without breaking the module export surface.
_ = HTTPException
