"""Block F V2.0 (F5) — DB-stored LLM prompt registry + generation log.

Two responsibilities:

1. ``get_active_prompt(kind)`` — the AI generation worker reads its
   prompt from the DB at task start. Admin activates a new version
   without redeploy via single-statement atomic swap. The partial
   unique index ``uq_prompt_templates_active_per_kind`` guarantees
   ≤1 active per kind so the read is unambiguous.

2. ``record_generation(...)`` — every LLM call (success + failure)
   appends one row to ``ai_generations`` with prompt + response +
   duration + cost + outcome. The recommender/quality-ops surface
   reads this table; it is the only place that writes to it.

Block F engineering constraints applied:

- **Domain doesn't speak transport.** Returns SQLAlchemy models /
  dataclasses; the worker (Celery) and admin API consume the same
  functions.
- **Fail-soft on missing prompt.** ``PromptNotConfigured`` is the
  only exception this module raises; the worker has a hard-coded
  fallback prompt for resilience during seeding gaps.
- **Append-only logging.** ``record_generation`` flushes inside the
  caller's transaction; on the rare error path the caller decides
  whether to rollback or proceed.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AIGeneration, PromptTemplate

logger = logging.getLogger(__name__)


class PromptNotConfigured(Exception):
    """Raised by :func:`get_active_prompt` when no active row exists.

    Callers (the worker) catch this and fall back to a hard-coded
    prompt so production never stalls because of an admin mis-config.
    """


async def get_active_prompt(
    db: AsyncSession,
    kind: str = "listing_description",
) -> PromptTemplate:
    """Return the current active prompt for ``kind``.

    Partial unique index guarantees ≤1 active row per kind, so a
    single-row SELECT is sufficient. Raises :class:`PromptNotConfigured`
    when no active row exists (callers fall back).
    """
    row = await db.execute(
        select(PromptTemplate).where(
            PromptTemplate.kind == kind,
            PromptTemplate.is_active.is_(True),
        )
    )
    obj = row.scalar_one_or_none()
    if obj is None:
        raise PromptNotConfigured(f"No active prompt_templates row for kind={kind!r}")
    return obj


async def record_generation(
    db: AsyncSession,
    *,
    model: str,
    prompt_text: str,
    response_text: str,
    duration_ms: int,
    outcome: str,
    triggered_by: str,
    listing_id: Optional[UUID] = None,
    prompt_template_id: Optional[UUID] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    cost_usd_micros: Optional[int] = None,
) -> AIGeneration:
    """Append one row to ``ai_generations``.

    Caller is responsible for committing the transaction. Errors here
    are logged at WARNING — the recommendation pipeline is
    observational and must never break the primary user flow.

    ``outcome`` is one of:
        ok | fallback_template | timeout | rate_limit | invalid_response

    ``triggered_by`` is one of:
        manual | auto_parser | param_change | manual_retry
    """
    try:
        row = AIGeneration(
            listing_id=listing_id,
            prompt_template_id=prompt_template_id,
            model=model,
            prompt_text=prompt_text,
            response_text=response_text,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd_micros=cost_usd_micros,
            triggered_by=triggered_by,
            outcome=outcome,
        )
        db.add(row)
        await db.flush()
        logger.info(
            "ai_generation.recorded listing=%s outcome=%s model=%s duration_ms=%d",
            listing_id,
            outcome,
            model,
            duration_ms,
        )
        return row
    except Exception:  # pragma: no cover — defensive
        logger.warning(
            "ai_generation.record_failed listing=%s outcome=%s",
            listing_id,
            outcome,
            exc_info=True,
        )
        raise
