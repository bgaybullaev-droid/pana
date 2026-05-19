"""Phase-2 — nightly duplicate-account detection signals.

Single Celery task ``run_suspicion_signals`` that calls
``services.suspicions.run_all_signals`` against an async session.
Scheduled via Celery Beat at 02:30 daily (see ``celery_app``). The
underlying service functions are idempotent — only new collisions /
similar-name pairs that don't already have an open suspicion are
inserted, so a re-run is safe.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services.suspicions import run_all_signals
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def run_suspicion_signals() -> Dict[str, Any]:
    """Run all duplicate-account detection signals.

    Returns ``{"phone_collision": N, "similar_names": M}`` so the
    Celery result log shows how many suspicions each signal emitted
    on this run.
    """
    return asyncio.run(_run_all())


async def _run_all() -> Dict[str, Any]:
    engine = create_async_engine(
        settings.async_database_url, pool_pre_ping=True, pool_size=2
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_maker() as session:
            result = await run_all_signals(session)
            logger.info("suspicions.task.done result=%s", result)
            return result
    finally:
        await engine.dispose()
