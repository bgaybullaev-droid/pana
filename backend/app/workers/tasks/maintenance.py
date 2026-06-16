"""Block D V2.0 — maintenance / pruning Celery tasks.

Single-file home for periodic cleanup jobs introduced by Block D.
Currently:
- ``prune_behavioral_signals`` — drop rows older than 180 days from
  the personalization-signal feed (D2 retention policy).

Operational notes
=================
Tasks are scheduled via Celery Beat. The schedule lives in
``app.workers.celery_app`` so all periodic-task wiring is in one
place. Failures log at WARNING and never block.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import BehavioralSignal
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


_BEHAVIORAL_SIGNALS_RETENTION_DAYS = 180


async def _with_session(fn):
    engine = create_async_engine(
        settings.async_database_url, pool_pre_ping=True, pool_size=2
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_maker() as session:
            return await fn(session)
    finally:
        await engine.dispose()


@celery_app.task
def prune_behavioral_signals() -> Dict[str, Any]:
    """Block D D2 — delete ``behavioral_signals`` rows older than 180 days.

    Idempotent; safe to run repeatedly. Returns a small dict for log
    scraping: ``{"deleted_rows": N, "cutoff": "2025-..."}``.
    """
    return asyncio.run(_prune_behavioral_signals())


async def _prune_behavioral_signals() -> Dict[str, Any]:
    cutoff = datetime.utcnow() - timedelta(days=_BEHAVIORAL_SIGNALS_RETENTION_DAYS)

    async def _run(db: AsyncSession) -> Dict[str, Any]:
        before_q = await db.execute(
            select(func.count())
            .select_from(BehavioralSignal)
            .where(BehavioralSignal.created_at < cutoff)
        )
        candidate_count = int(before_q.scalar_one() or 0)
        if candidate_count == 0:
            logger.info(
                "maintenance.prune_signals: nothing to prune (cutoff=%s)",
                cutoff.isoformat(),
            )
            return {"deleted_rows": 0, "cutoff": cutoff.isoformat()}

        await db.execute(
            delete(BehavioralSignal).where(BehavioralSignal.created_at < cutoff)
        )
        await db.commit()
        logger.info(
            "maintenance.prune_signals: deleted=%d cutoff=%s",
            candidate_count,
            cutoff.isoformat(),
        )
        return {"deleted_rows": candidate_count, "cutoff": cutoff.isoformat()}

    try:
        return await _with_session(_run)
    except Exception as exc:
        logger.warning(
            "maintenance.prune_signals_failed: %s", exc, exc_info=True
        )
        return {"deleted_rows": 0, "error": str(exc)}


# =============================================================================
# Block D V2.0 (FU5) — bot_search_queries 90-day retention
# =============================================================================


_BOT_SEARCH_QUERIES_RETENTION_DAYS = 90


@celery_app.task
def prune_bot_search_queries() -> Dict[str, Any]:
    """Block D FU5 — delete ``bot_search_queries`` rows older than 90 days.

    Append-only telemetry; trimming by ``created_at`` keeps the table
    bounded while preserving the recent window product analysis reads.
    Idempotent; safe to run repeatedly. Returns ``{"deleted_rows": N,
    "cutoff": "..."}`` for log scraping.
    """
    return asyncio.run(_prune_bot_search_queries())


async def _prune_bot_search_queries() -> Dict[str, Any]:
    from app.db.models import BotSearchQuery

    cutoff = datetime.utcnow() - timedelta(days=_BOT_SEARCH_QUERIES_RETENTION_DAYS)

    async def _run(db: AsyncSession) -> Dict[str, Any]:
        before_q = await db.execute(
            select(func.count())
            .select_from(BotSearchQuery)
            .where(BotSearchQuery.created_at < cutoff)
        )
        candidate_count = int(before_q.scalar_one() or 0)
        if candidate_count == 0:
            logger.info(
                "maintenance.prune_bot_search_queries: nothing to prune (cutoff=%s)",
                cutoff.isoformat(),
            )
            return {"deleted_rows": 0, "cutoff": cutoff.isoformat()}

        await db.execute(
            delete(BotSearchQuery).where(BotSearchQuery.created_at < cutoff)
        )
        await db.commit()
        logger.info(
            "maintenance.prune_bot_search_queries: deleted=%d cutoff=%s",
            candidate_count,
            cutoff.isoformat(),
        )
        return {"deleted_rows": candidate_count, "cutoff": cutoff.isoformat()}

    try:
        return await _with_session(_run)
    except Exception as exc:
        logger.warning(
            "maintenance.prune_bot_search_queries_failed: %s", exc, exc_info=True
        )
        return {"deleted_rows": 0, "error": str(exc)}


# =============================================================================
# Block F F1 — abandoned-draft purge
# =============================================================================


@celery_app.task
def purge_abandoned_drafts() -> Dict[str, Any]:
    """Block F F1 — delete ``Listing`` rows where ``status=DRAFT`` and
    ``updated_at`` is older than ``settings.f1_draft_lifetime_days``.

    Idempotent; safe to run repeatedly. Returns ``{"deleted_rows": N,
    "cutoff": "..."}`` for log scraping. Photos are orphan-collected by
    the existing ``uploads_gc.cleanup_orphan_uploads`` cron.

    DRAFT rows do not count against the seller's listings_count quota
    (Block C C2 grandfathering) — counter only increments on the first
    DRAFT → ACTIVE flip. So purging an abandoned draft is a clean delete
    with no counter-rollback needed.
    """
    return asyncio.run(_purge_abandoned_drafts())


async def _purge_abandoned_drafts() -> Dict[str, Any]:
    from app.db.models import Listing, ListingStatus

    lifetime_days = settings.f1_draft_lifetime_days
    cutoff = datetime.utcnow() - timedelta(days=lifetime_days)

    async def _run(db: AsyncSession) -> Dict[str, Any]:
        before_q = await db.execute(
            select(func.count())
            .select_from(Listing)
            .where(
                Listing.status == ListingStatus.DRAFT,
                Listing.updated_at < cutoff,
                Listing.deleted_at.is_(None),
            )
        )
        candidate_count = int(before_q.scalar_one() or 0)
        if candidate_count == 0:
            logger.info(
                "maintenance.purge_drafts: nothing to purge (cutoff=%s, lifetime_days=%d)",
                cutoff.isoformat(),
                lifetime_days,
            )
            return {
                "deleted_rows": 0,
                "cutoff": cutoff.isoformat(),
                "lifetime_days": lifetime_days,
            }

        # Hard delete — DRAFT listings are unpublished WIP and never
        # had B2C surface; no soft-delete semantics required. CASCADE
        # on ListingImage etc. cleans up children.
        await db.execute(
            delete(Listing).where(
                Listing.status == ListingStatus.DRAFT,
                Listing.updated_at < cutoff,
                Listing.deleted_at.is_(None),
            )
        )
        await db.commit()
        logger.info(
            "maintenance.purge_drafts: deleted=%d cutoff=%s lifetime_days=%d",
            candidate_count,
            cutoff.isoformat(),
            lifetime_days,
        )
        return {
            "deleted_rows": candidate_count,
            "cutoff": cutoff.isoformat(),
            "lifetime_days": lifetime_days,
        }

    try:
        return await _with_session(_run)
    except Exception as exc:
        logger.warning(
            "maintenance.purge_drafts_failed: %s", exc, exc_info=True
        )
        return {"deleted_rows": 0, "error": str(exc)}


# =============================================================================
# Block F F5b — ai_generations 90-day retention + quality-threshold cron
# =============================================================================


_AI_GENERATIONS_RETENTION_DAYS = 90


@celery_app.task
def prune_ai_generations() -> Dict[str, Any]:
    """Block F F5b — delete ``ai_generations`` rows older than 90 days.

    Append-only audit log; we trim by ``created_at`` so quality alerts
    based on the last 24h window are never affected. Feedback rows in
    ``ai_generation_feedback`` survive thanks to the FK ``ON DELETE
    SET NULL`` declared in F5a.
    """
    return asyncio.run(_prune_ai_generations())


async def _prune_ai_generations() -> Dict[str, Any]:
    from app.db.models import AIGeneration

    cutoff = datetime.utcnow() - timedelta(days=_AI_GENERATIONS_RETENTION_DAYS)

    async def _run(db: AsyncSession) -> Dict[str, Any]:
        before_q = await db.execute(
            select(func.count())
            .select_from(AIGeneration)
            .where(AIGeneration.created_at < cutoff)
        )
        candidate_count = int(before_q.scalar_one() or 0)
        if candidate_count == 0:
            logger.info(
                "maintenance.prune_ai_generations: nothing to prune (cutoff=%s)",
                cutoff.isoformat(),
            )
            return {"deleted_rows": 0, "cutoff": cutoff.isoformat()}

        await db.execute(
            delete(AIGeneration).where(AIGeneration.created_at < cutoff)
        )
        await db.commit()
        logger.info(
            "maintenance.prune_ai_generations: deleted=%d cutoff=%s",
            candidate_count,
            cutoff.isoformat(),
        )
        return {"deleted_rows": candidate_count, "cutoff": cutoff.isoformat()}

    try:
        return await _with_session(_run)
    except Exception as exc:
        logger.warning(
            "maintenance.prune_ai_generations_failed: %s", exc, exc_info=True
        )
        return {"deleted_rows": 0, "error": str(exc)}


@celery_app.task
def check_quality_thresholds() -> Dict[str, Any]:
    """Block F F5b — evaluate the three quality metrics and notify
    admins via Telegram on healthy→tripped transitions.

    Returns ``{"evaluations": [...], "notified": ["metric", ...]}``.
    The notified list is empty when nothing flipped this run.
    """
    return asyncio.run(_check_quality_thresholds())


async def _check_quality_thresholds() -> Dict[str, Any]:
    from app.services.quality_alerts import (
        check_thresholds,
        maybe_notify_admins,
    )

    async def _run(db: AsyncSession) -> Dict[str, Any]:
        evaluations = await check_thresholds(db)
        notified = await maybe_notify_admins(evaluations)
        return {
            "evaluations": [
                {
                    "metric": ev.metric,
                    "value": ev.value,
                    "threshold": ev.threshold,
                    "tripped": ev.tripped,
                }
                for ev in evaluations
            ],
            "notified": notified,
        }

    try:
        return await _with_session(_run)
    except Exception as exc:
        logger.warning(
            "maintenance.check_quality_thresholds_failed: %s", exc, exc_info=True
        )
        return {"evaluations": [], "notified": [], "error": str(exc)}


# =============================================================================
# Block F V2.0 F3c — sitemap warm-up (drives Cache-Control freshness)
# =============================================================================


@celery_app.task
def rebuild_sitemap_caches() -> Dict[str, Any]:
    """Block F F3c — force a fresh render of the sitemap-index and the
    per-lang listing/filter sitemaps so the next Googlebot/Yandexbot
    crawl gets recent ``<lastmod>`` timestamps without waiting on a
    cold cache miss against the API.

    The route layer already serves ``Cache-Control: public, max-age=900``
    so this task just primes the path; no separate cache store yet.
    Idempotent; safe to run repeatedly.
    """
    return asyncio.run(_rebuild_sitemap_caches())


async def _rebuild_sitemap_caches() -> Dict[str, Any]:
    from app.services.sitemap import (
        SUPPORTED_LANGS,
        build_filters_sitemap,
        build_listings_sitemap,
        build_sitemap_index,
    )

    async def _run(db: AsyncSession) -> Dict[str, Any]:
        # Index first so we know how many listing pages to warm up.
        index_xml = await build_sitemap_index(db)
        warmed: list[str] = ["index"]
        for lang in SUPPORTED_LANGS:
            await build_listings_sitemap(db, lang, page=1)
            await build_filters_sitemap(db, lang)
            warmed.append(f"{lang}-listings-1")
            warmed.append(f"{lang}-filters")
        return {
            "warmed": warmed,
            "index_bytes": len(index_xml),
        }

    try:
        return await _with_session(_run)
    except Exception as exc:
        logger.warning(
            "maintenance.rebuild_sitemap_caches_failed: %s", exc, exc_info=True
        )
        return {"warmed": [], "error": str(exc)}
