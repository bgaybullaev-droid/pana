"""Phase-2 — admin queue for the duplicate-account suspicion workflow.

Three endpoints under ``/admin/suspicions``:

* ``GET /admin/suspicions``           — paginated list, filter by
  ``status`` (default ``open``) and ``signal_kind``.
* ``GET /admin/suspicions/{id}``      — single row with full evidence.
* ``POST /admin/suspicions/{id}/decide`` — admin decision. Body
  ``{decision: 'merged' | 'dismissed' | 'reviewed', notes?}``. On
  ``merged`` we additionally write an ``AccountLink`` row with the
  pair extracted from the suspicion evidence so subsequent merge
  flows have a permanent record.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_admin
from app.db.database import get_db
from app.db.models import AccountLink, AccountSuspicion, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/suspicions", tags=["Admin Suspicions"])


_DECISIONS = {"merged", "dismissed", "reviewed"}
_STATUS_VALUES = {"open", "reviewed", "dismissed", "merged"}


class SuspicionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    primary_user_id: UUID
    signal_kind: str
    evidence: dict[str, Any]
    status: str
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime


class DecideRequest(BaseModel):
    decision: str = Field(..., max_length=16)
    notes: Optional[str] = None


@router.get("", response_model=list[SuspicionResponse])
async def list_suspicions(
    status_filter: str = Query(default="open", alias="status", max_length=16),
    signal_kind: Optional[str] = Query(default=None, max_length=48),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> list[SuspicionResponse]:
    if status_filter not in _STATUS_VALUES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "invalid_status", "allowed": sorted(_STATUS_VALUES)},
        )

    stmt = (
        select(AccountSuspicion)
        .where(AccountSuspicion.status == status_filter)
        .order_by(AccountSuspicion.created_at.desc())
    )
    if signal_kind:
        stmt = stmt.where(AccountSuspicion.signal_kind == signal_kind)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = list((await db.execute(stmt)).scalars().all())
    return [SuspicionResponse.model_validate(r) for r in rows]


@router.get("/{suspicion_id}", response_model=SuspicionResponse)
async def get_suspicion(
    suspicion_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> SuspicionResponse:
    row = (
        await db.execute(
            select(AccountSuspicion).where(AccountSuspicion.id == suspicion_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "suspicion_not_found"},
        )
    return SuspicionResponse.model_validate(row)


def _pair_from_evidence(evidence: dict[str, Any]) -> Optional[tuple[UUID, UUID]]:
    """Pull a (a < b) normalised pair of UUIDs out of ``evidence.user_ids``.

    The signal functions always set ``evidence.user_ids`` to a sorted
    list of stringified UUIDs. We accept the first two entries — even
    if a bucket had 3+ collisions the first two are the canonical pair
    and additional ones will surface in the next signal run.
    """
    raw_ids = evidence.get("user_ids") if isinstance(evidence, dict) else None
    if not isinstance(raw_ids, list) or len(raw_ids) < 2:
        return None
    try:
        parsed = sorted(UUID(str(x)) for x in raw_ids[:2])
    except (ValueError, TypeError):
        return None
    a, b = parsed[0], parsed[1]
    if a == b:
        return None
    return a, b


@router.post("/{suspicion_id}/decide", response_model=SuspicionResponse)
async def decide_suspicion(
    suspicion_id: UUID,
    payload: DecideRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> SuspicionResponse:
    if payload.decision not in _DECISIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "invalid_decision", "allowed": sorted(_DECISIONS)},
        )

    row = (
        await db.execute(
            select(AccountSuspicion).where(AccountSuspicion.id == suspicion_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "suspicion_not_found"},
        )

    row.status = payload.decision
    row.reviewed_by = admin.id
    row.reviewed_at = datetime.utcnow()
    if payload.notes is not None:
        row.notes = payload.notes

    # ``merged`` also writes a permanent AccountLink row. Existing
    # link for the same pair is fine — uniqueness is enforced by the
    # composite (a, b) constraint, so a re-merge becomes a no-op
    # after a single round-trip catches the IntegrityError.
    if payload.decision == "merged":
        pair = _pair_from_evidence(row.evidence or {})
        if pair is not None:
            a, b = pair
            existing = (
                await db.execute(
                    select(AccountLink.id).where(
                        AccountLink.user_id_a == a,
                        AccountLink.user_id_b == b,
                    )
                )
            ).first()
            if existing is None:
                db.add(
                    AccountLink(
                        user_id_a=a,
                        user_id_b=b,
                        relation="duplicate",
                        decided_by=admin.id,
                        decided_at=datetime.utcnow(),
                    )
                )

    await db.commit()
    await db.refresh(row)
    logger.info(
        "admin.suspicion.decided id=%s decision=%s by_admin=%s",
        suspicion_id,
        payload.decision,
        admin.id,
    )
    return SuspicionResponse.model_validate(row)
