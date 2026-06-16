"""Block D (FU5) — admin read-only view of bot search-query telemetry.

One endpoint under ``/admin/search-telemetry``:
    GET  /admin/search-telemetry?days=7

Surfaces the ``bot_search_queries`` capture (written fire-and-forget by
``workers.tasks.telemetry``) for product analysis without SSH/SQL on the
VPS: per-source totals with empty-result and unrecognized shares, the
top unrecognized queries (parser-dictionary backlog) and a recent tail.

Read-only: there is no write surface — telemetry is append-only and
pruned by the ``prune_bot_search_queries`` cron.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_admin
from app.db.database import get_db
from app.db.models import BotSearchQuery, User

router = APIRouter(
    prefix="/admin/search-telemetry", tags=["Admin — Search Telemetry (D/FU5)"]
)


class SourceBreakdown(BaseModel):
    source: str
    total: int
    empty: int
    unrecognized: int
    empty_pct: float
    unrecognized_pct: float


class UnrecognizedRow(BaseModel):
    raw_text: str
    hits: int


class RecentRow(BaseModel):
    created_at: datetime
    source: str
    raw_text: str
    extracted_fields: List[str]
    results_count: int


class SearchTelemetryResponse(BaseModel):
    days: int
    since: datetime
    total: int
    by_source: List[SourceBreakdown]
    top_unrecognized: List[UnrecognizedRow]
    recent: List[RecentRow]


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0


@router.get("", response_model=SearchTelemetryResponse)
async def get_search_telemetry(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> SearchTelemetryResponse:
    since = datetime.utcnow() - timedelta(days=days)

    # "unrecognized" = parser extracted zero filters (empty JSONB array);
    # "empty" = the search itself returned no listings.
    unrecognized_cond = func.jsonb_array_length(BotSearchQuery.extracted_fields) == 0
    empty_cond = BotSearchQuery.results_count == 0

    source_rows = (
        await db.execute(
            select(
                BotSearchQuery.source,
                func.count().label("total"),
                func.count().filter(empty_cond).label("empty"),
                func.count().filter(unrecognized_cond).label("unrecognized"),
            )
            .where(BotSearchQuery.created_at >= since)
            .group_by(BotSearchQuery.source)
            .order_by(func.count().desc())
        )
    ).all()

    by_source: List[SourceBreakdown] = []
    total_all = 0
    for source, total, empty, unrecognized in source_rows:
        total = int(total or 0)
        empty = int(empty or 0)
        unrecognized = int(unrecognized or 0)
        total_all += total
        by_source.append(
            SourceBreakdown(
                source=source,
                total=total,
                empty=empty,
                unrecognized=unrecognized,
                empty_pct=_pct(empty, total),
                unrecognized_pct=_pct(unrecognized, total),
            )
        )

    unrecognized_rows = (
        await db.execute(
            select(BotSearchQuery.raw_text, func.count().label("hits"))
            .where(BotSearchQuery.created_at >= since, unrecognized_cond)
            .group_by(BotSearchQuery.raw_text)
            .order_by(func.count().desc())
            .limit(50)
        )
    ).all()
    top_unrecognized = [
        UnrecognizedRow(raw_text=raw_text, hits=int(hits))
        for raw_text, hits in unrecognized_rows
    ]

    recent_rows = (
        await db.execute(
            select(BotSearchQuery)
            .where(BotSearchQuery.created_at >= since)
            .order_by(BotSearchQuery.created_at.desc())
            .limit(100)
        )
    ).scalars().all()
    recent = [
        RecentRow(
            created_at=row.created_at,
            source=row.source,
            raw_text=row.raw_text,
            extracted_fields=list(row.extracted_fields or []),
            results_count=row.results_count,
        )
        for row in recent_rows
    ]

    return SearchTelemetryResponse(
        days=days,
        since=since,
        total=total_all,
        by_source=by_source,
        top_unrecognized=top_unrecognized,
        recent=recent,
    )
