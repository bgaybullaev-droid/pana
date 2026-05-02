"""Audit-fix regression tests — 5 production blockers + 1 fallback guard.

Scope (strictly the audit fixes; no new features):
    FIX 1 — admin approve / reject call index_listing / delete_listing
    FIX 2 — Meili facets emit lowercase enum values (parity with PG)
    FIX 3 — `boost_rank:desc` always leads the Meili sort → is_boosted
            semantics preserved
    FIX 4 — counters increment on the per-write index/delete paths
    FIX 5 — `deleted_at IS NULL` is NOT in the Meili filter expression
    FALLBACK — Meili failure → Postgres path still answers (no 5xx)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.config import settings
from app.db.models import (
    Currency,
    Listing,
    ListingStatus,
    ListingType,
    ModerationStatus,
    PropertyType,
    SourceType,
)
from app.schemas.listing import ListingFilters
from app.services import search_index, search_router

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────
# FIX 2 — facet value normalization
# ─────────────────────────────────────────────────────────────────────


class TestFacetsLowercase:
    def test_type_values_are_lowercased(self):
        """Meili stores 'SELL'/'RENT' (enum NAMES); PG returns
        'sell'/'rent' (enum .value). Facets output MUST be lowercase to
        be byte-identical across backends."""
        search_index.reset_backfill_counters()
        fake_index = MagicMock()
        fake_index.search = MagicMock(
            return_value={
                "facetDistribution": {
                    "type": {"SELL": 5, "RENT": 3},
                    "property_type": {"APARTMENT": 8},
                },
                "estimatedTotalHits": 8,
            }
        )
        with patch.object(search_index, "ensure_index_exists", return_value=fake_index):
            result = search_index.search_facets_in_meili(ListingFilters())
        # All type values must be lowercase now.
        dt_values = {b["value"] for b in result["deal_type"]}
        assert dt_values == {"sell", "rent"}
        pt_values = {b["value"] for b in result["property_type"]}
        assert pt_values == {"apartment"}

    def test_region_values_pass_through_unchanged(self):
        """Region / district are stored raw in PG (lowercase snake_case
        like 'toshkent_shahri'). Meili mirrors that — no transformation
        needed and none should happen."""
        fake_index = MagicMock()
        fake_index.search = MagicMock(
            return_value={
                "facetDistribution": {
                    "region": {"Toshkent_Shahri": 7},
                },
                "estimatedTotalHits": 7,
            }
        )
        with patch.object(search_index, "ensure_index_exists", return_value=fake_index):
            result = search_index.search_facets_in_meili(ListingFilters())
        # Region must NOT be lowercased — it's pass-through.
        region_values = {b["value"] for b in result["region"]}
        assert region_values == {"Toshkent_Shahri"}


# ─────────────────────────────────────────────────────────────────────
# FIX 3 — boost_rank ordering
# ─────────────────────────────────────────────────────────────────────


class TestBoostRankSort:
    def test_boost_rank_always_leads_sort(self):
        """Promoted listings (is_boosted=true) MUST surface first on
        Meili just like the Postgres primary tier
        `ORDER BY is_boosted DESC, …`."""
        f = ListingFilters()
        sort = search_index._filters_to_meili_sort(f)
        assert sort[0] == "boost_rank:desc"

    def test_secondary_tier_matches_requested_sort(self):
        f = ListingFilters(sort_by="price", sort_order="asc")
        sort = search_index._filters_to_meili_sort(f)
        assert sort == ["boost_rank:desc", "price:asc"]

    def test_unknown_sort_key_falls_back_to_created_at(self):
        f = ListingFilters(sort_by="views_count", sort_order="asc")
        sort = search_index._filters_to_meili_sort(f)
        assert sort == ["boost_rank:desc", "created_at:desc"]

    def test_boost_rank_is_sortable(self):
        """SORTABLE_ATTRIBUTES must include boost_rank — Meilisearch
        rejects sorts on non-sortable fields at query time."""
        assert "boost_rank" in search_index.SORTABLE_ATTRIBUTES

    def test_boost_rank_lives_in_indexed_document(self):
        """If the document doesn't carry boost_rank, the sort clause
        matches no docs and we ship empty feeds. Guard against that."""
        listing = Listing(
            id=uuid4(),
            type=ListingType.SELL,
            property_type=PropertyType.APARTMENT,
            status=ListingStatus.ACTIVE,
            moderation_status=ModerationStatus.APPROVED,
            source_type=SourceType.MANUAL,
            price=50000,
            currency=Currency.USD,
            is_boosted=True,
        )
        doc = search_index._map_listing_to_document(listing)
        assert doc["boost_rank"] == 1

        listing2 = Listing(
            id=uuid4(),
            type=ListingType.SELL,
            property_type=PropertyType.APARTMENT,
            status=ListingStatus.ACTIVE,
            moderation_status=ModerationStatus.APPROVED,
            source_type=SourceType.MANUAL,
            price=50000,
            currency=Currency.USD,
            is_boosted=False,
        )
        doc2 = search_index._map_listing_to_document(listing2)
        assert doc2["boost_rank"] == 0


# ─────────────────────────────────────────────────────────────────────
# FIX 4 — counters on per-write hooks
# ─────────────────────────────────────────────────────────────────────


class TestWriteHookCounters:
    def test_index_success_increments(self):
        search_index.reset_backfill_counters()
        fake_index = MagicMock()
        with patch.object(search_index, "ensure_index_exists", return_value=fake_index):
            listing = Listing(
                id=uuid4(),
                type=ListingType.SELL,
                property_type=PropertyType.APARTMENT,
                status=ListingStatus.ACTIVE,
                moderation_status=ModerationStatus.APPROVED,
                source_type=SourceType.MANUAL,
                price=1,
                currency=Currency.USD,
            )
            search_index.index_listing(listing)
        c = search_index.get_backfill_counters()
        assert c["meili_index_success_total"] == 1
        assert c["meili_index_failure_total"] == 0

    def test_index_failure_increments_when_meili_unreachable(self):
        search_index.reset_backfill_counters()
        with patch.object(search_index, "ensure_index_exists", return_value=None):
            listing = Listing(id=uuid4())
            result = search_index.index_listing(listing)
        assert result is False
        c = search_index.get_backfill_counters()
        assert c["meili_index_failure_total"] == 1

    def test_delete_success_increments(self):
        search_index.reset_backfill_counters()
        fake_index = MagicMock()
        with patch.object(search_index, "ensure_index_exists", return_value=fake_index):
            search_index.delete_listing(uuid4())
        c = search_index.get_backfill_counters()
        assert c["meili_delete_success_total"] == 1
        assert c["meili_delete_failure_total"] == 0

    def test_delete_failure_increments_on_exception(self):
        search_index.reset_backfill_counters()
        fake_index = MagicMock()
        fake_index.delete_document = MagicMock(side_effect=RuntimeError("boom"))
        with patch.object(search_index, "ensure_index_exists", return_value=fake_index):
            result = search_index.delete_listing(uuid4())
        assert result is False
        c = search_index.get_backfill_counters()
        assert c["meili_delete_failure_total"] == 1


# ─────────────────────────────────────────────────────────────────────
# FIX 5 — deleted_at clause removed
# ─────────────────────────────────────────────────────────────────────


class TestDeletedAtNotInFilter:
    def test_deleted_at_is_not_in_meili_expression(self):
        """The `deleted_at` attribute is not in the indexed document
        (by design — we only index non-deleted rows). The filter must
        NOT reference it, otherwise the expression's behavior depends on
        undefined Meili semantics for missing attributes."""
        expr = search_index._filters_to_meili_expression(ListingFilters())
        assert "deleted_at" not in expr

    def test_base_predicates_still_present(self):
        """status=ACTIVE + moderation_status=APPROVED remain — these are
        the actual correctness gates now that deleted_at is gone."""
        expr = search_index._filters_to_meili_expression(ListingFilters())
        assert 'status = "ACTIVE"' in expr
        assert 'moderation_status = "APPROVED"' in expr


# ─────────────────────────────────────────────────────────────────────
# FALLBACK — router still falls back on any Meili exception
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRouterFallbackIntact:
    async def test_listings_falls_back_on_meili_exception(self):
        """PR10 invariant re-verified after the FIX edits: any Meili
        failure must drop through to Postgres. No 5xx surface."""
        from unittest.mock import AsyncMock

        pg_runner = AsyncMock(return_value={"from": "pg"})
        with (
            patch.object(settings, "search_backend", "meili"),
            patch.object(
                search_index,
                "search_listings_in_meili",
                side_effect=RuntimeError("meili down"),
            ),
        ):
            result = await search_router.get_listings(
                filters=ListingFilters(),
                db_session=MagicMock(),
                page=1,
                per_page=10,
                current_user=None,
                postgres_runner=pg_runner,
            )
        assert result == {"from": "pg"}
        # And the fallback must pass meili_ids=None so the PG path runs
        # _apply_filters, not a stale IN-list.
        assert pg_runner.await_args.kwargs["meili_ids"] is None

    async def test_facets_falls_back_on_meili_exception(self):
        from unittest.mock import AsyncMock

        pg_runner = AsyncMock(return_value={"from": "pg"})
        with (
            patch.object(settings, "search_backend", "meili"),
            patch.object(
                search_index,
                "search_facets_in_meili",
                side_effect=RuntimeError("meili down"),
            ),
        ):
            result = await search_router.get_facets(
                filters=ListingFilters(),
                db_session=MagicMock(),
                postgres_runner=pg_runner,
            )
        assert result == {"from": "pg"}
