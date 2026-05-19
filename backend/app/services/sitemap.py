"""Block F V2.0 (F3a) — sitemap.org-compatible XML generators.

Pure async services. The SEO router (F3b) wires these to
``/sitemap.xml`` and friends. The 50,000-URL-per-file cap is the
sitemaps.org hard limit (and Google's hard rejection threshold).

Public surface:
    build_listings_sitemap(db, lang, page)  → urlset XML
    build_filters_sitemap(db, lang)         → urlset XML
    build_sitemap_index(db)                 → sitemapindex XML
"""

from __future__ import annotations

import logging
import xml.sax.saxutils as _xml_escape
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Listing, ListingStatus
from app.services.seo_meta import (
    SUPPORTED_LANGS,
    _filter_canonical_path,  # internal helper, re-used for filter URLs
    _public_host,
    slug_for_listing,
)

logger = logging.getLogger(__name__)

# sitemap.org hard limits.
SITEMAP_MAX_URLS = 50_000
SITEMAP_MAX_BYTES = 50 * 1024 * 1024

# Per-URL <changefreq>/<priority> defaults — tuned for an aggregator
# where listings churn within days, filter pages are evergreen.
_DEFAULT_CHANGEFREQ_LISTINGS = "daily"
_DEFAULT_PRIORITY_LISTINGS = "0.7"
_DEFAULT_CHANGEFREQ_FILTERS = "weekly"
_DEFAULT_PRIORITY_FILTERS = "0.5"


# ─────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────


def _xe(value: str) -> str:
    """XML-escape a string for use inside ``<loc>``/``<lastmod>``."""
    return _xml_escape.escape(value, {'"': "&quot;", "'": "&apos;"})


def _format_lastmod(dt: Optional[datetime]) -> str:
    """W3C-datetime / ISO-8601 with second precision; UTC."""
    if dt is None:
        return ""
    return dt.replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class SitemapEntry:
    """One ``<url>`` row of a sitemap or one ``<sitemap>`` row of the index.

    ``lastmod`` is stored as a stringified ISO datetime on the way out
    so Jinja2 templates can render it directly.
    """

    loc: str
    lastmod: Optional[str] = None
    changefreq: str = "weekly"
    priority: str = "0.5"


# Backwards-compat alias for the internal renderer below.
_SitemapEntry = SitemapEntry


def _render_urlset(entries: Iterable[SitemapEntry]) -> str:
    """Serialise a sequence of entries into a sitemaps.org ``<urlset>``."""
    body = ["<?xml version='1.0' encoding='UTF-8'?>"]
    body.append(
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
    )
    for e in entries:
        body.append("  <url>")
        body.append(f"    <loc>{_xe(e.loc)}</loc>")
        if e.lastmod:
            body.append(f"    <lastmod>{_xe(e.lastmod)}</lastmod>")
        body.append(f"    <changefreq>{e.changefreq}</changefreq>")
        body.append(f"    <priority>{e.priority}</priority>")
        body.append("  </url>")
    body.append("</urlset>")
    return "\n".join(body) + "\n"


def _render_sitemapindex(entries: Iterable[SitemapEntry]) -> str:
    body = ["<?xml version='1.0' encoding='UTF-8'?>"]
    body.append(
        "<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
    )
    for e in entries:
        body.append("  <sitemap>")
        body.append(f"    <loc>{_xe(e.loc)}</loc>")
        if e.lastmod:
            body.append(f"    <lastmod>{_xe(e.lastmod)}</lastmod>")
        body.append("  </sitemap>")
    body.append("</sitemapindex>")
    return "\n".join(body) + "\n"


# ─────────────────────────────────────────────────────────────────────
# Listings sitemap
# ─────────────────────────────────────────────────────────────────────


def _ssr_indexable_statuses() -> tuple[ListingStatus, ...]:
    """Listing statuses that render an indexable HTML page.

    Mirrors F3 spec §"Behavior — Listing route: 200 HTML if status ∈
    {ACTIVE, GENERATION_FAILED}".
    """
    return (ListingStatus.ACTIVE, ListingStatus.GENERATION_FAILED)


