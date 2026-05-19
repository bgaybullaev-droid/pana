"""Block F V2.0 F5b — admin AI quality surface.

Seven admin-only endpoints under ``/admin/ai/*``:
    GET  /admin/ai/generations              — paginated browse
    GET  /admin/ai/generations/{id}         — full row (prompt+response)
    GET  /admin/ai/feedback                 — feedback queue
    POST /admin/ai/feedback/{id}/handle     — mark handled
    GET  /admin/ai/prompts                  — versions per kind
    POST /admin/ai/prompts                  — create new version (inactive)
    POST /admin/ai/prompts/{id}/activate    — atomic active-swap

Plus one auxiliary read endpoint that the FE uses for the dashboard
landing tab: ``GET /admin/ai/metrics`` — 24h aggregates + alert flags.
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_admin
from app.core.config import settings
from app.db.database import get_db
from app.db.models import (
    AIGeneration,
    AIGenerationFeedback,
    PromptTemplate,
    User,
)
from app.schemas.ai_quality import (
    AIFeedbackList,
    AIFeedbackResponse,
    AIGenerationDetail,
    AIGenerationList,
    AIGenerationSummary,
    AIMetricsSnapshot,
    PromptTemplateCreate,
    PromptTemplateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/ai", tags=["Admin AI"])

_PAGE_SIZE_DEFAULT = 25
_PAGE_SIZE_MAX = 100


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "invalid_date", "field": value},
        ) from exc


# ────────────────────────────────────────────────────────────
# Generations
# ────────────────────────────────────────────────────────────


@router.get("/generations", response_model=AIGenerationList)
async def list_generations(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    lang: Optional[str] = Query(default=None, max_length=12),
    model: Optional[str] = Query(default=None, max_length=64),
    outcome: Optional[str] = Query(default=None, max_length=32),
    has_feedback: Optional[bool] = Query(default=None),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=_PAGE_SIZE_DEFAULT, ge=1, le=_PAGE_SIZE_MAX),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AIGenerationList:
    """Paginated browse of every recorded LLM call. Filters compose."""
    conditions = []
    if (dt := _parse_date(date_from)) is not None:
        conditions.append(AIGeneration.created_at >= dt)
    if (dt := _parse_date(date_to)) is not None:
        conditions.append(AIGeneration.created_at <= dt)
    if model:
        conditions.append(AIGeneration.model == model)
    if outcome:
        conditions.append(AIGeneration.outcome == outcome)
    # `lang` filter joins through prompt_template.kind which encodes
    # language in convention `listing_description_<lang>`. If the
    # registry kind is single-locale, we filter on kind ending.
    if lang:
        conditions.append(
            AIGeneration.prompt_template_id.in_(
                select(PromptTemplate.id).where(
                    PromptTemplate.kind.endswith(f"_{lang}")
                )
            )
        )
    if has_feedback is True:
        conditions.append(
            AIGeneration.id.in_(
                select(AIGenerationFeedback.generation_id).where(
                    AIGenerationFeedback.generation_id.is_not(None)
                )
            )
        )
    elif has_feedback is False:
        conditions.append(
            AIGeneration.id.not_in(
                select(AIGenerationFeedback.generation_id).where(
                    AIGenerationFeedback.generation_id.is_not(None)
                )
            )
        )

    where_clause = and_(*conditions) if conditions else None
    count_stmt = select(func.count(AIGeneration.id))
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)
    total = int((await db.execute(count_stmt)).scalar() or 0)

    list_stmt = select(AIGeneration).order_by(AIGeneration.created_at.desc())
    if where_clause is not None:
        list_stmt = list_stmt.where(where_clause)
    list_stmt = list_stmt.offset((page - 1) * page_size).limit(page_size)
    rows = list((await db.execute(list_stmt)).scalars().all())

    return AIGenerationList(
        total=total,
        page=page,
        items=[AIGenerationSummary.model_validate(r) for r in rows],
    )


@router.get(
    "/generations/{generation_id}", response_model=AIGenerationDetail
)
async def get_generation(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AIGenerationDetail:
    """Full row including the LLM prompt and response. Admin-only."""
    row = (
        await db.execute(
            select(AIGeneration).where(AIGeneration.id == generation_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "generation_not_found"},
        )
    return AIGenerationDetail.model_validate(row)


# ────────────────────────────────────────────────────────────
# Feedback queue
# ────────────────────────────────────────────────────────────


@router.get("/feedback", response_model=AIFeedbackList)
async def list_feedback(
    handled: bool = Query(default=False),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=_PAGE_SIZE_DEFAULT, ge=1, le=_PAGE_SIZE_MAX),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AIFeedbackList:
    """Paginated feedback queue. Default ``handled=false`` matches the
    spec — admin clears items by calling the ``/handle`` endpoint."""
    base = select(AIGenerationFeedback).where(
        AIGenerationFeedback.handled.is_(handled)
    )
    total = int(
        (
            await db.execute(
                select(func.count(AIGenerationFeedback.id)).where(
                    AIGenerationFeedback.handled.is_(handled)
                )
            )
        ).scalar()
        or 0
    )
    rows = list(
        (
            await db.execute(
                base.order_by(AIGenerationFeedback.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return AIFeedbackList(
        total=total,
        page=page,
        items=[AIFeedbackResponse.model_validate(r) for r in rows],
    )


@router.post(
    "/feedback/{feedback_id}/handle", response_model=AIFeedbackResponse
)
async def handle_feedback(
    feedback_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AIFeedbackResponse:
    """Mark a feedback row as handled. Idempotent — calling twice on
    an already-handled row is a no-op that still returns the row."""
    row = (
        await db.execute(
            select(AIGenerationFeedback).where(
                AIGenerationFeedback.id == feedback_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "feedback_not_found"},
        )
    if not row.handled:
        row.handled = True
        await db.commit()
        await db.refresh(row)
        logger.info(
            "admin_ai.feedback_handled id=%s by_admin=%s", feedback_id, admin.id
        )
    return AIFeedbackResponse.model_validate(row)


# ────────────────────────────────────────────────────────────
# Prompt versions
# ────────────────────────────────────────────────────────────


@router.get(
    "/prompts", response_model=list[PromptTemplateResponse]
)
async def list_prompts(
    kind: Optional[str] = Query(default=None, max_length=48),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> list[PromptTemplateResponse]:
    """List prompt versions newest-first. Optionally filter by kind."""
    stmt = select(PromptTemplate).order_by(
        PromptTemplate.kind.asc(), PromptTemplate.version.desc()
    )
    if kind:
        stmt = stmt.where(PromptTemplate.kind == kind)
    rows = list((await db.execute(stmt)).scalars().all())
    return [PromptTemplateResponse.model_validate(r) for r in rows]


@router.post(
    "/prompts",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(
    payload: PromptTemplateCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> PromptTemplateResponse:
    """Create a new version for ``payload.kind``. Always inserted with
    ``is_active=False`` and ``version = max(version) + 1`` so the
    currently-active prompt is never disrupted by the create alone —
    the separate ``/activate`` call performs the atomic swap."""
    max_version = (
        await db.execute(
            select(func.max(PromptTemplate.version)).where(
                PromptTemplate.kind == payload.kind
            )
        )
    ).scalar() or 0
    row = PromptTemplate(
        kind=payload.kind,
        version=int(max_version) + 1,
        body=payload.body,
        model_hint=payload.model_hint,
        notes=payload.notes,
        is_active=False,
        created_by_user_id=admin.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info(
        "admin_ai.prompt_created id=%s kind=%s version=%d by_admin=%s",
        row.id,
        row.kind,
        row.version,
        admin.id,
    )
    return PromptTemplateResponse.model_validate(row)


@router.post(
    "/prompts/{prompt_id}/activate", response_model=PromptTemplateResponse
)
async def activate_prompt(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> PromptTemplateResponse:
    """Atomically flip ``is_active=true`` on the target row and
    ``false`` on every other row of the same kind.

    Single statement:

        UPDATE prompt_templates
        SET is_active = (id = :new_id)
        WHERE kind = :kind

    The partial unique index ``(kind) WHERE is_active`` would catch any
    concurrent activation that managed to land two ``true`` rows at the
    same time, so the swap is safe under contention.
    """
    target = (
        await db.execute(
            select(PromptTemplate).where(PromptTemplate.id == prompt_id)
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "prompt_not_found"},
        )

    await db.execute(
        PromptTemplate.__table__.update()
        .where(PromptTemplate.kind == target.kind)
        .values(is_active=case((PromptTemplate.id == prompt_id, True), else_=False))
    )
    await db.commit()
    await db.refresh(target)
    logger.info(
        "admin_ai.prompt_activated id=%s kind=%s version=%d by_admin=%s",
        target.id,
        target.kind,
        target.version,
        admin.id,
    )
    return PromptTemplateResponse.model_validate(target)


# ────────────────────────────────────────────────────────────
# Metrics overview
# ────────────────────────────────────────────────────────────


@router.get("/metrics", response_model=AIMetricsSnapshot)
async def metrics_snapshot(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> AIMetricsSnapshot:
    """24h rolling aggregate used by the admin dashboard's landing tab."""
    window = datetime.utcnow() - timedelta(hours=24)
    rows = list(
        (
            await db.execute(
                select(
                    AIGeneration.outcome,
                    AIGeneration.duration_ms,
                    AIGeneration.cost_usd_micros,
                ).where(AIGeneration.created_at >= window)
            )
        ).all()
    )
    total = len(rows)
    ok = sum(1 for r in rows if r.outcome == "ok")
    fallback = sum(1 for r in rows if r.outcome == "fallback_template")
    failure = total - ok - fallback
    durations = [int(r.duration_ms) for r in rows if r.duration_ms is not None]
    cost_micros = sum(int(r.cost_usd_micros or 0) for r in rows)

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_cost_micros = int(
        (
            await db.execute(
                select(func.coalesce(func.sum(AIGeneration.cost_usd_micros), 0)).where(
                    AIGeneration.created_at >= today_start
                )
            )
        ).scalar()
        or 0
    )

    bad_feedback_count = int(
        (
            await db.execute(
                select(func.count(AIGenerationFeedback.id)).where(
                    AIGenerationFeedback.created_at >= window
                )
            )
        ).scalar()
        or 0
    )
    bad_feedback_rate = (bad_feedback_count / total) if total else 0.0

    # Alert states are read from Redis flags (see quality_alerts).
    from app.services.quality_alerts import current_alert_states

    alert_states = await current_alert_states()

    return AIMetricsSnapshot(
        window_hours=24,
        total_generations=total,
        ok_count=ok,
        fallback_count=fallback,
        failure_count=failure,
        bad_feedback_count=bad_feedback_count,
        bad_feedback_rate=round(bad_feedback_rate, 4),
        duration_p50_ms=(int(statistics.median(durations)) if durations else None),
        duration_p95_ms=(
            int(_percentile(durations, 95)) if durations else None
        ),
        cost_usd_today=round(today_cost_micros / 1_000_000, 4),
        alert_states=alert_states,
    )


def _percentile(values: list[int], pct: int) -> float:
    """Pure-Python percentile (no numpy dep). 95th percentile of N=5
    values is the index ``ceil(0.95 * 5) - 1 = 4`` element of the
    sorted list."""
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(pct / 100.0 * (len(s) - 1)))))
    return float(s[k])
