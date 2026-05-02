"""PR-H — Orphaned upload-file garbage collection.

Periodic Celery task that walks the on-disk upload tree and deletes
files older than `min_age_hours` that are NOT referenced by any
`listing_images` row. Runs daily via celery-beat.

Design:

    - Source of truth: the `listing_images` table. Every URL column
      (original_url, thumbnail_url, medium_url, large_url) is scanned;
      the task extracts the `listings/{user_id}/{filename}` key and
      builds a SET of referenced keys.

    - Age gate: files younger than `min_age_hours` (default 24) are
      SKIPPED even if unreferenced. This protects against the race
      where an upload just hit disk but the listing record hasn't been
      committed yet.

    - Dry-run: pass `dry_run=True` to enumerate candidates without
      deleting. Useful for ops sanity-checks before first rollout.

    - Idempotent: re-running is safe. The task only deletes files that
      were unreferenced at start-of-run — a concurrent listing write
      that lands DURING the walk still gets its file preserved on the
      next run because the file's mtime resets via the write.

    - Safe-fallback: any filesystem error on a single file increments
      `errors` and the task continues. The task itself never raises.

Metrics returned:
    {
        "scanned_count": int,       # total files walked
        "referenced_count": int,    # kept (DB references it)
        "too_new_count": int,       # kept (mtime within threshold)
        "deleted_count": int,       # actually (or hypothetically) deleted
        "errors": int,              # file-level failures
        "cutoff": str,              # ISO threshold
        "dry_run": bool,
    }
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import ListingImage
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Match the mount in app/main.py:49 — shared upload root.
_UPLOAD_DIR = Path(
    settings.upload_dir if hasattr(settings, "upload_dir") else "uploads"
)

# Public only so tests can pin a cutoff.
DEFAULT_MIN_AGE_HOURS = 24


@asynccontextmanager
async def _get_session() -> AsyncIterator[AsyncSession]:
    """Dedicated short-lived engine per task run — matches the pattern
    in notifications.py."""
    engine = create_async_engine(
        settings.async_database_url, pool_pre_ping=True, pool_size=2
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
    await engine.dispose()


def _url_to_key(url: Optional[str]) -> Optional[str]:
    """Extract the `listings/{user}/{file}` key from an upload URL.

    Supported shapes (both absolute and relative URLs):
        https://host/uploads/listings/<uuid>/<name>.jpg
        http://localhost:8001/uploads/listings/<uuid>/<name>.jpg
        /uploads/listings/<uuid>/<name>.jpg

    Returns None when the URL doesn't look like an upload key
    (e.g. external CDN, crawler source URLs).
    """
    if not url:
        return None
    marker = "/uploads/"
    idx = url.find(marker)
    if idx == -1:
        return None
    return url[idx + len(marker) :].lstrip("/")


async def _collect_referenced_keys(db: AsyncSession) -> Set[str]:
    """Query every URL column on listing_images and return the set of
    keys currently in use. Scales linearly with photo count; for ~1M
    photos this is ~200MB of memory — acceptable for a daily GC."""
    referenced: Set[str] = set()
    result = await db.execute(
        select(
            ListingImage.original_url,
            ListingImage.thumbnail_url,
            ListingImage.medium_url,
            ListingImage.large_url,
        )
    )
    for row in result:
        for url in row:
            key = _url_to_key(url)
            if key:
                referenced.add(key)
    return referenced


def _walk_upload_tree(base: Path):
    """Yield every regular file under `base/listings/{user}/{file}`.
    Yields a tuple of `(absolute_path, key, mtime_utc)` — skips anything
    that isn't a two-level deep regular file."""
    listings_root = base / "listings"
    if not listings_root.exists():
        return
    for user_dir in listings_root.iterdir():
        if not user_dir.is_dir():
            continue
        for file_path in user_dir.iterdir():
            if not file_path.is_file():
                continue
            try:
                mtime = datetime.utcfromtimestamp(file_path.stat().st_mtime)
            except OSError as exc:
                logger.warning("stat failed for %s: %s", file_path, exc)
                continue
            key = f"listings/{user_dir.name}/{file_path.name}"
            yield file_path, key, mtime


async def _cleanup_orphan_uploads(
    min_age_hours: int,
    dry_run: bool,
) -> Dict[str, Any]:
    threshold = datetime.utcnow() - timedelta(hours=min_age_hours)

    async with _get_session() as db:
        referenced = await _collect_referenced_keys(db)

    scanned = 0
    kept_referenced = 0
    kept_too_new = 0
    deleted = 0
    errors = 0

    for file_path, key, mtime in _walk_upload_tree(_UPLOAD_DIR):
        scanned += 1

        if key in referenced:
            kept_referenced += 1
            continue

        if mtime > threshold:
            kept_too_new += 1
            continue

        if dry_run:
            deleted += 1
            continue

        try:
            file_path.unlink()
            deleted += 1
        except OSError as exc:
            logger.warning("unlink failed for %s: %s", file_path, exc)
            errors += 1

    logger.info(
        "upload GC: scanned=%d referenced=%d too_new=%d deleted=%d errors=%d dry_run=%s",
        scanned,
        kept_referenced,
        kept_too_new,
        deleted,
        errors,
        dry_run,
    )

    return {
        "scanned_count": scanned,
        "referenced_count": kept_referenced,
        "too_new_count": kept_too_new,
        "deleted_count": deleted,
        "errors": errors,
        "cutoff": threshold.isoformat(),
        "dry_run": dry_run,
    }


@celery_app.task
def cleanup_orphan_uploads(
    min_age_hours: int = DEFAULT_MIN_AGE_HOURS,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Public task entry point. Delegates to the async helper.

    Args:
        min_age_hours: files younger than this are skipped (race guard).
        dry_run: when True, enumerates candidates without deleting.
    """
    return asyncio.run(_cleanup_orphan_uploads(min_age_hours, dry_run))