async def _count_listings(db: AsyncSession) -> int:
    stmt = (
        select(func.count(Listing.id))
        .where(Listing.deleted_at.is_(None))
        .where(Listing.status.in_(_ssr_indexable_statuses()))
    )
    return int((await db.execute(stmt)).scalar() or 0)


async def build_listings_sitemap(
    db: AsyncSession, lang: str, page: int = 1
) -> str:
    """Paginated sitemap for active listings in *lang*.

    *page* is 1-indexed. Each page holds at most ``SITEMAP_MAX_URLS``
    (50k) URLs per sitemaps.org. Listings drained ordered by
    ``updated_at DESC`` so fresh changes propagate to the head of the
    first page.
    """
    if lang not in SUPPORTED_LANGS:
        lang = "ru"
    if page < 1:
        page = 1

    offset = (page - 1) * SITEMAP_MAX_URLS
    stmt = (
        select(
            Listing.id,
            Listing.rooms,
            Listing.district,
            Listing.updated_at,
        )
        .where(Listing.deleted_at.is_(None))
        .where(Listing.status.in_(_ssr_indexable_statuses()))
        .order_by(Listing.updated_at.desc())
        .offset(offset)
        .limit(SITEMAP_MAX_URLS)
    )
    entries = await listings_sitemap_entries(db, lang, page)
    logger.info(
        "sitemap.generated kind=listings lang=%s page=%d entries=%d",
        lang,
        page,
        len(entries),
    )
    return _render_urlset(entries)


async def listings_sitemap_entries(
    db: AsyncSession, lang: str, page: int = 1
) -> list[SitemapEntry]:
    """Structured form of the listing sitemap — for Jinja2 template
    rendering. The string variant ``build_listings_sitemap`` wraps this
    and is the path used by the SEO router when it's cheaper to skip
    Jinja altogether."""
    if lang not in SUPPORTED_LANGS:
        lang = "ru"
    if page < 1:
        page = 1

    offset = (page - 1) * SITEMAP_MAX_URLS
    stmt = (
        select(
            Listing.id,
            Listing.rooms,
            Listing.district,
            Listing.updated_at,
        )
        .where(Listing.deleted_at.is_(None))
        .where(Listing.status.in_(_ssr_indexable_statuses()))
        .order_by(Listing.updated_at.desc())
        .offset(offset)
        .limit(SITEMAP_MAX_URLS)
    )
    rows = (await db.execute(stmt)).all()

    host = _public_host()
    entries: list[SitemapEntry] = []
    for row in rows:
        stub = _ListingStub(id=row.id, rooms=row.rooms, district=row.district)
        slug = slug_for_listing(stub)
        loc = f"{host}/{lang}/listing/{row.id}/{slug}"
        entries.append(
            SitemapEntry(
                loc=loc,
                lastmod=_format_lastmod(row.updated_at) or None,
                changefreq=_DEFAULT_CHANGEFREQ_LISTINGS,
                priority=_DEFAULT_PRIORITY_LISTINGS,
            )
        )
    return entries


@dataclass(frozen=True)
class _ListingStub:
    """Minimal Listing-shaped duck for ``slug_for_listing``."""

    id: object
    rooms: Optional[int]
    district: Optional[str]


# ─────────────────────────────────────────────────────────────────────
# Filters sitemap
# ─────────────────────────────────────────────────────────────────────


# 3-param-depth indexable filter shapes per F3 spec.
_DEALS = ("sell", "rent")
_PROPS = ("apartment", "house", "commercial", "land")


