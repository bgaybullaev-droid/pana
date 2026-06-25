"""Block F V2.0 F3a — SEO template smoke renders.

These are not byte-exact snapshot tests (the spec calls them snapshot
tests; here we keep them as structural assertions that survive cosmetic
template edits while still catching regressions to schema.org JSON-LD,
canonical/hreflang tags, and `<meta name="robots">` flags).

Run with::

    pytest -m unit backend/tests/unit/test_seo_templates.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from uuid import uuid4

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.services.seo_meta import (
    build_filter_meta,
    build_listing_jsonld,
    build_listing_meta,
)

pytestmark = [pytest.mark.unit]


TEMPLATES_DIR = (
    Path(__file__).resolve().parents[2] / "app" / "templates"
)


@pytest.fixture(scope="module")
def jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


@dataclass
class _Img:
    original_url: str
    medium_url: Optional[str] = None
    large_url: Optional[str] = None
    is_primary: bool = False
    position: int = 0


def _listing():
    return SimpleNamespace(
        id=uuid4(),
        rooms=3,
        district="chilonzor",
        region="toshkent_shahri",
        area=65.0,
        price=35000,
        currency="USD",
        property_type="apartment",
        type="sell",
        title=None,
        ai_description_ru="Просторная трёхкомнатная квартира в Чиланзаре.",
        ai_description_uz="Chilonzor tumanida 3-xonali kvartira.",
        ai_description_uz_cyrl="Чилонзор туманидаги 3 хонали квартира.",
        description=None,
        images=[
            _Img(
                original_url="https://cdn.example.com/orig.jpg",
                large_url="https://cdn.example.com/large.jpg",
                medium_url="https://cdn.example.com/medium.jpg",
                is_primary=True,
            )
        ],
        address=None,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 5, 1),
    )


# ─────────────────────────────────────────────────────────────────────
# listing.html
# ─────────────────────────────────────────────────────────────────────


def test_listing_template_renders_canonical_jsonld_and_meta(jinja_env):
    l = _listing()
    meta = build_listing_meta(l, "ru")
    jsonld = json.dumps(build_listing_jsonld(l, "ru"), ensure_ascii=False)
    html = jinja_env.get_template("seo/listing.html").render(
        lang="ru",
        meta=meta,
        jsonld=jsonld,
        images=[{"url": img.large_url} for img in l.images],
        price_display="35 000 у.е.",
        description=l.ai_description_ru,
        params=[
            {"label": "Площадь", "value": "65 м²"},
            {"label": "Комнат", "value": 3},
        ],
        labels={"params": "Параметры", "cta": "Открыть в UcharMarket"},
        deeplink="https://t.me/UcharMarketBot?startapp=listing_xxx",
        year=2026,
    )
    # canonical + hreflang
    assert f'<link rel="canonical" href="{meta.canonical}">' in html
    for code in ("ru", "uz", "uz-latn"):
        assert f'hreflang="{code}"' in html
    # JSON-LD block
    assert '<script type="application/ld+json">' in html
    assert '"@type": "RealEstateListing"' in html
    # og:* tags
    assert 'property="og:title"' in html
    assert 'property="og:image"' in html
    # CTA
    assert "UcharMarketBot" in html


def test_listing_template_safe_without_image(jinja_env):
    l = _listing()
    l.images = []
    meta = build_listing_meta(l, "ru")
    jsonld = json.dumps(build_listing_jsonld(l, "ru"), ensure_ascii=False)
    html = jinja_env.get_template("seo/listing.html").render(
        lang="ru",
        meta=meta,
        jsonld=jsonld,
        images=[],
        price_display="",
        description=l.ai_description_ru,
        params=[],
        labels={"params": "Параметры", "cta": "Открыть"},
        deeplink="https://t.me/Bot?startapp=listing_y",
        year=2026,
    )
    # og:image absent when no photo
    assert 'property="og:image"' not in html


# ─────────────────────────────────────────────────────────────────────
# filter.html / empty.html / gone.html
# ─────────────────────────────────────────────────────────────────────


def test_filter_template_renders_listing_links(jinja_env):
    meta = build_filter_meta(
        {"deal": "sell", "property_type": "apartment", "district": "chilonzor"}, "ru"
    )
    html = jinja_env.get_template("seo/filter.html").render(
        lang="ru",
        meta=meta,
        intro=None,
        listings=[
            {"url": "https://pana.uz/ru/listing/abc/3-rooms-chilonzor", "title": "3-комн в Чиланзаре", "price_display": "35 000 у.е."},
            {"url": "https://pana.uz/ru/listing/def/2-rooms-chilonzor", "title": "2-комн в Чиланзаре", "price_display": "28 000 у.е."},
        ],
        pagination=None,
        labels={"empty": "Пусто", "prev": "Назад", "next": "Вперёд", "open_app": "Открыть"},
        deeplink="https://t.me/UcharMarketBot",
        year=2026,
    )
    assert "3-комн в Чиланзаре" in html
    assert "pana.uz/ru/listing/abc" in html


def test_empty_template_emits_noindex(jinja_env):
    meta = build_filter_meta({"district": "chilonzor"}, "ru")
    html = jinja_env.get_template("seo/empty.html").render(
        lang="ru",
        meta=meta,
        labels={"empty_body": "Сейчас нет объявлений", "open_app": "Открыть"},
        deeplink="https://t.me/UcharMarketBot",
        year=2026,
    )
    assert 'name="robots" content="noindex,follow"' in html


def test_gone_template_renders(jinja_env):
    html = jinja_env.get_template("seo/gone.html").render(
        lang="ru",
        labels={
            "gone_title": "Объявление снято",
            "gone_body": "Это объявление больше не актуально.",
            "gone_cta": "На главную",
        },
        home_url="https://pana.uz/ru/",
    )
    assert 'name="robots" content="noindex,follow"' in html
    assert "Объявление снято" in html


# ─────────────────────────────────────────────────────────────────────
# robots.txt + sitemap XML
# ─────────────────────────────────────────────────────────────────────


def test_robots_allows_lang_paths(jinja_env):
    body = jinja_env.get_template("seo/robots.txt").render(
        public_host="https://pana.uz"
    )
    for line in ("Allow: /ru/", "Allow: /uz/", "Allow: /uz-latn/"):
        assert line in body
    for line in ("Disallow: /api/", "Disallow: /admin/", "Disallow: /seller/", "Disallow: /uploads/"):
        assert line in body
    assert "Sitemap: https://pana.uz/sitemap.xml" in body


def test_sitemap_listings_template_renders(jinja_env):
    body = jinja_env.get_template("seo/sitemap_listings.xml").render(
        entries=[
            SimpleNamespace(
                loc="https://pana.uz/ru/listing/abc/3-rooms",
                lastmod="2026-05-01T12:00:00",
                changefreq="daily",
                priority="0.7",
            )
        ]
    )
    assert "<urlset" in body
    assert "<lastmod>2026-05-01T12:00:00</lastmod>" in body


def test_sitemap_index_template_renders(jinja_env):
    body = jinja_env.get_template("seo/sitemap_index.xml").render(
        sitemaps=[
            SimpleNamespace(
                loc="https://pana.uz/sitemap-ru-listings-1.xml",
                lastmod="2026-05-01T12:00:00",
            )
        ]
    )
    assert "<sitemapindex" in body
    assert "sitemap-ru-listings-1.xml" in body
