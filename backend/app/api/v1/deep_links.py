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
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services import deeplink

logger = logging.getLogger(__name__)
router = APIRouter()


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
    """Resolve a ``filter_*`` payload by short ID.

    Returns 404 for unknown IDs and for any payload kind other than
    ``filter`` — keeps claim/agent/ref opaque to the TWA.
    """
    # Defensive: keep the resolver's surface tiny. Hard-cap length so a
    # malicious caller can't probe with megabyte URLs.
    if len(short_id) > 16 or not short_id.isalnum():
        logger.info("deeplink.resolve.bad_id id=%r", short_id[:16])
        raise HTTPException(status_code=404, detail="Deep link not found")

    payload = await deeplink.resolve_filter_payload(short_id, db)
    if payload is None:
        # Resolver did not find a ``filter`` kind. Log analytics row
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