async def _filter_combos_with_listings(
    db: AsyncSession,
) -> Sequence[tuple[str, str, Optional[str], Optional[int]]]:
    """Distinct (deal, property_type, district, rooms) combos that
    currently have at least one indexable listing. Anything with zero
    active listings is excluded from the sitemap (renders as
    ``noindex`` per F3 spec; including it would invite re-crawls of
    no-content pages).
    """
    stmt = (
        select(
            Listing.type,
            Listing.property_type,
            Listing.district,
            Listing.rooms,
        )
        .where(Listing.deleted_at.is_(None))
        .where(Listing.status.in_(_ssr_indexable_statuses()))
        .distinct()
    )
    rows = (await db.execute(stmt)).all()
    out: list[tuple[str, str, Optional[str], Optional[int]]] = []
    for row in rows:
        deal_raw = row.type
        deal = deal_raw.value if hasattr(deal_raw, "value") else deal_raw
        prop_raw = row.property_type
        prop = prop_raw.value if hasattr(prop_raw, "value") else prop_raw
        if deal not in _DEALS or prop not in _PROPS:
            continue
        out.append((deal, prop, row.district, row.rooms))
    return out


async def build_filters_sitemap(db: AsyncSession, lang: str) -> str:
    """Sitemap of every base filter URL with at least one active listing.

    Enumerates 4 depths (district-only, deal×type, deal×type×district,
    deal×type×rooms×district) and deduplicates so identical paths
    collapse to a single URL entry.
    """
    entries = await filters_sitemap_entries(db, lang)
    logger.info(
        "sitemap.generated kind=filters lang=%s entries=%d", lang, len(entries)
    )
    return _render_urlset(entries)


async def filters_sitemap_entries(
    db: AsyncSession, lang: str
) -> list[SitemapEntry]:
    """Structured form of the filter sitemap — for Jinja2 template
    rendering. See ``build_filters_sitemap`` for behaviour."""
    if lang not in SUPPORTED_LANGS:
        lang = "ru"

    combos = await _filter_combos_with_listings(db)

    from app.services.seo_meta import _normalize_district_key

    seen: dict[str, SitemapEntry] = {}

    def _add(path: str) -> None:
        host = _public_host()
        loc = f"{host}{path}"
        if loc in seen:
            return
        seen[loc] = SitemapEntry(
            loc=loc,
            lastmod=None,
            changefreq=_DEFAULT_CHANGEFREQ_FILTERS,
            priority=_DEFAULT_PRIORITY_FILTERS,
        )

    for deal, prop, district_raw, rooms in combos:
        district_key = _normalize_district_key(district_raw)
        if district_key:
            _add(_filter_canonical_path(lang, None, None, None, district_key))
        _add(_filter_canonical_path(lang, deal, prop, None, None))
        if district_key:
            _add(_filter_canonical_path(lang, deal, prop, None, district_key))
        if district_key and rooms is not None and rooms > 0:
            _add(_filter_canonical_path(lang, deal, prop, int(rooms), district_key))

    return list(seen.values())


# ─────────────────────────────────────────────────────────────────────
# Sitemap index
# ─────────────────────────────────────────────────────────────────────


async def build_sitemap_index(db: AsyncSession) -> str:
    """Top-level ``<sitemapindex>`` enumerating per-lang/per-page sitemaps.

    A single 50k page per lang is the steady-state expectation; the
    index correctly fans out to N pages when the active-listings count
    exceeds the per-file limit.
    """
    entries = await sitemap_index_entries(db)
    logger.info("sitemap.generated kind=index entries=%d", len(entries))
    return _render_sitemapindex(entries)


async def sitemap_index_entries(db: AsyncSession) -> list[SitemapEntry]:
    """Structured form of the sitemap index — for Jinja2 template rendering."""
    total = await _count_listings(db)
    pages = max(1, (total + SITEMAP_MAX_URLS - 1) // SITEMAP_MAX_URLS)
    host = _public_host()
    now_iso = _format_lastmod(datetime.utcnow())
    entries: list[SitemapEntry] = []
    for lang in SUPPORTED_LANGS:
        for page in range(1, pages + 1):
            entries.append(
                SitemapEntry(
                    loc=f"{host}/sitemap-{lang}-listings-{page}.xml",
                    lastmod=now_iso,
                )
            )
        entries.append(
            SitemapEntry(
                loc=f"{host}/sitemap-{lang}-filters.xml",
                lastmod=now_iso,
            )
        )
    return entries


# Re-export for the router so it doesn't have to import settings directly.
PUBLIC_HOST = settings.f3_public_web_host
