"""A8 — Admin API for parser-source CRUD + per-source metrics.

Block A V2.0 surface for managing the parser channel list without code
edits, plus aggregated extraction/AI-failure stats over a rolling 7-day
window.

Endpoints (all admin-only):
- ``GET    /admin/sources``                — list + last-7-day aggregates
- ``POST   /admin/sources``                — add a new source
- ``GET    /admin/sources/{id}``           — single source + last-30-day breakdown
- ``GET    /admin/sources/{id}/metrics``   — per-day metrics for a window (?days=N)
- ``PATCH  /admin/sources/{id}``           — update name/priority/is_active/parse_interval
- ``POST   /admin/sources/{id}/toggle``    — flip ``is_active``
- ``DELETE /admin/sources/{id}``           — hard delete (cascade clears metrics)
- ``POST   /admin/sources/{id}/metrics``   — crawler-side ingestion (upsert per day)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_admin
from app.core.exceptions import BadRequestException, NotFoundException
from app.db.database import get_db
from app.db.models import ParserSource, SourceMetric, User

logger = logging.getLogger(__name__)
router = APIRouter()


# ── identifier validators ─────────────────────────────────────────────


_TG_USERNAME_RE = re.compile(r"^@?[A-Za-z0-9_]{4,64}$")


def _normalise_telegram_identifier(value: str) -> str:
    """Telegram channel: ``@username`` or bare ``username`` (4-64 chars,
    letters/digits/underscore). Stored without the leading ``@`` so the
    crawler-side Telethon resolver receives the same form across rows.
    """
    s = value.strip()
    if not _TG_USERNAME_RE.match(s):
        raise ValueError(
            "telegram identifier must be 4-64 chars (letters, digits, "
            "underscore), optionally prefixed with '@'"
        )
    return s.lstrip("@")


def _validate_olx_url(value: str) -> str:
    """OLX source: http(s) URL with a hostname containing ``olx``."""
    s = value.strip()
    parsed = urlparse(s)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("olx identifier must be a full http(s) URL")
    if "olx" not in parsed.netloc.lower():
        raise ValueError("olx URL must point to an olx domain")
    return s

# ── schemas ───────────────────────────────────────────────────────────


class SourceCreate(BaseModel):
    """Body for ``POST /admin/sources``.

    Validates ``identifier`` against ``type``:
    * ``telegram_channel`` → @-prefixed or bare username, 4–64 chars.
    * ``website`` / ``olx`` → http(s) URL pointing to an olx domain.
    """

    type: str = Field(
        ...,
        pattern="^(telegram_channel|website|olx|other)$",
        description="Source kind. ``telegram_channel`` is the default.",
    )
    identifier: str = Field(..., min_length=1, max_length=200)
    name: str = Field(..., min_length=1, max_length=200)
    priority: str = Field("medium", pattern="^(high|medium|low)$")
    parse_interval_minutes: int = Field(60, ge=5, le=1440)
    is_active: bool = True

    @model_validator(mode="after")
    def _validate_identifier_per_type(self) -> "SourceCreate":
        if self.type == "telegram_channel":
            self.identifier = _normalise_telegram_identifier(self.identifier)
        elif self.type in ("website", "olx"):
            self.identifier = _validate_olx_url(self.identifier)
        # ``other`` is a free-form escape hatch — no extra validation
        return self


class SourceUpdate(BaseModel):
    """Body for ``PATCH /admin/sources/{id}``. All fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    priority: Optional[str] = Field(None, pattern="^(high|medium|low)$")
    parse_interval_minutes: Optional[int] = Field(None, ge=5, le=1440)
    is_active: Optional[bool] = None


class SourceMetric7d(BaseModel):
    """Aggregated 7-day metric block returned with each source."""

    listings_found: int = 0
    listings_extracted: int = 0
    listings_failed: int = 0
    dupes_filtered: int = 0
    ai_failed: int = 0
    notified: int = 0
    extraction_success_rate: Optional[float] = None  # 0–1, None when found=0


class SourceResponse(BaseModel):
    id: str
    type: str
    identifier: str
    name: str
    is_active: bool
    priority: str
    parse_interval_minutes: int
    total_parsed: int
    total_errors: int
    consecutive_errors: int
    last_parsed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    metrics_7d: SourceMetric7d


