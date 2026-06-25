"""Block F V2.0 F3b — SEO router behaviour tests.

These tests inject a mocked ``get_seo_db`` so no live Postgres is
required. Covers:

* Flow G: ``GET /ru/listing/<id>/<slug>`` returns HTML with title,
  ``<meta property="og:*">``, ``<link rel="canonical">``, ``hreflang``,
  and ``<script type="application/ld+json">``.
* Flow J: TWA User-Agent → 302 redirect to ``services.deeplink``
  before the DB is queried.
* 410 Gone for deleted / non-indexable listing status.
* 301 slug-drift to canonical when the URL slug doesn't match.
* Filter route with 0 active listings → 200 + ``noindex,follow``.
* Cache-Control headers per spec (300/900/3600).
* ``robots.txt`` allow/disallow surface.
* Regression: existing ``/api/v1/...`` paths still resolve.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.database import get_seo_db
from app.db.models import ListingStatus
from app.main import app

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────


@dataclass
class _Img:
    original_url: str
    medium_url: Optional[str] = None
    large_url: Optional[str] = None
    is_primary: bool = False
    position: int = 0


def _fake_listing(
    *,
    rooms: int = 3,
    district: str = "chilonzor",
    listing_id: Optional[UUID] = None,
    status: ListingStatus = ListingStatus.ACTIVE,
    deleted_at: Optional[datetime] = None,
):
    return SimpleNamespace(
        id=listing_id or UUID("11111111-2222-3333-4444-555555555555"),
        rooms=rooms,
        district=district,
        region="toshkent_shahri",
        area=65.0,
        price=35000,
        currency="USD",
        property_type="apartment",
        type="sell",
        title=None,
        ai_description_ru="Просторная квартира в Чиланзаре.",
        ai_description_uz="Chilonzor tumanida kvartira.",
        ai_description_uz_cyrl="Чилонзор туманидаги квартира.",
        description=None,
        images=[
            _Img(
                original_url="https://cdn.example.com/o.jpg",
                large_url="https://cdn.example.com/l.jpg",
                medium_url="https://cdn.example.com/m.jpg",
                is_primary=True,
                position=0,
            )
        ],
        address=None,
        status=status,
        deleted_at=deleted_at,
        floor=4,
        total_floors=9,
        created_at=datetime(2026, 1, 1, 12, 0, 0),
        updated_at=datetime(2026, 5, 1, 12, 0, 0),
    )


def _mock_db_yielding(listing=None, listings: list | None = None, total: int = 0):
    """Build an async-iterable dependency override that yields a fake
    session whose .execute() returns the configured rows."""

    async def fake_execute(stmt):
        result = MagicMock()
        stmt_s = str(stmt)
        if "count(" in stmt_s.lower():
            result.scalar.return_value = total
            return result
        # Filter list / sitemap query.
        if listings is not None:
            scalars = MagicMock()
            scalars.all.return_value = listings
            result.scalars.return_value = scalars
            result.all.return_value = listings  # sitemap path
            result.scalar_one_or_none.return_value = None
            return result
        # Single-listing fetch.
        result.scalar_one_or_none.return_value = listing
        return result

    db = MagicMock()
    db.execute = AsyncMock(side_effect=fake_execute)

    async def override():
        yield db

    return override


@pytest.fixture
def client_with(monkeypatch):
    """Return a factory: ``client_with(db_override)`` yields an
    AsyncClient with the given dependency override applied."""

    def factory(override):
        app.dependency_overrides[get_seo_db] = override
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://testserver")

    yield factory
    app.dependency_overrides.pop(get_seo_db, None)


# ─────────────────────────────────────────────────────────────────────
# Flow G — listing detail HTML
# ─────────────────────────────────────────────────────────────────────


class TestListingDetail:
    async def test_returns_html_with_meta_and_jsonld(self, client_with):
        listing = _fake_listing()
        async with client_with(_mock_db_yielding(listing=listing)) as ac:
            resp = await ac.get(
                f"/ru/listing/{listing.id}/3-rooms-chilonzor"
            )
        assert resp.status_code == 200, resp.text
        body = resp.text
        # Title + meta description
        assert "<title>" in body
        assert 'name="description"' in body
        # canonical
        canonical_re = re.compile(
            r'<link rel="canonical" href="https://pana\.uz/ru/listing/'
            + str(listing.id)
            + r'/3-rooms-chilonzor"',
        )
        assert canonical_re.search(body)
        # hreflang trio
        for code in ("ru", "uz", "uz-latn"):
            assert f'hreflang="{code}"' in body
        # og:*
        assert 'property="og:title"' in body
        # JSON-LD with RealEstateListing
        assert '<script type="application/ld+json">' in body
        assert '"@type": "RealEstateListing"' in body
        # Cache-Control
        assert "max-age=300" in resp.headers.get("cache-control", "")

    async def test_slug_drift_301_to_canonical(self, client_with):
        listing = _fake_listing()
        async with client_with(_mock_db_yielding(listing=listing)) as ac:
            resp = await ac.get(
                f"/ru/listing/{listing.id}/wrong-slug",
                follow_redirects=False,
            )
        assert resp.status_code == 301
        loc = resp.headers["location"]
        assert loc.endswith(f"/ru/listing/{listing.id}/3-rooms-chilonzor")

    async def test_deleted_listing_returns_410(self, client_with):
        listing = _fake_listing(deleted_at=datetime(2026, 4, 1))
        async with client_with(_mock_db_yielding(listing=listing)) as ac:
            resp = await ac.get(
                f"/ru/listing/{listing.id}/3-rooms-chilonzor"
            )
        assert resp.status_code == 410
        assert "noindex" in resp.headers.get("x-robots-tag", "").lower()

    async def test_paused_listing_returns_410(self, client_with):
        listing = _fake_listing(status=ListingStatus.PAUSED)
        async with client_with(_mock_db_yielding(listing=listing)) as ac:
            resp = await ac.get(
                f"/ru/listing/{listing.id}/3-rooms-chilonzor"
            )
        assert resp.status_code == 410

    async def test_missing_listing_returns_410(self, client_with):
        async with client_with(_mock_db_yielding(listing=None)) as ac:
            resp = await ac.get(
                f"/ru/listing/{uuid4()}/anything"
            )
        assert resp.status_code == 410


# ─────────────────────────────────────────────────────────────────────
# Flow J — TWA UA bounce
# ─────────────────────────────────────────────────────────────────────


class TestTwaBounce:
    @pytest.mark.parametrize(
        "ua",
        [
            "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (TelegramWebApp/2.0)",
            "tdesktop 4.6.0",
            "Telegram-Android 10.5.1",
            "Telegram-iOS 9.7.2",
        ],
    )
    async def test_twa_ua_redirects_302(self, ua, client_with):
        # DB should never be queried — assert by failing the mock if it is.
        called = {"db": False}

        async def fake_execute(stmt):
            called["db"] = True
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            return result

        db = MagicMock()
        db.execute = AsyncMock(side_effect=fake_execute)

        async def override():
            yield db

        async with client_with(override) as ac:
            resp = await ac.get(
                f"/ru/listing/{uuid4()}/3-rooms-chilonzor",
                headers={"user-agent": ua},
                follow_redirects=False,
            )
        assert resp.status_code == 302
        assert "t.me/" in resp.headers["location"]
        assert called["db"] is False, "DB queried despite UA bounce"

    async def test_normal_ua_does_not_bounce(self, client_with):
        listing = _fake_listing()
        async with client_with(_mock_db_yielding(listing=listing)) as ac:
            resp = await ac.get(
                f"/ru/listing/{listing.id}/3-rooms-chilonzor",
                headers={"user-agent": "Googlebot/2.1"},
                follow_redirects=False,
            )
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# Filter routes — empty + populated
# ─────────────────────────────────────────────────────────────────────


class TestFilterRoutes:
    async def test_filter_empty_returns_noindex_200(self, client_with):
        async with client_with(_mock_db_yielding(listings=[], total=0)) as ac:
            resp = await ac.get("/ru/sell/apartment/chilonzor")
        assert resp.status_code == 200
        assert "noindex,follow" in resp.headers.get("x-robots-tag", "")
        assert 'name="robots" content="noindex,follow"' in resp.text

    async def test_filter_populated_returns_listings(self, client_with):
        listings = [_fake_listing()]
        async with client_with(
            _mock_db_yielding(listings=listings, total=1)
        ) as ac:
            resp = await ac.get("/ru/sell/apartment/chilonzor")
        assert resp.status_code == 200
        assert "Chilonzor" in resp.text or "Чиланзар" in resp.text

    async def test_unknown_district_returns_410(self, client_with):
        async with client_with(_mock_db_yielding(listings=[], total=0)) as ac:
            resp = await ac.get("/ru/tashkent/unknownzor")
        assert resp.status_code == 410


# ─────────────────────────────────────────────────────────────────────
# Sitemap / robots / regression
# ─────────────────────────────────────────────────────────────────────


class TestSitemapRobots:
    async def test_robots_txt(self, client_with):
        # Robots endpoint doesn't actually use the DB but the override
        # is harmless.
        async with client_with(_mock_db_yielding(listings=[], total=0)) as ac:
            resp = await ac.get("/robots.txt")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        for line in ("Allow: /ru/", "Allow: /uz/", "Disallow: /api/", "Disallow: /admin/"):
            assert line in resp.text
        # Cache-Control 3600
        assert "max-age=3600" in resp.headers["cache-control"]

    async def test_sitemap_index(self, client_with):
        async with client_with(_mock_db_yielding(total=0)) as ac:
            resp = await ac.get("/sitemap.xml")
        assert resp.status_code == 200
        assert "application/xml" in resp.headers["content-type"]
        assert "<sitemapindex" in resp.text
        assert "max-age=900" in resp.headers["cache-control"]

    async def test_sitemap_listings(self, client_with):
        async with client_with(_mock_db_yielding(listings=[])) as ac:
            resp = await ac.get("/sitemap-ru-listings-1.xml")
        assert resp.status_code == 200
        assert "<urlset" in resp.text


class TestRegression:
    async def test_api_v1_health_still_resolves(self, client_with):
        """The SEO router is mounted at root, but ``/api/v1/...`` routes
        still match first. Smoke-test the health endpoint (no auth)."""
        # Need *some* override for get_seo_db so the fixture cleans up.
        async with client_with(_mock_db_yielding(listings=[])) as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"

    async def test_root_still_resolves(self, client_with):
        async with client_with(_mock_db_yielding(listings=[])) as ac:
            resp = await ac.get("/")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Real Estate API"
