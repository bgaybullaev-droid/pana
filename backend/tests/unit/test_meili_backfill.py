"""PR9 — Meilisearch backfill unit tests.

Pure mock-based: no live Meili process, no live DB session. Verifies:

    - Batch splitting via WHERE id > last_id LIMIT batch_size
    - A single failing batch does NOT halt the whole run
    - Per-batch retry happens exactly once on failure
    - Idempotency: running twice does not double-count or fail
    - Mapping correctness: the same docs the per-row indexer produces
    - Safe-fallback: returns zeros when Meili is unreachable; never raises
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.db.models import (
    Currency,
    Listing,
    ListingStatus,
    ListingType,
    ModerationStatus,
    PropertyType,
    SourceType,
)
from app.services import search_index
from app.services.search_index import (
    _index_batch,
    _map_listing_to_document,
    backfill_all_listings,
    get_backfill_counters,
    reset_backfill_counters,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _mk(i: int) -> Listing:
    """Build a minimal in-memory Listing whose `id` orders deterministically."""
    return Listing(
        id=UUID(int=i),
        type=ListingType.SELL,
        property_type=PropertyType.APARTMENT,
        status=ListingStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
        source_type=SourceType.MANUAL,
        price=50000 + i,
        currency=Currency.USD,
        rooms=2,
        area=55.0,
        floor=3,
        total_floors=9,
        building_type="new",
        condition="euro",
        is_furnished=True,
        region="toshkent_shahri",
        district="mirzo_ulugbek",
        title=f"L{i}",
        created_at=datetime(2026, 4, 14, 12, 0, 0),
    )


def _make_session_returning(pages):
    """Mock async DB session whose `execute()` returns successive pages.

    pages: list[list[Listing]] — each call to execute() returns the next
    page; an empty list ends the loop.
    """
    session = MagicMock()
    call = {"i": 0}

    async def _execute(_query):
        i = call["i"]
        call["i"] += 1
        result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = pages[i] if i < len(pages) else []
        result.scalars.return_value = scalars
        return result

    session.execute = _execute
    return session


# ─────────────────────────────────────────────────────────────────────
# Safe-fallback (Meili unreachable)
# ─────────────────────────────────────────────────────────────────────


class TestSafeFallback:
    async def test_returns_zeros_when_meili_unreachable(self):
        """ensure_index_exists() → None means no client; backfill returns
        zero counts and never raises."""
        reset_backfill_counters()
        session = _make_session_returning([[_mk(1)]])
        with patch.object(search_index, "ensure_index_exists", return_value=None):
            result = await backfill_all_listings(session, batch_size=10)
        assert result == {"indexed_count": 0, "failed_count": 0}

    async def test_never_raises_on_db_failure(self):
        """A hard DB exception during pagination is logged and the loop
        exits cleanly with whatever was indexed so far."""
        reset_backfill_counters()
        session = MagicMock()
        # Async exec that raises immediately
        session.execute = AsyncMock(side_effect=RuntimeError("db down"))
        with patch.object(
            search_index, "ensure_index_exists", return_value=MagicMock()
        ):
            result = await backfill_all_listings(session, batch_size=10)
        assert result == {"indexed_count": 0, "failed_count": 0}


# ─────────────────────────────────────────────────────────────────────
# Batch splitting
# ─────────────────────────────────────────────────────────────────────


class TestBatchSplitting:
    async def test_batches_use_configured_size(self):
        """3 batches of 5 + a short final batch. Each call to add_documents
        is one batch."""
        reset_backfill_counters()
        page1 = [_mk(i) for i in range(1, 6)]  # batch_size=5 → full
        page2 = [_mk(i) for i in range(6, 11)]  # full
        page3 = [_mk(11)]  # short → loop ends
        session = _make_session_returning([page1, page2, page3])

        index = MagicMock()
        with patch.object(search_index, "ensure_index_exists", return_value=index):
            result = await backfill_all_listings(session, batch_size=5)

        # 3 add_documents calls; sizes 5, 5, 1
        assert index.add_documents.call_count == 3
        sizes = [len(call.args[0]) for call in index.add_documents.call_args_list]
        assert sizes == [5, 5, 1]
        assert result == {"indexed_count": 11, "failed_count": 0}

    async def test_loop_terminates_on_short_final_batch(self):
        """A batch smaller than batch_size triggers immediate exit (no
        wasted final empty query)."""
        reset_backfill_counters()
        session = _make_session_returning([[_mk(1), _mk(2)]])  # only 2 rows
        index = MagicMock()
        with patch.object(search_index, "ensure_index_exists", return_value=index):
            result = await backfill_all_listings(session, batch_size=1000)
        assert result["indexed_count"] == 2
        # Should have stopped after 1 query (short batch).
        assert index.add_documents.call_count == 1


# ─────────────────────────────────────────────────────────────────────
# Failure / retry semantics
# ─────────────────────────────────────────────────────────────────────


class TestFailureHandling:
    async def test_batch_failure_does_not_halt_run(self):
        """Batch 2 of 3 fails (both attempts). Batches 1 and 3 still
        succeed; final counts reflect partial failure."""
        reset_backfill_counters()
        page1 = [_mk(i) for i in range(1, 4)]  # 3 rows, batch_size=3
        page2 = [_mk(i) for i in range(4, 7)]  # 3 rows
        page3 = [_mk(7), _mk(8)]  # 2 rows (short → stop)
        session = _make_session_returning([page1, page2, page3])

        index = MagicMock()
        # First attempt of any batch succeeds, EXCEPT batch starting with id=4
        # which fails twice (initial + retry).
        attempts = []

        def _add(docs, primary_key):
            attempts.append(docs[0]["id"])
            if docs[0]["id"] == str(UUID(int=4)):
                raise RuntimeError("meili 502")
            return MagicMock()

        index.add_documents = MagicMock(side_effect=_add)

        with patch.object(search_index, "ensure_index_exists", return_value=index):
            result = await backfill_all_listings(session, batch_size=3)

        assert result["indexed_count"] == 5  # batch1 (3) + batch3 (2)
        assert result["failed_count"] == 3  # batch2 (3) failed both attempts

        # Total calls: batch1 (1) + batch2 (2 attempts) + batch3 (1) = 4
        assert index.add_documents.call_count == 4

    async def test_retry_happens_exactly_once_per_failed_batch(self):
        reset_backfill_counters()
        # One batch of 2; first call raises, second succeeds.
        session = _make_session_returning([[_mk(1), _mk(2)]])
        index = MagicMock()
        call_state = {"n": 0}

        def _add(docs, primary_key):
            call_state["n"] += 1
            if call_state["n"] == 1:
                raise RuntimeError("transient")
            return MagicMock()

        index.add_documents = MagicMock(side_effect=_add)

        with patch.object(search_index, "ensure_index_exists", return_value=index):
            result = await backfill_all_listings(session, batch_size=1000)

        # Initial + 1 retry = 2 calls total; success on retry → indexed.
        assert index.add_documents.call_count == 2
        assert result == {"indexed_count": 2, "failed_count": 0}


# ─────────────────────────────────────────────────────────────────────
# Idempotency
# ─────────────────────────────────────────────────────────────────────


class TestIdempotency:
    async def test_running_twice_produces_same_outcome(self):
        """Meili upserts by primary key, so re-running the backfill against
        the same dataset yields the same result counts."""
        reset_backfill_counters()
        rows = [_mk(i) for i in range(1, 4)]
        index = MagicMock()

        # Each invocation gets a fresh mock session (real life: each run
        # opens a new DB session via async_session_maker()).
        with patch.object(search_index, "ensure_index_exists", return_value=index):
            session_a = _make_session_returning([rows])
            r1 = await backfill_all_listings(session_a, batch_size=1000)
            session_b = _make_session_returning([rows])
            r2 = await backfill_all_listings(session_b, batch_size=1000)

        assert r1 == r2 == {"indexed_count": 3, "failed_count": 0}
        # Counters accumulate across runs (that's their contract).
        counters = get_backfill_counters()
        assert counters["meili_backfill_success_total"] == 6
        assert counters["meili_backfill_failure_total"] == 0


# ─────────────────────────────────────────────────────────────────────
# Mapping correctness — same documents the per-row indexer produces
# ─────────────────────────────────────────────────────────────────────


class TestMappingCorrectness:
    async def test_documents_match_map_listing_to_document(self):
        """The batch path MUST produce documents identical to what the
        single-row `index_listing` path produces. No drift allowed."""
        reset_backfill_counters()
        rows = [_mk(i) for i in range(1, 4)]
        expected_docs = [_map_listing_to_document(r) for r in rows]

        sent_docs: list[dict] = []
        index = MagicMock()
        index.add_documents = MagicMock(
            side_effect=lambda docs, primary_key: sent_docs.extend(docs)
        )

        session = _make_session_returning([rows])
        with patch.object(search_index, "ensure_index_exists", return_value=index):
            await backfill_all_listings(session, batch_size=1000)

        assert sent_docs == expected_docs

    async def test_index_batch_helper_returns_true_on_empty_list(self):
        """Empty batch is a trivial success — never raises, never calls
        the index."""
        index = MagicMock()
        assert _index_batch(index, []) is True
        assert index.add_documents.call_count == 0

    async def test_index_batch_helper_returns_false_on_exception(self):
        index = MagicMock()
        index.add_documents = MagicMock(side_effect=RuntimeError("fail"))
        assert _index_batch(index, [_mk(1)]) is False


# ─────────────────────────────────────────────────────────────────────
# Counters
# ─────────────────────────────────────────────────────────────────────


class TestCounters:
    async def test_success_counter_increments_per_indexed_row(self):
        reset_backfill_counters()
        rows = [_mk(i) for i in range(1, 6)]
        index = MagicMock()
        session = _make_session_returning([rows])
        with patch.object(search_index, "ensure_index_exists", return_value=index):
            await backfill_all_listings(session, batch_size=1000)
        c = get_backfill_counters()
        assert c["meili_backfill_success_total"] == 5
        assert c["meili_backfill_failure_total"] == 0

    async def test_failure_counter_increments_on_failed_batch(self):
        reset_backfill_counters()
        rows = [_mk(i) for i in range(1, 4)]
        index = MagicMock()
        index.add_documents = MagicMock(side_effect=RuntimeError("perma-fail"))
        session = _make_session_returning([rows])
        with patch.object(search_index, "ensure_index_exists", return_value=index):
            await backfill_all_listings(session, batch_size=1000)
        c = get_backfill_counters()
        assert c["meili_backfill_failure_total"] == 3
        assert c["meili_backfill_success_total"] == 0

    async def test_reset_zeroes_counters(self):
        # FIX 4 added per-write index/delete counters; reset must zero
        # ALL tracked counters, not just the backfill pair.
        _BACKFILL = search_index._BACKFILL_COUNTERS
        for k in _BACKFILL:
            _BACKFILL[k] = 42
        reset_backfill_counters()
        c = get_backfill_counters()
        assert all(v == 0 for v in c.values()), c
        # And we still have the full set of counter keys afterwards.
        for k in (
            "meili_backfill_success_total",
            "meili_backfill_failure_total",
            "meili_index_success_total",
            "meili_index_failure_total",
            "meili_delete_success_total",
            "meili_delete_failure_total",
        ):
            assert k in c
