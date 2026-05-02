"""PR10 — Search router + Meili mapper unit tests.

Covers:
    - Router dispatches to Postgres when flag is "postgres"
    - Router dispatches to Meili when flag is "meili", calls hydrate
    - Router falls back to Postgres on ANY Meili exception
    - Filter→Meili expression builder respects silent-drop rule
    - sort mapper falls back to created_at:desc for unknown sort keys

Pure mock-based; no live Meili / DB.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import settings
from app.schemas.listing import ListingFilters
from app.services import search_index, search_router

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


# ─────────────────────────────────────────────────────────────────────
# Router dispatch
# ─────────────────────────────────────────────────────────────────────


class TestRouterDispatch:
    async def test_postgres_flag_calls_pg_runner_directly(self):
        f = ListingFilters()
        pg_runner = AsyncMock(return_value={"ok": True})
        with patch.object(settings, "search_backend", "postgres"):
            result = await search_router.get_listings(
                filters=f,
                db_session=MagicMock(),
                page=1,
                per_page=10,
                current_user=None,
                postgres_runner=pg_runner,
            )
        assert result == {"ok": True}
        assert pg_runner.await_count == 1
        # Postgres path must pass meili_ids=None explicitly.
        kw = pg_runner.await_args.kwargs
        assert kw["meili_ids"] is None
        assert kw["meili_total"] is None

    async def test_meili_flag_calls_meili_then_pg_hydrate(self):
        f = ListingFilters()
        pg_runner = AsyncMock(return_value={"ok": True})
        with (
            patch.object(settings, "search_backend", "meili"),
            patch.object(
                search_index,
                "search_listings_in_meili",
                return_value=(["id-1", "id-2"], 2),
            ),
        ):
            result = await search_router.get_listings(
                filters=f,
                db_session=MagicMock(),
                page=1,
                per_page=10,
                current_user=None,
                postgres_runner=pg_runner,
            )
        assert result == {"ok": True}
        kw = pg_runner.await_args.kwargs
        # Meili path must pass the IDs + total through to the runner.
        assert kw["meili_ids"] == ["id-1", "id-2"]
        assert kw["meili_total"] == 2

    async def test_meili_failure_falls_back_to_postgres(self):
        f = ListingFilters()
        pg_runner = AsyncMock(return_value={"source": "pg"})
        with (
            patch.object(settings, "search_backend", "meili"),
            patch.object(
                search_index,
                "search_listings_in_meili",
                side_effect=RuntimeError("meili down"),
            ),
        ):
            result = await search_router.get_listings(
                filters=f,
                db_session=MagicMock(),
                page=1,
                per_page=10,
                current_user=None,
                postgres_runner=pg_runner,
            )
        assert result == {"source": "pg"}
        # Fallback must pass meili_ids=None.
        assert pg_runner.await_args.kwargs["meili_ids"] is None

    async def test_facets_postgres_flag_bypasses_meili(self):
        f = ListingFilters()
        pg_runner = AsyncMock(return_value={"deal_type": []})
        with patch.object(settings, "search_backend", "postgres"):
            result = await search_router.get_facets(
                filters=f,
                db_session=MagicMock(),
                postgres_runner=pg_runner,
            )
        assert result == {"deal_type": []}
        assert pg_runner.await_count == 1

    async def test_facets_meili_error_falls_back_to_postgres(self):
        f = ListingFilters()
        pg_runner = AsyncMock(return_value={"source": "pg"})
        with (
            patch.object(settings, "search_backend", "meili"),
            patch.object(
                search_index,
                "search_facets_in_meili",
                side_effect=RuntimeError("boom"),
            ),
        ):
            result = await search_router.get_facets(
                filters=f,
                db_session=MagicMock(),
                postgres_runner=pg_runner,
            )
        assert result == {"source": "pg"}

    async def test_facets_meili_returns_non_dict_falls_back(self):
        f = ListingFilters()
        pg_runner = AsyncMock(return_value={"source": "pg"})
        with (
            patch.object(settings, "search_backend", "meili"),
            patch.object(
                search_index,
                "search_facets_in_meili",
                return_value="not a dict",
            ),
        ):
            result = await search_router.get_facets(
                filters=f,
                db_session=MagicMock(),
                postgres_runner=pg_runner,
            )
        assert result == {"source": "pg"}


# ─────────────────────────────────────────────────────────────────────
# Filter → Meili expression mapper
# ─────────────────────────────────────────────────────────────────────


class TestFilterExpression:
    def test_always_includes_base_predicates(self):
        # FIX 5 — `deleted_at IS NULL` was removed (field not indexed).
        # Correctness is enforced at write-time: soft-deletes call
        # `delete_listing()`, so deleted rows never live in the index.
        expr = search_index._filters_to_meili_expression(ListingFilters())
        assert 'status = "ACTIVE"' in expr
        assert 'moderation_status = "APPROVED"' in expr
        assert "deleted_at" not in expr

    def test_type_and_property_type_go_uppercase(self):
        f = ListingFilters(type="rent", property_type="apartment")
        expr = search_index._filters_to_meili_expression(f)
        assert 'type = "RENT"' in expr
        assert 'property_type = "APARTMENT"' in expr

    def test_price_range_emits_numeric_predicates(self):
        f = ListingFilters(price_min=50000, price_max=100000)
        expr = search_index._filters_to_meili_expression(f)
        assert "price >= 50000" in expr
        assert "price <= 100000" in expr

    def test_rooms_list_becomes_OR(self):
        f = ListingFilters(rooms=[1, 2, 3])
        expr = search_index._filters_to_meili_expression(f)
        assert "rooms = 1" in expr
        assert "rooms = 2" in expr
        assert "rooms = 3" in expr

    def test_region_list_becomes_OR(self):
        f = ListingFilters(region=["toshkent_shahri", "toshkent_viloyati"])
        expr = search_index._filters_to_meili_expression(f)
        assert 'region = "toshkent_shahri"' in expr
        assert 'region = "toshkent_viloyati"' in expr

    def test_amenities_AND_match_each_as_separate_predicate(self):
        f = ListingFilters(amenities=["tv", "ac"])
        expr = search_index._filters_to_meili_expression(f)
        # Meili array semantics: "col = val" matches array-contains.
        # AND-joined predicates => doc must contain BOTH values.
        assert 'amenities = "tv"' in expr
        assert 'amenities = "ac"' in expr
        # Ensure they're AND-joined (i.e. appear as separate top-level
        # clauses, not within an OR group).
        assert 'amenities = "tv" AND amenities = "ac"' in expr or (
            'amenities = "ac" AND amenities = "tv"' in expr
        )

    def test_rent_payment_OR_match(self):
        f = ListingFilters(type="rent", rent_payment=["cash", "payme"])
        expr = search_index._filters_to_meili_expression(f)
        assert 'rent_payment = "cash" OR rent_payment = "payme"' in expr

    def test_applicability_drops_rent_filter_on_sell(self):
        """rent_period is not applicable when type=sell → must NOT
        appear in the expression."""
        f = ListingFilters(type="sell", rent_period="daily")
        expr = search_index._filters_to_meili_expression(f)
        assert "rent_period" not in expr

    def test_applicability_drops_sale_filter_on_rent(self):
        f = ListingFilters(type="rent", mortgage_ok=True)
        expr = search_index._filters_to_meili_expression(f)
        assert "mortgage_ok" not in expr

    def test_mortgage_ok_only_on_true(self):
        """Booleans are True-only (mirrors Postgres path: we never filter
        for `mortgage_ok = false`)."""
        f = ListingFilters(type="sell", mortgage_ok=True)
        expr = search_index._filters_to_meili_expression(f)
        assert "mortgage_ok = true" in expr

        f2 = ListingFilters(type="sell", mortgage_ok=False)
        expr2 = search_index._filters_to_meili_expression(f2)
        assert "mortgage_ok" not in expr2

    def test_string_escaping(self):
        f = ListingFilters(region=['weird"thing'])
        expr = search_index._filters_to_meili_expression(f)
        # The embedded quote is escaped.
        assert r'region = "weird\"thing"' in expr

    def test_mixed_complex_filter(self):
        f = ListingFilters(
            type="sell",
            property_type="apartment",
            price_min=70000,
            mortgage_ok=True,
            amenities=["tv"],
        )
        expr = search_index._filters_to_meili_expression(f)
        for clause in (
            'type = "SELL"',
            'property_type = "APARTMENT"',
            "price >= 70000",
            "mortgage_ok = true",
            'amenities = "tv"',
        ):
            assert clause in expr


# ─────────────────────────────────────────────────────────────────────
# Sort mapper
# ─────────────────────────────────────────────────────────────────────


class TestSortMapper:
    # FIX 3 — sort now always leads with `boost_rank:desc` so promoted
    # listings surface first, mirroring the Postgres `ORDER BY
    # is_boosted DESC, …` primary tier.

    def test_known_sort_key_maps_through(self):
        f = ListingFilters(sort_by="price", sort_order="asc")
        assert search_index._filters_to_meili_sort(f) == [
            "boost_rank:desc",
            "price:asc",
        ]

    def test_created_at_is_always_valid(self):
        f = ListingFilters(sort_by="created_at", sort_order="desc")
        assert search_index._filters_to_meili_sort(f) == [
            "boost_rank:desc",
            "created_at:desc",
        ]

    def test_non_sortable_key_falls_back_to_default(self):
        # `views_count` is a valid Postgres sort key but NOT in Meili's
        # SORTABLE_ATTRIBUTES list — mapper must degrade to created_at:desc.
        f = ListingFilters(sort_by="views_count", sort_order="asc")
        assert search_index._filters_to_meili_sort(f) == [
            "boost_rank:desc",
            "created_at:desc",
        ]
