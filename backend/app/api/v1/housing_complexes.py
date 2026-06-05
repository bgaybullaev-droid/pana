"""PR-F — Housing Complexes (residential-complex) search + get-by-id.

Backs the seller form's `jk_id` autocomplete widget. The model is defined
in `app/db/models.py::HousingComplex` (Sprint 7 / T-027) and coexists
with the free-text `Listing.jk_name` column — sellers can choose to tag
against a known HC (jk_id) OR type a free-text name (jk_name), matching
the matrix-gated dual-column design.

Endpoints:
    GET /api/v1/housing-complexes?q=<prefix>&region=<region>&limit=<N>
        → List[HousingComplexListItem]
            Matches on `name ILIKE '%<q>%'`, optionally narrowed by
            `region`. Ordered by name ascending. Soft-capped at 50.
    GET /api/v1/housing-complexes/{hc_id}
        → HousingComplexResponse  (full row)

Both endpoints are PUBLIC for authenticated users — the catalog isn't
sensitive. Unauthenticated callers get 401 via the `get_current_user`
dependency (there's no anonymous-safe variant since autocomplete only
runs inside the seller form).
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
from app.db.models import HousingComplex, User
from app.schemas.common import UTCDateTime

router = APIRouter()

# Soft-cap so a seller typing a common letter doesn't get 10k rows.
_MAX_LIMIT = 50


class HousingComplexListItem(BaseModel):
    """Compact row — enough to render in an autocomplete dropdown."""

    id: UUID
    name: str
    name_uz_latn: Optional[str] = None
    name_uz_cyrl: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    microdistrict: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {"from_attributes": True}


class HousingComplexResponse(BaseModel):
    """Full HC detail — returned by get-by-id."""

    id: UUID
    name: str
    name_uz_latn: Optional[str] = None
    name_uz_cyrl: Optional[str] = None
    developer_id: Optional[UUID] = None
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


@router.get("", response_model=List[HousingComplexListItem])
async def search_housing_complexes(
    q: Optional[str] = Query(None, max_length=200),
    region: Optional[str] = Query(None, max_length=100),
    district: Optional[str] = Query(None, max_length=100),
    limit: int = Query(20, ge=1, le=_MAX_LIMIT),
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Prefix-search housing complexes by name, optionally narrowed by
    region and/or district (район→ЖК cascade). Returns at most `limit`
    rows (hard cap 50). Empty `q` returns the first complexes by name —
    useful for the initial dropdown state once a district is picked.
    """
    query = select(HousingComplex)
    predicates = []
    if q and q.strip():
        # Case-insensitive substring match across all name locales. Use PG
        # ILIKE for predicate stability; no full-text ranking needed here.
        needle = f"%{q.lower().strip()}%"
        predicates.append(
            or_(
                func.lower(HousingComplex.name).like(needle),
                func.lower(HousingComplex.name_uz_latn).like(needle),
                func.lower(HousingComplex.name_uz_cyrl).like(needle),
            )
        )
    if region and region.strip():
        predicates.append(HousingComplex.region == region.strip())
    if district and district.strip():
        predicates.append(HousingComplex.district == district.strip())
    if predicates:
        query = query.where(and_(*predicates))
    query = query.order_by(HousingComplex.name.asc()).limit(limit)

    result = await db.execute(query)
    rows = result.scalars().all()
    return [HousingComplexListItem.model_validate(r) for r in rows]


@router.get("/{hc_id}", response_model=HousingComplexResponse)
async def get_housing_complex(
    hc_id: UUID,
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(HousingComplex).where(HousingComplex.id == hc_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundException("HousingComplex", str(hc_id))
    return HousingComplexResponse.model_validate(row)
