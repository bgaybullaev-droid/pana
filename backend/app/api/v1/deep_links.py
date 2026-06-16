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
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
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