class SourceMetricIn(BaseModel):
    """Body for ``POST /admin/sources/{id}/metrics``.

    Crawler-side writeback. ``day`` defaults to today (UTC). Counters are
    incremented (UPSERT-merge) so multiple crawler ticks per day are safe.

    Two field groupings are accepted to keep the crawler agnostic:
    * Internal names: ``listings_found / listings_extracted / listings_failed
      / dupes_filtered / ai_failed / notified``.
    * Spec aliases: ``parsed / saved / failed / duplicates / notified``.
      When both are supplied, internal names win.
    """

    day: Optional[datetime] = None  # default: today (UTC)
    listings_found: Optional[int] = Field(None, ge=0)
    listings_extracted: Optional[int] = Field(None, ge=0)
    listings_failed: Optional[int] = Field(None, ge=0)
    dupes_filtered: Optional[int] = Field(None, ge=0)
    ai_failed: Optional[int] = Field(None, ge=0)
    notified: Optional[int] = Field(None, ge=0)
    # Spec aliases (used by the crawler integration; same numbers under
    # different names — the model_validator merges them.)
    parsed: Optional[int] = Field(None, ge=0)
    saved: Optional[int] = Field(None, ge=0)
    failed: Optional[int] = Field(None, ge=0)
    duplicates: Optional[int] = Field(None, ge=0)

    @model_validator(mode="after")
    def _merge_aliases(self) -> "SourceMetricIn":
        if self.listings_found is None and self.parsed is not None:
            self.listings_found = self.parsed
        if self.listings_extracted is None and self.saved is not None:
            self.listings_extracted = self.saved
        if self.listings_failed is None and self.failed is not None:
            self.listings_failed = self.failed
        if self.dupes_filtered is None and self.duplicates is not None:
            self.dupes_filtered = self.duplicates
        # Final defaults
        self.listings_found = self.listings_found or 0
        self.listings_extracted = self.listings_extracted or 0
        self.listings_failed = self.listings_failed or 0
        self.dupes_filtered = self.dupes_filtered or 0
        self.ai_failed = self.ai_failed or 0
        self.notified = self.notified or 0
        return self


class SourceDailyMetric(BaseModel):
    day: datetime
    listings_found: int
    listings_extracted: int
    listings_failed: int
    dupes_filtered: int
    ai_failed: int
    notified: int


class SourceMetricsRangeResponse(BaseModel):
    """Daily breakdown returned by ``GET /admin/sources/{id}/metrics``."""

    days: int
    totals: SourceMetric7d
    daily: List[SourceDailyMetric]


# ── helpers ───────────────────────────────────────────────────────────


_AGG_COLS = (
    "listings_found",
    "listings_extracted",
    "listings_failed",
    "dupes_filtered",
    "ai_failed",
    "notified",
)


def _agg_query(source_id_filter, cutoff: datetime):
    """Build a SUM(...) query over SourceMetric for one or all sources.

    ``source_id_filter`` is either a UUID (single source) or None (all).
    """
    cols = [
        func.coalesce(func.sum(getattr(SourceMetric, c)), 0).label(c)
        for c in _AGG_COLS
    ]
    q = select(*([SourceMetric.source_id, *cols] if source_id_filter is None else cols))
    q = q.where(SourceMetric.day >= cutoff)
    if source_id_filter is not None:
        q = q.where(SourceMetric.source_id == source_id_filter)
    if source_id_filter is None:
        q = q.group_by(SourceMetric.source_id)
    return q


def _serialise(source: ParserSource, m: dict) -> SourceResponse:
    """Build the response model with the 7-day aggregate attached."""
    found = int(m.get("listings_found", 0) or 0)
    extracted = int(m.get("listings_extracted", 0) or 0)
    rate = (extracted / found) if found > 0 else None
    return SourceResponse(
        id=str(source.id),
        type=source.type,
        identifier=source.identifier,
        name=source.name,
        is_active=source.is_active,
        priority=source.priority,
        parse_interval_minutes=source.parse_interval_minutes,
        total_parsed=source.total_parsed,
        total_errors=source.total_errors,
        consecutive_errors=source.consecutive_errors,
        last_parsed_at=source.last_parsed_at,
        created_at=source.created_at,
        updated_at=source.updated_at,
        metrics_7d=SourceMetric7d(
            listings_found=found,
            listings_extracted=extracted,
            listings_failed=int(m.get("listings_failed", 0) or 0),
            dupes_filtered=int(m.get("dupes_filtered", 0) or 0),
            ai_failed=int(m.get("ai_failed", 0) or 0),
            notified=int(m.get("notified", 0) or 0),
            extraction_success_rate=rate,
        ),
    )


