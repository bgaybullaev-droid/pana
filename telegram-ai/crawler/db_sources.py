"""DB-backed parser-source loader and metrics writeback.

Block A V2.0 (A8) — replaces the YAML ``channels:`` list as the source
of truth. The crawler reads its channel list from the Postgres
``parser_sources`` table on startup and refreshes periodically; metric
deltas (parsed / saved / failed / duplicates / notified) are written
back to the same table via ``source_metric`` rows so the admin
dashboard surfaces per-source extraction stats.

Connection: same Postgres credentials the backend uses
(``POSTGRES_HOST/PORT/USER/PASSWORD/DB`` env vars; ``DATABASE_URL``
overrides). The crawler runs as its own process so it opens its own
connection pool — there is no shared SQLAlchemy session.

The module exposes three things:
* :func:`load_active_sources` — list of active sources (telegram + olx).
* :func:`load_telegram_channels` — convenience: identifiers of active
  telegram_channel rows; what the existing crawler loop iterates over.
* :func:`write_source_metric` — UPSERT-merge a metric delta for one
  source, one calendar day. Mirrors the backend's
  ``POST /admin/sources/{id}/metrics``.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, date
from typing import Iterator, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ParserSourceRow:
    """A row from ``parser_sources``."""

    id: str
    type: str  # telegram_channel | website | olx | other
    identifier: str
    name: str
    is_active: bool
    priority: str  # high | medium | low
    parse_interval_minutes: int


def _connection_kwargs() -> dict:
    """Build psycopg2.connect() kwargs from the same env the backend uses."""
    url = os.getenv("DATABASE_URL")
    if url and url.startswith(("postgres://", "postgresql://")):
        # Already a libpq URL — psycopg2 accepts it directly via ``dsn=``.
        # Strip optional ``+driver`` part (e.g. postgresql+asyncpg://...)
        if "+" in url.split("://", 1)[0]:
            scheme, rest = url.split("://", 1)
            url = scheme.split("+", 1)[0] + "://" + rest
        return {"dsn": url}
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "dbname": os.getenv("POSTGRES_DB", "real_estate"),
    }


@contextmanager
def _conn() -> Iterator:
    """Open a short-lived psycopg2 connection. Reraises on driver-missing."""
    try:
        import psycopg2  # type: ignore
    except ImportError as e:  # noqa: BLE001 — surfaced via log
        raise RuntimeError(
            "psycopg2-binary is required for DB-backed sources. "
            "Install via `pip install psycopg2-binary`."
        ) from e

    conn = psycopg2.connect(**_connection_kwargs())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── reads ─────────────────────────────────────────────────────────────


def load_active_sources() -> List[ParserSourceRow]:
    """Return every active source. Empty list on connection failure
    (caller decides whether to fail-fast or fall back).
    """
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, type, identifier, name, is_active,
                           priority, parse_interval_minutes
                    FROM parser_sources
                    WHERE is_active = TRUE
                    ORDER BY priority DESC, identifier ASC
                    """
                )
                rows = cur.fetchall()
        return [
            ParserSourceRow(
                id=str(r[0]),
                type=r[1],
                identifier=r[2],
                name=r[3],
                is_active=r[4],
                priority=r[5],
                parse_interval_minutes=r[6],
            )
            for r in rows
        ]
    except Exception as exc:  # noqa: BLE001
        logger.error("load_active_sources failed: %s", exc)
        return []


def load_telegram_channels() -> List[str]:
    """Return identifiers of every active ``telegram_channel`` source.

    Identifier is the bare username (no leading ``@``), matching the
    backend's normalisation. The existing crawler iterates over a list
    of usernames; this returns that list directly.
    """
    return [
        row.identifier for row in load_active_sources() if row.type == "telegram_channel"
    ]


def find_source_id(identifier: str) -> Optional[str]:
    """Look up the row id by identifier. Used by metric writeback to
    convert a channel username back into the source UUID without a
    second round-trip per write.
    """
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM parser_sources WHERE identifier = %s",
                    (identifier,),
                )
                row = cur.fetchone()
                return str(row[0]) if row else None
    except Exception as exc:  # noqa: BLE001
        logger.error("find_source_id(%s) failed: %s", identifier, exc)
        return None


# ── writes ────────────────────────────────────────────────────────────


def write_source_metric(
    source_id: str,
    *,
    parsed: int = 0,
    saved: int = 0,
    failed: int = 0,
    duplicates: int = 0,
    ai_failed: int = 0,
    notified: int = 0,
    day: Optional[date] = None,
) -> bool:
    """Add a metric delta to today's row for ``source_id``.

    UPSERT-merge: counters are *added* on conflict, so calling this
    multiple times per day is safe and reflects cumulative work the
    crawler did since its last writeback.

    Returns True on success.
    """
    if day is None:
        day = datetime.utcnow().date()

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO source_metric (
                        source_id, day,
                        listings_found, listings_extracted,
                        listings_failed, dupes_filtered,
                        ai_failed, notified
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_id, day) DO UPDATE
                      SET listings_found     = source_metric.listings_found     + EXCLUDED.listings_found,
                          listings_extracted = source_metric.listings_extracted + EXCLUDED.listings_extracted,
                          listings_failed    = source_metric.listings_failed    + EXCLUDED.listings_failed,
                          dupes_filtered     = source_metric.dupes_filtered     + EXCLUDED.dupes_filtered,
                          ai_failed          = source_metric.ai_failed          + EXCLUDED.ai_failed,
                          notified           = source_metric.notified           + EXCLUDED.notified,
                          updated_at         = now()
                    """,
                    (source_id, day, parsed, saved, failed, duplicates, ai_failed, notified),
                )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("write_source_metric(%s) failed: %s", source_id, exc)
        return False


# ── CLI smoke test ────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sources = load_active_sources()
    print(f"Loaded {len(sources)} active sources from DB:")
    for s in sources:
        print(f"  {s.type:18s} {s.identifier:35s} priority={s.priority} active={s.is_active}")
    tg = load_telegram_channels()
    print(f"\n{len(tg)} active telegram channels: {', '.join(tg)}")
