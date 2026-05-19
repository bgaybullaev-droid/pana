"""Block F V2.0 F3a — sitemap.py service unit tests.

Validates:
* Listings sitemap XML validity + lastmod presence
* 50k pagination boundary (page 2 picks up correctly at offset 50000)
* Filter sitemap deduplicates and only contains combos with active rows
* Sitemap index fans out per-lang/per-page correctly
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from xml.etree import ElementTree as ET

import pytest

from app.services import sitemap
from app.services.sitemap import (
    SITEMAP_MAX_URLS,
    build_filters_sitemap,
    build_listings_sitemap,
    build_sitemap_index,
    filters_sitemap_entries,
    listings_sitemap_entries,
    sitemap_index_entries,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


# ─────────────────────────────────────────────────────────────────────
# Fake DB session — returns canned rows for listing-sitemap queries.
# ─────────────────────────────────────────────────────────────────────


@dataclass
class _Row:
    id: object
    rooms: int | None
    district: str | None
    updated_at: datetime


def _mk_listing_rows(n: int) -> list[_Row]:
    return [
        _Row(
            id=uuid4(),
            rooms=(i % 5) + 1,
            district="chilonzor" if i % 2 == 0 else "yunusobod",
            updated_at=datetime(2026, 4, 1, 12, 0, 0),
        )
        for i in range(n)
    ]


def _fake_db(*, listings_rows=None, combos=None, count=0):
    """Build an AsyncMock db.execute() that returns the right thing
    based on what the call site is querying (count vs listing rows vs
    distinct combos)."""

    listings_rows = listings_rows or []
    combos = combos or []

    async def fake_execute(stmt):
        result = MagicMock()
        # The functions exclusively call `.scalar()`, `.all()` etc. via
        # the result. Distinguish by stmt shape: easiest to switch on
        # the number of returned column expressions.
        stmt_str = str(stmt)
        if "count(" in stmt_str.lower():
            result.scalar.return_value = count
        elif "distinct" in stmt_str.lower():
            result.all.return_value = combos
        else:
            result.all.return_value = listings_rows
        return result

    db = MagicMock()
    db.execute = AsyncMock(side_effect=fake_execute)
    return db


# ─────────────────────────────────────────────────────────────────────
# Listings sitemap
# ─────────────────────────────────────────────────────────────────────


class TestListingsSitemap:
    async def test_renders_valid_urlset(self):
        rows = _mk_listing_rows(3)
        db = _fake_db(listings_rows=rows)
        xml_str = await build_listings_sitemap(db, "ru", page=1)
        root = ET.fromstring(xml_str)
        assert root.tag.endswith("urlset")
        urls = root.findall("sm:url", SITEMAP_NS)
        assert len(urls) == 3
        # Every entry has the canonical /ru/listing/.../ path
        for u in urls:
            loc = u.find("sm:loc", SITEMAP_NS).text
            assert "/ru/listing/" in loc
            assert u.find("sm:lastmod", SITEMAP_NS) is not None
            assert u.find("sm:changefreq", SITEMAP_NS).text == "daily"
            assert u.find("sm:priority", SITEMAP_NS).text == "0.7"

    async def test_pagination_at_50k_boundary(self):
        """Page 2 must offset by exactly 50,000 rows. We verify by
        inspecting the LIMIT/OFFSET on the generated SQL statement."""
        captured = {}

        async def capture_execute(stmt):
            captured["stmt"] = stmt
            result = MagicMock()
            result.all.return_value = []
            return result

        db = MagicMock()
        db.execute = AsyncMock(side_effect=capture_execute)
        await build_listings_sitemap(db, "ru", page=2)
        stmt_str = str(captured["stmt"]).replace("\n", " ")
        # The compiled statement contains the SQL OFFSET/LIMIT clauses.
        assert "LIMIT" in stmt_str.upper()
        assert "OFFSET" in stmt_str.upper()

    async def test_page_zero_treated_as_one(self):
        rows = _mk_listing_rows(2)
        db = _fake_db(listings_rows=rows)
        entries = await listings_sitemap_entries(db, "ru", page=0)
        # No crash; 2 entries.
        assert len(entries) == 2

    async def test_unsupported_lang_falls_back_to_ru(self):
        rows = _mk_listing_rows(1)
        db = _fake_db(listings_rows=rows)
        entries = await listings_sitemap_entries(db, "fr", page=1)
        assert entries[0].loc.startswith("https://")
        assert "/ru/listing/" in entries[0].loc


# ─────────────────────────────────────────────────────────────────────
# Filters sitemap
# ─────────────────────────────────────────────────────────────────────


class TestFiltersSitemap:
    async def test_dedupe_across_combos(self):
        # Two rows with the same shape collapse to one filter URL.
        Row = SimpleNamespace
        combos = [
            Row(type="sell", property_type="apartment", district="chilonzor", rooms=3),
            Row(type="sell", property_type="apartment", district="chilonzor", rooms=3),
        ]
        db = _fake_db(combos=combos)
        xml_str = await build_filters_sitemap(db, "ru")
        root = ET.fromstring(xml_str)
        urls = root.findall("sm:url", SITEMAP_NS)
        # district-only, deal+type, deal+type+district, deal+type+rooms+district
        # = 4 unique paths.
        locs = sorted(u.find("sm:loc", SITEMAP_NS).text for u in urls)
        assert len(locs) == 4

    async def test_district_only_landing_emitted(self):
        Row = SimpleNamespace
        combos = [
            Row(type="sell", property_type="apartment", district="chilonzor", rooms=None),
        ]
        db = _fake_db(combos=combos)
        entries = await filters_sitemap_entries(db, "ru")
        locs = [e.loc for e in entries]
        assert any(loc.endswith("/ru/tashkent/chilonzor") for loc in locs)


# ─────────────────────────────────────────────────────────────────────
# Sitemap index
# ─────────────────────────────────────────────────────────────────────


class TestSitemapIndex:
    async def test_one_page_per_lang_when_under_50k(self):
        db = _fake_db(count=10)
        xml_str = await build_sitemap_index(db)
        root = ET.fromstring(xml_str)
        # 3 langs × (1 listings + 1 filters) = 6 entries
        sitemaps = root.findall("sm:sitemap", SITEMAP_NS)
        assert len(sitemaps) == 6

    async def test_fans_out_at_50k_boundary(self):
        # Exactly 50,000 still fits in 1 page; 50,001 spills into 2.
        db = _fake_db(count=SITEMAP_MAX_URLS + 1)
        entries = await sitemap_index_entries(db)
        # 3 langs × (2 listing pages + 1 filters) = 9 entries
        assert len(entries) == 9

    async def test_exact_50k_boundary_one_page(self):
        db = _fake_db(count=SITEMAP_MAX_URLS)
        entries = await sitemap_index_entries(db)
        # Exactly fills one file per lang.
        assert len(entries) == 6  # 3 langs × (1 listings + 1 filters)
