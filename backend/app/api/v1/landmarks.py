"""PR-G — Landmarks (address-hint catalog) search + get-by-id.

Backs the seller form's `landmark` autocomplete widget. The model is
defined in `app/db/models.py::Landmark` and coexists with the free-text
`Listing.landmark` column — sellers can tag against a known landmark
(landmark_id) OR type a free-text name, mirroring the jk_id / jk_name
dual-column design.

Endpoints:
    GET /api/v1/landmarks?q=<prefix>&region=&district=&category=&limit=<N>
        → List[LandmarkListItem]
            Matches `name ILIKE '%<q>%'` (also the Uzbek name variants),
            optionally narrowed by region / district / category. Ordered
            by name ascending. Soft-capped at 50.
    GET /api/v1/landmarks/{landmark_id}
        → LandmarkResponse  (full row)

Both endpoints are PUBLIC for authenticated users — the catalog isn't
sensitive. Unauthenticated callers get 401 via `get_current_user`.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.exceptions import NotFoundException
from app.db.database import get_db
from app.db.models import Landmark, User
from app.schemas.common import UTCDateTime

router = APIRouter()

# Soft-cap so a seller typing a common letter doesn't get thousands of rows.
_MAX_LIMIT = 50


class LandmarkListItem(BaseModel):
    """Compact row — enough to render in an autocomplete dropdown."""

    id: UUID
    name: str
    name_uz_latn: Optional[str] = None
    name_uz_cyrl: Optional[str] = None
    category: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    microdistrict: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"from_attributes": True}


class LandmarkResponse(BaseModel):
    """Full landmark detail — returned by get-by-id."""

    id: UUID
    name: str
    name_uz_latn: Optional[str] = None
    name_uz_cyrl: Optional[str] = None
    category: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    microdistrict: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    osm_id: Optional[str] = None
    source: Optional[str] = None
    created_at: UTCDateTime
    updated_at: UTCDateTime

    model_config = {"from_attributes": True}


@router.get("", response_model=List[LandmarkListItem])
async def search_landmarks(
    q: Optional[str] = Query(None, max_length=200),
    region: Optional[str] = Query(None, max_length=100),
    district: Optional[str] = Query(None, max_length=100),
    category: Optional[str] = Query(None, max_length=50),
    limit: int = Query(20, ge=1, le=_MAX_LIMIT),
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Prefix-search landmarks by name, optionally narrowed by region /
    district / category. Returns at most `limit` rows (hard cap 50).
    Empty `q` returns the first complexes by name — useful for the initial
    dropdown state once a district is picked (район→ориентир cascade)."""
    query = select(Landmark)
    predicates = []
    if q and q.strip():
        # Case-insensitive substring match across all name locales so a
        # seller typing in any script finds the entry.
        needle = f"%{q.lower().strip()}%"
        predicates.append(
            or_(
                func.lower(Landmark.name).like(needle),
                func.lower(Landmark.name_uz_latn).like(needle),
                func.lower(Landmark.name_uz_cyrl).like(needle),
            )
        )
    if region and region.strip():
        predicates.append(Landmark.region == region.strip())
    if district and district.strip():
        predicates.append(Landmark.district == district.strip())
    if category and category.strip():
        predicates.append(Landmark.category == category.strip())
    if predicates:
        query = query.where(and_(*predicates))
    query = query.order_by(Landmark.name.asc()).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()
    return [LandmarkListItem.model_validate(r) for r in rows]


@router.get("/{landmark_id}", response_model=LandmarkResponse)
async def get_landmark(
    landmark_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Landmark).where(Landmark.id == landmark_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundException("Landmark", str(landmark_id))
    return LandmarkResponse.model_validate(row)
