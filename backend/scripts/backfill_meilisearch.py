#!/usr/bin/env python3
"""PR9 — Backfill Meilisearch from Postgres.

Streams every ACTIVE non-deleted listing into the `listings` Meili index
in batches. Idempotent (Meili upserts by primary key) — safe to re-run
any number of times. Never raises into the caller; partial failures are
logged at WARNING and counted in the result.

Usage:
    python backend/scripts/backfill_meilisearch.py [BATCH_SIZE]

    BATCH_SIZE   defaults to 1000; pass smaller for slower targets

Exit code:
    0 on completion (even with partial failures)
    1 only on argument parsing failure
"""

import asyncio
import logging
import sys

logger = logging.getLogger("backfill_meilisearch")


async def _run(batch_size: int) -> int:
    # Imports are inside the coroutine so a missing dependency surfaces
    # as a clean log line rather than an import-time crash.
    from app.db.database import async_session_maker
    from app.services.search_index import (
        backfill_all_listings,
        backfill_crawled_listings,
        get_backfill_counters,
        init_meilisearch_index,
    )

    # Step 1 — make sure the index + attributes exist. Safe-fallback:
    # `False` here means Meili is unreachable; backfill will return zeros.
    if not init_meilisearch_index():
        logger.warning(
            "init_meilisearch_index() returned False — Meili likely "
            "unreachable. Backfill will report zero indexed."
        )

    # Step 2 — stream native + crawled (Telegram/OLX) listings into the index.
    async with async_session_maker() as session:
        native = await backfill_all_listings(session, batch_size=batch_size)
        crawled = await backfill_crawled_listings(session, batch_size=batch_size)

    indexed = native["indexed_count"] + crawled["indexed_count"]
    failed = native["failed_count"] + crawled["failed_count"]
    counters = get_backfill_counters()
    logger.info(
        "backfill done: indexed=%d (native=%d crawled=%d) failed=%d counters=%s",
        indexed,
        native["indexed_count"],
        crawled["indexed_count"],
        failed,
        counters,
    )
    print(
        f"Indexed: {indexed}  (native={native['indexed_count']} "
        f"crawled={crawled['indexed_count']})  Failed: {failed}"
    )
    print(f"Counters: {counters}")
    return 0


def _parse_batch_size(argv: list[str]) -> int:
    if len(argv) <= 1:
        return 1000
    try:
        n = int(argv[1])
    except ValueError:
        sys.stderr.write(f"invalid BATCH_SIZE: {argv[1]!r}\n")
        sys.exit(1)
    if n <= 0:
        sys.stderr.write("BATCH_SIZE must be positive\n")
        sys.exit(1)
    return n


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    batch_size = _parse_batch_size(sys.argv)
    return asyncio.run(_run(batch_size))


if __name__ == "__main__":
    sys.exit(main())
