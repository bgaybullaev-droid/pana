"""Block D V2.0 (D3) — public resolver for filter-style deep-link payloads.

When a marketing link routes via ``?startapp=filter_<short_id>``, the
TWA receives the short ID through ``initDataUnsafe.start_param``.
The frontend then calls ``GET /deep-links/{short_id}`` to fetch the
stored filter JSON and hydrate its buyer-side filter store.

Only ``kind=filter`` payloads are exposed here. Claim/agent/ref tickets
are bot-side flows and have no equivalent TWA-readable endpoint —
exposing them would leak the security boundary established in
DECISION_MATRIX D3-Q2.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services import deeplink

logger = logging.getLogger(__name__)
router = APIRouter()

# Opaque short-ids are 12 uppercase base32 chars; marketing slugs (FU6)
# are lowercase words joined by underscores (``chilonzor_2rooms_rent``).
# This guard accepts both shapes and hard-caps length so a malicious
# caller can't probe with megabyte URLs before we touch the DB.
_VALID_SHORT_ID = re.compile(r"^[A-Za-z0-9_]{1,32}$")


class DeepLinkResponse(BaseModel):
    """Payload returned to the TWA when resolving a filter short-id."""

    id: str
    kind: str
    payload: dict[str, Any]


class FilterLinkRequest(BaseModel):
    """Full buyer-feed filter set the TWA wants to encode into a share link.

    Mirrors the frontend ``HomeFilters`` so a user can share *any* filter
    combination — not just the district/rooms/deal subset the bot and
    marketing slugs cover. Unknown keys are ignored; only set (non-None)
    fields are stored, and the resolver round-trips them back verbatim.
    """

    model_config = ConfigDict(extra="ignore")

    q: Optional[str] = Field(None, max_length=200)
    type: Optional[list[str]] = None
    property_type: Optional[list[str]] = None
    rooms: Optional[list[int]] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    region: Optional[list[str]] = None
    district: Optional[list[str]] = None
    area_min: Optional[int] = None
    area_max: Optional[int] = None
    floor_min: Optional[int] = None
    floor_max: Optional[int] = None
    total_floors_min: Optional[int] = None
    total_floors_max: Optional[int] = None
    not_first_floor: Optional[bool] = None
    not_last_floor: Optional[bool] = None
    building_type: Optional[str] = None
    condition: Optional[list[str]] = None
    has_photo: Optional[bool] = None
    posted_within: Optional[int] = None
    mortgage_ok: Optional[bool] = None
    installment_ok: Optional[bool] = None
    halol_ok: Optional[bool] = None
    furnished: Optional[bool] = None
    allowed_pets: Optional[bool] = None
    allowed_students: Optional[bool] = None
    utilities_incl: Optional[bool] = None
    rent_period: Optional[str] = None
    sort: Optional[str] = None


class FilterLinkResponse(BaseModel):
    """Newly minted share link: opaque short id + ready-to-share URL."""

    id: str
    url: str


@router.get("/{short_id}", response_model=DeepLinkResponse)
async def resolve_deep_link(
    short_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DeepLinkResponse:
    """Resolve a ``filter_*`` payload by short ID or marketing slug.

    Resolution order:
      1. stored ``filter`` short-id in ``deep_link_payloads`` (increments
         its use-count);
      2. FU6 fallback — decode a human marketing slug
         (``chilonzor_2rooms_rent``) into a synthesised filter payload.

    Returns 404 for unknown IDs and for any payload kind other than
    ``filter`` — keeps claim/agent/ref opaque to the TWA.
    """
    if not _VALID_SHORT_ID.match(short_id):
        logger.info("deeplink.resolve.bad_id id=%r", short_id[:32])
        raise HTTPException(status_code=404, detail="Deep link not found")

    payload = await deeplink.resolve_filter_payload(short_id, db)
    if payload is not None:
        await deeplink.record_event(
            "filter",
            f"filter_{short_id}",
            db,
            user_id=None,
            is_new_user=False,
            outcome=deeplink.OUTCOME_RESOLVED,
        )
        await db.commit()
        return DeepLinkResponse(
            id=payload.id,
            kind=payload.kind,
            payload=payload.payload,
        )

    # No stored short-id — try decoding a human marketing slug (FU6).
    slug_payload = deeplink.parse_filter_slug(short_id)
    if slug_payload is not None:
        await deeplink.record_event(
            "filter",
            f"filter_{short_id}",
            db,
            user_id=None,
            is_new_user=False,
            outcome=deeplink.OUTCOME_RESOLVED_SLUG,
        )
        await db.commit()
        return DeepLinkResponse(id=short_id, kind="filter", payload=slug_payload)

    # Neither a known short-id nor a decodable slug. Log analytics row
    # for visibility into broken share URLs in the wild.
    await deeplink.record_event(
        "filter",
        f"filter_{short_id}",
        db,
        user_id=None,
        is_new_user=False,
        outcome=deeplink.OUTCOME_REJECTED_UNKNOWN,
    )
    await db.commit()
    raise HTTPException(status_code=404, detail="Deep link not found")


@router.post("/filter", response_model=FilterLinkResponse)
async def create_filter_link(
    req: FilterLinkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FilterLinkResponse:
    """Persist the caller's current filter set and return a share link.

    Powers the in-app "Share filter" action: the buyer (or marketing)
    encodes the full ``HomeFilters`` here and gets back a
    ``t.me/<bot>?startapp=filter_<id>`` URL. Auth-gated so anonymous
    callers can't spam the payload table; attribution is recorded via
    ``created_by_user_id``.
    """
    filters = req.model_dump(exclude_none=True)
    if not filters:
        raise HTTPException(status_code=400, detail="No filters to share")

    short_id, url = await deeplink.build_filter_link(
        filters, db, created_by_user_id=current_user.id
    )
    await db.commit()
    logger.info("deeplink.filter.shared id=%s by_user=%s", short_id, current_user.id)
    return FilterLinkResponse(id=short_id, url=url)