# ── endpoints ─────────────────────────────────────────────────────────


@router.get(
    "/sources",
    response_model=List[SourceResponse],
    summary="List parser sources with 7-day metrics",
)
async def list_sources(
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List every source. The 7-day metric block aggregates the last 7
    daily rows from ``source_metric``; missing rows count as zero."""
    sources = (
        await db.execute(
            select(ParserSource).order_by(ParserSource.priority.desc(), ParserSource.identifier)
        )
    ).scalars().all()

    if not sources:
        return []

    cutoff = datetime.utcnow() - timedelta(days=7)

    metrics = (
        await db.execute(
            select(
                SourceMetric.source_id,
                func.coalesce(func.sum(SourceMetric.listings_found), 0).label("listings_found"),
                func.coalesce(func.sum(SourceMetric.listings_extracted), 0).label("listings_extracted"),
                func.coalesce(func.sum(SourceMetric.listings_failed), 0).label("listings_failed"),
                func.coalesce(func.sum(SourceMetric.dupes_filtered), 0).label("dupes_filtered"),
                func.coalesce(func.sum(SourceMetric.ai_failed), 0).label("ai_failed"),
                func.coalesce(func.sum(SourceMetric.notified), 0).label("notified"),
            )
            .where(SourceMetric.day >= cutoff)
            .group_by(SourceMetric.source_id)
        )
    ).all()
    by_source = {row.source_id: dict(row._mapping) for row in metrics}

    return [
        _serialise(s, by_source.get(s.id, {})) for s in sources
    ]


@router.post(
    "/sources",
    response_model=SourceResponse,
    status_code=201,
    summary="Add a new parser source",
)
async def create_source(
    body: SourceCreate,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = (
        await db.execute(
            select(ParserSource.id).where(ParserSource.identifier == body.identifier)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise BadRequestException("Source with this identifier already exists")

    source = ParserSource(
        type=body.type,
        identifier=body.identifier,
        name=body.name,
        priority=body.priority,
        parse_interval_minutes=body.parse_interval_minutes,
        is_active=body.is_active,
        config={},
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return _serialise(source, {})


@router.get(
    "/sources/{source_id}",
    response_model=dict,
    summary="Single source with last-30-day daily breakdown",
)
async def get_source(
    source_id: UUID,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    source = (
        await db.execute(select(ParserSource).where(ParserSource.id == source_id))
    ).scalar_one_or_none()
    if source is None:
        raise NotFoundException("ParserSource", str(source_id))

    cutoff = datetime.utcnow() - timedelta(days=30)
    daily_rows = (
        await db.execute(
            select(SourceMetric)
            .where(SourceMetric.source_id == source_id, SourceMetric.day >= cutoff)
            .order_by(SourceMetric.day.asc())
        )
    ).scalars().all()

    cutoff7 = datetime.utcnow() - timedelta(days=7)
    agg7 = (
        await db.execute(
            select(
                func.coalesce(func.sum(SourceMetric.listings_found), 0).label("listings_found"),
                func.coalesce(func.sum(SourceMetric.listings_extracted), 0).label("listings_extracted"),
                func.coalesce(func.sum(SourceMetric.listings_failed), 0).label("listings_failed"),
                func.coalesce(func.sum(SourceMetric.dupes_filtered), 0).label("dupes_filtered"),
                func.coalesce(func.sum(SourceMetric.ai_failed), 0).label("ai_failed"),
                func.coalesce(func.sum(SourceMetric.notified), 0).label("notified"),
            ).where(
                SourceMetric.source_id == source_id,
                SourceMetric.day >= cutoff7,
            )
        )
    ).one()

    return {
        "source": _serialise(source, dict(agg7._mapping)).model_dump(),
        "daily_30d": [
            SourceDailyMetric(
                day=r.day,
                listings_found=r.listings_found,
                listings_extracted=r.listings_extracted,
                listings_failed=r.listings_failed,
                dupes_filtered=r.dupes_filtered,
                ai_failed=r.ai_failed,
                notified=r.notified,
            ).model_dump()
            for r in daily_rows
        ],
    }


@router.get(
    "/sources/{source_id}/metrics",
    response_model=SourceMetricsRangeResponse,
    summary="Per-day metrics for a window (days=1..90).",
)
async def get_source_metrics(
    source_id: UUID,
    days: int = Query(7, ge=1, le=90),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Return totals + a per-day array for the last ``days`` days.

    Used by the admin "metrics" drawer (defaults to 7 days, configurable
    up to 90). Missing days are not back-filled with zeroes; the UI
    shows them as gaps in the chart.
    """
    exists = (
        await db.execute(select(ParserSource.id).where(ParserSource.id == source_id))
    ).scalar_one_or_none()
    if exists is None:
        raise NotFoundException("ParserSource", str(source_id))

    cutoff = datetime.utcnow() - timedelta(days=days)

    daily_rows = (
        await db.execute(
            select(SourceMetric)
            .where(SourceMetric.source_id == source_id, SourceMetric.day >= cutoff)
            .order_by(SourceMetric.day.asc())
        )
    ).scalars().all()

    totals = (
        await db.execute(
            select(
                func.coalesce(func.sum(SourceMetric.listings_found), 0).label("listings_found"),
                func.coalesce(func.sum(SourceMetric.listings_extracted), 0).label("listings_extracted"),
                func.coalesce(func.sum(SourceMetric.listings_failed), 0).label("listings_failed"),
                func.coalesce(func.sum(SourceMetric.dupes_filtered), 0).label("dupes_filtered"),
                func.coalesce(func.sum(SourceMetric.ai_failed), 0).label("ai_failed"),
                func.coalesce(func.sum(SourceMetric.notified), 0).label("notified"),
            ).where(
                SourceMetric.source_id == source_id,
                SourceMetric.day >= cutoff,
            )
        )
    ).one()
    t = dict(totals._mapping)
    found = int(t["listings_found"] or 0)
    extracted = int(t["listings_extracted"] or 0)
    rate = (extracted / found) if found > 0 else None

    return SourceMetricsRangeResponse(
        days=days,
        totals=SourceMetric7d(
            listings_found=found,
            listings_extracted=extracted,
            listings_failed=int(t["listings_failed"] or 0),
            dupes_filtered=int(t["dupes_filtered"] or 0),
            ai_failed=int(t["ai_failed"] or 0),
            notified=int(t["notified"] or 0),
            extraction_success_rate=rate,
        ),
        daily=[
            SourceDailyMetric(
                day=r.day,
                listings_found=r.listings_found,
                listings_extracted=r.listings_extracted,
                listings_failed=r.listings_failed,
                dupes_filtered=r.dupes_filtered,
                ai_failed=r.ai_failed,
                notified=r.notified,
            )
            for r in daily_rows
        ],
    )


@router.patch(
    "/sources/{source_id}",
    response_model=SourceResponse,
    summary="Update source — name / priority / interval / is_active",
)
async def update_source(
    source_id: UUID,
    body: SourceUpdate,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    source = (
        await db.execute(select(ParserSource).where(ParserSource.id == source_id))
    ).scalar_one_or_none()
    if source is None:
        raise NotFoundException("ParserSource", str(source_id))

    if body.name is not None:
        source.name = body.name
    if body.priority is not None:
        source.priority = body.priority
    if body.parse_interval_minutes is not None:
        source.parse_interval_minutes = body.parse_interval_minutes
    if body.is_active is not None:
        source.is_active = body.is_active

    await db.commit()
    await db.refresh(source)

    cutoff = datetime.utcnow() - timedelta(days=7)
    metrics = (
        await db.execute(
            select(
                func.coalesce(func.sum(SourceMetric.listings_found), 0).label("listings_found"),
                func.coalesce(func.sum(SourceMetric.listings_extracted), 0).label("listings_extracted"),
                func.coalesce(func.sum(SourceMetric.listings_failed), 0).label("listings_failed"),
                func.coalesce(func.sum(SourceMetric.dupes_filtered), 0).label("dupes_filtered"),
                func.coalesce(func.sum(SourceMetric.ai_failed), 0).label("ai_failed"),
                func.coalesce(func.sum(SourceMetric.notified), 0).label("notified"),
            ).where(
                SourceMetric.source_id == source_id,
                SourceMetric.day >= cutoff,
            )
        )
    ).one()
    return _serialise(source, dict(metrics._mapping))


@router.post(
    "/sources/{source_id}/toggle",
    response_model=SourceResponse,
    summary="Flip is_active",
)
async def toggle_source(
    source_id: UUID,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Single-call enable / disable. Returns the row in its new state.

    Cheaper for the UI than a full PATCH body, and the crawler's tick
    will pick up the change on its next refresh.
    """
    source = (
        await db.execute(select(ParserSource).where(ParserSource.id == source_id))
    ).scalar_one_or_none()
    if source is None:
        raise NotFoundException("ParserSource", str(source_id))
    source.is_active = not source.is_active
    await db.commit()
    await db.refresh(source)

    cutoff = datetime.utcnow() - timedelta(days=7)
    metrics = (
        await db.execute(
            select(
                func.coalesce(func.sum(SourceMetric.listings_found), 0).label("listings_found"),
                func.coalesce(func.sum(SourceMetric.listings_extracted), 0).label("listings_extracted"),
                func.coalesce(func.sum(SourceMetric.listings_failed), 0).label("listings_failed"),
                func.coalesce(func.sum(SourceMetric.dupes_filtered), 0).label("dupes_filtered"),
                func.coalesce(func.sum(SourceMetric.ai_failed), 0).label("ai_failed"),
                func.coalesce(func.sum(SourceMetric.notified), 0).label("notified"),
                func.coalesce(func.sum(SourceMetric.notified), 0).label("notified"),
            ).where(
                SourceMetric.source_id == source_id,
                SourceMetric.day >= cutoff,
            )
        )
    ).one()
    return _serialise(source, dict(metrics._mapping))


@router.delete(
    "/sources/{source_id}",
    status_code=204,
    summary="Hard-delete a source (cascades to its metrics)",
)
async def delete_source(
    source_id: UUID,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    source = (
        await db.execute(select(ParserSource).where(ParserSource.id == source_id))
    ).scalar_one_or_none()
    if source is None:
        raise NotFoundException("ParserSource", str(source_id))
    await db.delete(source)
    await db.commit()


@router.post(
    "/sources/{source_id}/metrics",
    status_code=204,
    summary="Crawler metric writeback (UPSERT-merge per day)",
)
async def write_source_metric(
    source_id: UUID,
    body: SourceMetricIn,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Upsert a daily metric row.

    The same crawler can call this multiple times per day; the row's
    counters get *added*, not replaced, so each call submits the delta
    accumulated since the previous call. The unique index on
    ``(source_id, day)`` enforces one row per day.
    """
    exists = (
        await db.execute(select(ParserSource.id).where(ParserSource.id == source_id))
    ).scalar_one_or_none()
    if exists is None:
        raise NotFoundException("ParserSource", str(source_id))

    day = (body.day or datetime.utcnow()).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    await db.execute(
        text(
            """
            INSERT INTO source_metric (
                source_id, day, listings_found, listings_extracted,
                listings_failed, dupes_filtered, ai_failed, notified
            )
            VALUES (
                :sid, :day, :found, :extracted, :failed, :dupes, :ai_failed, :notified
            )
            ON CONFLICT (source_id, day) DO UPDATE
              SET listings_found     = source_metric.listings_found     + EXCLUDED.listings_found,
                  listings_extracted = source_metric.listings_extracted + EXCLUDED.listings_extracted,
                  listings_failed    = source_metric.listings_failed    + EXCLUDED.listings_failed,
                  dupes_filtered     = source_metric.dupes_filtered     + EXCLUDED.dupes_filtered,
                  ai_failed          = source_metric.ai_failed          + EXCLUDED.ai_failed,
                  notified           = source_metric.notified           + EXCLUDED.notified,
                  updated_at         = now()
            """
        ),
        {
            "sid": source_id,
            "day": day,
            "found": body.listings_found,
            "extracted": body.listings_extracted,
            "failed": body.listings_failed,
            "dupes": body.dupes_filtered,
            "ai_failed": body.ai_failed,
            "notified": body.notified,
        },
    )
    await db.commit()
