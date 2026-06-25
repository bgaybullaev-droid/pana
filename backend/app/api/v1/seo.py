"""Block F V2.0 (F3b) — SSR routes for SEO traffic.

Mounted at the **root** of the FastAPI app (no `/api/v1` prefix). API
routes still match first because ``main.py`` registers
``api_v1_router`` before this one.

Routes (9):
    GET  /robots.txt
    GET  /sitemap.xml
    GET  /sitemap-{lang}-listings-{page}.xml
    GET  /sitemap-{lang}-filters.xml
    GET  /{lang}/listing/{listing_id}/{slug}
    GET  /{lang}/tashkent/{district}
    GET  /{lang}/{deal}/{property_type}/{rooms_slug}/{district}
    GET  /{lang}/{deal}/{property_type}/{district}
    GET  /{lang}/{deal}/{property_type}

Behaviour:
    * Listing route: 200 HTML if status ∈ {ACTIVE, GENERATION_FAILED};
      301 to canonical when slug drifted; 410 Gone otherwise.
    * Filter route with 0 active listings → 200 + ``noindex,follow``.
    * Beyond 3-param filter depth → 404 (FastAPI never registers).
    * UA containing ``TelegramWebApp`` / ``tdesktop`` → 302 to deep
      link, before any DB hit on the listing route.
    * Cache-Control: 300s for content, 900s for sitemap, 3600s robots.

All DB access uses ``get_seo_db`` (Block F F3a) — a read-only pool so a
Googlebot burst can't starve the API pool.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path as APIPath, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.regions import DISTRICT_TO_REGION
from app.db.database import get_seo_db
from app.db.models import Listing, ListingImage, ListingStatus, PropertyType
from app.services.deeplink import build_listing_link
from app.services.seo_meta import (
    SUPPORTED_LANGS,
    _LANG_TO_AI_FIELD,
    _district_label,
    _filter_canonical_path,
    _format_price,
    _normalize_district_key,
    _public_host,
    build_filter_meta,
    build_listing_jsonld,
    build_listing_meta,
    slug_for_listing,
)
from app.services.sitemap import (
    build_filters_sitemap,
    build_listings_sitemap,
    build_sitemap_index,
)

logger = logging.getLogger(__name__)

# Mounted by main.py at the root of the app; ``app/templates`` is the
# Jinja2 search root, so we reference templates via ``seo/<name>``.
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
templates = Jinja2Templates(directory=str(_BACKEND_ROOT / "app" / "templates"))


router = APIRouter(tags=["SEO"], include_in_schema=False)


# ─────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────


# Cache-Control TTLs (seconds). Per F3 spec.
_CACHE_CONTENT = "public, max-age=300"
_CACHE_SITEMAP = "public, max-age=900"
_CACHE_ROBOTS = "public, max-age=3600"

# Indexable statuses per F3 spec — anything else collapses to 410 Gone.
_INDEXABLE_STATUSES = (ListingStatus.ACTIVE, ListingStatus.GENERATION_FAILED)

# Lang / deal / property regex used by Path validators so malformed
# URLs short-circuit with 422 → caller-side they look like 404s.
_LANG_REGEX = r"^(ru|uz|uz-latn)$"
_DEAL_REGEX = r"^(sell|rent)$"
_PROPERTY_REGEX = r"^(apartment|house|commercial|land)$"
_ROOMS_SLUG_REGEX = r"^[1-9][0-9]?-rooms$"
_DISTRICT_SLUG_REGEX = r"^[a-z][a-z0-9-]{0,40}$"

# Items per filter page.
_FILTER_PAGE_SIZE = 20

# Telegram clients that should bounce out of SSR back into the Mini App.
_TWA_UA_NEEDLES = ("TelegramWebApp", "tdesktop", "Telegram-Android", "Telegram-iOS")


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _twa_bounce_url(listing_id: Optional[UUID]) -> str:
    """Where to send a TWA-UA visitor. Listings deeplink; everything
    else falls back to the bot home so the user opens the Mini App.
    """
    if listing_id is not None:
        return build_listing_link(listing_id)
    bot = settings.telegram_bot_username or "UcharMarketBot"
    return f"https://t.me/{bot}"


def _twa_bounce_response(
    request: Request, listing_id: Optional[UUID] = None
) -> Optional[RedirectResponse]:
    """Return a 302 RedirectResponse iff the requesting UA looks like a
    Telegram in-app browser. None otherwise."""
    ua = request.headers.get("user-agent", "") or ""
    if not ua:
        return None
    for needle in _TWA_UA_NEEDLES:
        if needle in ua:
            target = _twa_bounce_url(listing_id)
            logger.info(
                "seo.twa_bounce path=%s ua=%s",
                request.url.path,
                ua[:80],
            )
            return RedirectResponse(url=target, status_code=302)
    return None


def _set_headers(response: Response, cache: str) -> None:
    response.headers["Cache-Control"] = cache
    response.headers["X-Robots-Tag"] = "all"


def _common_labels(lang: str) -> dict[str, str]:
    if lang == "ru":
        return {
            "params": "Параметры",
            "cta": "Открыть в PANA",
            "open_app": "Открыть в PANA",
            "empty": "Сейчас нет объявлений",
            "empty_body": "Сейчас по этим параметрам объявлений нет. Попробуйте расширить поиск в приложении.",
            "prev": "Назад",
            "next": "Вперёд",
            "gone_title": "Объявление снято",
            "gone_body": "Это объявление больше не актуально.",
            "gone_cta": "На главную",
        }
    if lang == "uz-latn":
        return {
            "params": "Parametrlar",
            "cta": "PANA'da ochish",
            "open_app": "PANA'da ochish",
            "empty": "Hozircha e'lonlar yo'q",
            "empty_body": "Hozircha bu parametrlar bo'yicha e'lonlar yo'q. Ilovada izlovni kengaytiring.",
            "prev": "Orqaga",
            "next": "Oldinga",
            "gone_title": "E'lon olindi",
            "gone_body": "Bu e'lon endi dolzarb emas.",
            "gone_cta": "Bosh sahifaga",
        }
    # uz (Cyrillic)
    return {
        "params": "Параметрлар",
        "cta": "PANA'да очиш",
        "open_app": "PANA'да очиш",
        "empty": "Ҳозирча эълонлар йўқ",
        "empty_body": "Ҳозирча бу параметрлар бўйича эълонлар йўқ. Иловада изловни кенгайтиринг.",
        "prev": "Орқага",
        "next": "Олдинга",
        "gone_title": "Эълон олинди",
        "gone_body": "Бу эълон энди долзарб эмас.",
        "gone_cta": "Бош саҳифага",
    }


def _ai_description_for(listing: Listing, lang: str) -> str:
    field = _LANG_TO_AI_FIELD.get(lang, "ai_description_ru")
    value = getattr(listing, field, None) or ""
    if value:
        return value
    for fallback in ("ai_description_ru", "ai_description_uz", "ai_description_uz_cyrl"):
        v = getattr(listing, fallback, None)
        if v:
            return v
    return getattr(listing, "description", None) or ""


def _params_block(listing: Listing, lang: str) -> list[dict]:
    """Build the structured `<ul>` rows for the params section."""
    labels_ru = {
        "rooms": "Комнат",
        "area": "Площадь",
        "floor": "Этаж",
        "total_floors": "Этажей в доме",
        "property_type": "Тип",
        "deal": "Тип сделки",
    }
    labels_uz_latn = {
        "rooms": "Xonalar",
        "area": "Maydon",
        "floor": "Qavat",
        "total_floors": "Binoda qavat",
        "property_type": "Tur",
        "deal": "Bitim turi",
    }
    labels_uz_cyrl = {
        "rooms": "Хоналар",
        "area": "Майдон",
        "floor": "Қават",
        "total_floors": "Бинода қават",
        "property_type": "Тур",
        "deal": "Битим тури",
    }
    labels = (
        labels_ru
        if lang == "ru"
        else labels_uz_latn
        if lang == "uz-latn"
        else labels_uz_cyrl
    )

    rows: list[dict] = []
    rooms = getattr(listing, "rooms", None)
    if rooms:
        rows.append({"label": labels["rooms"], "value": int(rooms)})
    area = getattr(listing, "area", None)
    if area:
        try:
            af = float(area)
            unit = "м²" if lang == "ru" else "m²"
            rows.append({"label": labels["area"], "value": f"{af:g} {unit}"})
        except (TypeError, ValueError):
            pass
    floor = getattr(listing, "floor", None)
    total = getattr(listing, "total_floors", None)
    if floor and total:
        rows.append({"label": labels["floor"], "value": f"{int(floor)}/{int(total)}"})
    elif floor:
        rows.append({"label": labels["floor"], "value": int(floor)})
    return rows


def _format_price_for(listing: Listing, lang: str) -> str:
    cur_raw = getattr(listing, "currency", None)
    cur = cur_raw.value if cur_raw is not None and hasattr(cur_raw, "value") else cur_raw
    return _format_price(getattr(listing, "price", None), cur, lang)


# ─────────────────────────────────────────────────────────────────────
# /robots.txt + /sitemap*.xml
# ─────────────────────────────────────────────────────────────────────


@router.get("/robots.txt")
async def robots_txt(request: Request) -> Response:
    body = templates.get_template("seo/robots.txt").render(public_host=_public_host())
    resp = Response(content=body, media_type="text/plain; charset=utf-8")
    _set_headers(resp, _CACHE_ROBOTS)
    return resp


@router.get("/sitemap.xml")
async def sitemap_index(db: AsyncSession = Depends(get_seo_db)) -> Response:
    try:
        body = await build_sitemap_index(db)
    except Exception:  # pragma: no cover — keep old sitemap path alive
        logger.exception("sitemap.rebuild_failed kind=index")
        raise HTTPException(status_code=503, detail="sitemap_unavailable")
    resp = Response(content=body, media_type="application/xml; charset=utf-8")
    _set_headers(resp, _CACHE_SITEMAP)
    return resp


@router.get("/sitemap-{lang}-listings-{page}.xml")
async def sitemap_listings(
    lang: str = APIPath(..., pattern=_LANG_REGEX),
    page: int = APIPath(..., ge=1, le=10_000),
    db: AsyncSession = Depends(get_seo_db),
) -> Response:
    try:
        body = await build_listings_sitemap(db, lang, page=page)
    except Exception:  # pragma: no cover
        logger.exception(
            "sitemap.rebuild_failed kind=listings lang=%s page=%d", lang, page
        )
        raise HTTPException(status_code=503, detail="sitemap_unavailable")
    resp = Response(content=body, media_type="application/xml; charset=utf-8")
    _set_headers(resp, _CACHE_SITEMAP)
    return resp


@router.get("/sitemap-{lang}-filters.xml")
async def sitemap_filters(
    lang: str = APIPath(..., pattern=_LANG_REGEX),
    db: AsyncSession = Depends(get_seo_db),
) -> Response:
    try:
        body = await build_filters_sitemap(db, lang)
    except Exception:  # pragma: no cover
        logger.exception("sitemap.rebuild_failed kind=filters lang=%s", lang)
        raise HTTPException(status_code=503, detail="sitemap_unavailable")
    resp = Response(content=body, media_type="application/xml; charset=utf-8")
    _set_headers(resp, _CACHE_SITEMAP)
    return resp


# ─────────────────────────────────────────────────────────────────────
# /{lang}/listing/{id}/{slug}
# ─────────────────────────────────────────────────────────────────────


def _render_gone(request: Request, lang: str, reason: str) -> Response:
    logger.info("seo.gone path=%s reason=%s", request.url.path, reason)
    labels = _common_labels(lang)
    body = templates.get_template("seo/gone.html").render(
        lang=lang,
        labels=labels,
        home_url=f"{_public_host()}/{lang}/",
    )
    resp = HTMLResponse(content=body, status_code=410)
    resp.headers["X-Robots-Tag"] = "noindex,follow"
    resp.headers["Cache-Control"] = _CACHE_CONTENT
    return resp


@router.get("/{lang}/listing/{listing_id}/{slug}")
async def listing_detail(
    request: Request,
    lang: str = APIPath(..., pattern=_LANG_REGEX),
    listing_id: UUID = APIPath(...),
    slug: str = APIPath(..., min_length=1, max_length=60),
    db: AsyncSession = Depends(get_seo_db),
) -> Response:
    start_ts = datetime.utcnow()

    # 1. UA bounce *before* DB hit so misbehaving Telegram clients don't
    #    hammer the read pool.
    if (bounce := _twa_bounce_response(request, listing_id)) is not None:
        return bounce

    # 2. Fetch the listing + primary image.
    stmt = (
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.images))
    )
    listing = (await db.execute(stmt)).scalar_one_or_none()
    if listing is None:
        return _render_gone(request, lang, reason="missing")
    if listing.deleted_at is not None:
        return _render_gone(request, lang, reason="deleted")
    if listing.status not in _INDEXABLE_STATUSES:
        return _render_gone(request, lang, reason=f"status:{listing.status.value}")

    # 3. Slug drift → 301 to canonical.
    canonical_slug = slug_for_listing(listing)
    if slug != canonical_slug:
        canonical = f"{_public_host()}/{lang}/listing/{listing.id}/{canonical_slug}"
        logger.info(
            "seo.slug_redirect from=%s to=%s",
            request.url.path,
            canonical,
        )
        return RedirectResponse(url=canonical, status_code=301)

    # 4. Render.
    meta = build_listing_meta(listing, lang)
    jsonld = json.dumps(build_listing_jsonld(listing, lang), ensure_ascii=False)
    images = [
        {"url": img.large_url or img.medium_url or img.original_url}
        for img in (listing.images or [])
        if (img.large_url or img.medium_url or img.original_url)
    ]
    description = _ai_description_for(listing, lang)
    price_display = _format_price_for(listing, lang)
    params = _params_block(listing, lang)
    deeplink = build_listing_link(listing.id)

    body = templates.get_template("seo/listing.html").render(
        request=request,
        lang=lang,
        meta=meta,
        jsonld=jsonld,
        images=images,
        price_display=price_display,
        description=description,
        params=params,
        labels=_common_labels(lang),
        deeplink=deeplink,
        year=datetime.utcnow().year,
    )

    resp = HTMLResponse(content=body, status_code=200)
    _set_headers(resp, _CACHE_CONTENT)
    duration_ms = int((datetime.utcnow() - start_ts).total_seconds() * 1000)
    logger.info(
        "seo.rendered path=%s listing_status=%s duration_ms=%d",
        request.url.path,
        listing.status.value,
        duration_ms,
    )
    return resp


# ─────────────────────────────────────────────────────────────────────
# Filter pages
# ─────────────────────────────────────────────────────────────────────


def _to_property_enum(prop: str) -> Optional[PropertyType]:
    try:
        return PropertyType(prop)
    except ValueError:
        return None


async def _query_filter_listings(
    db: AsyncSession,
    *,
    deal: Optional[str],
    property_type: Optional[str],
    district_key: Optional[str],
    rooms: Optional[int],
    page: int,
) -> tuple[list[Listing], int]:
    """Run the filter query against the SEO read-only pool. Returns
    (rows, total_count). Empty list + zero count → render empty.html.
    """
    where = [Listing.deleted_at.is_(None), Listing.status.in_(_INDEXABLE_STATUSES)]
    if deal:
        where.append(Listing.type == deal)
    if property_type:
        prop = _to_property_enum(property_type)
        if prop is None:
            return [], 0
        where.append(Listing.property_type == prop)
    if district_key:
        where.append(Listing.district == district_key)
    if rooms:
        where.append(Listing.rooms == rooms)

    count_stmt = select(func.count(Listing.id)).where(*where)
    total = int((await db.execute(count_stmt)).scalar() or 0)

    list_stmt = (
        select(Listing)
        .where(*where)
        .order_by(Listing.updated_at.desc())
        .offset((page - 1) * _FILTER_PAGE_SIZE)
        .limit(_FILTER_PAGE_SIZE)
        .options(selectinload(Listing.images))
    )
    rows = list((await db.execute(list_stmt)).scalars().all())
    return rows, total


def _render_filter_page(
    request: Request,
    lang: str,
    meta_filters: dict,
    *,
    page: int,
    listings: list[Listing],
    total: int,
) -> Response:
    """Common renderer for all filter shapes (district-only, deal+type,
    etc.). Empty result → empty.html with noindex,follow; otherwise
    filter.html with up to 20 rows + pagination links."""
    meta = build_filter_meta(meta_filters, lang)
    labels = _common_labels(lang)
    bot_url = _twa_bounce_url(None)

    if total == 0 or not listings:
        body = templates.get_template("seo/empty.html").render(
            request=request,
            lang=lang,
            meta=meta,
            labels=labels,
            deeplink=bot_url,
            year=datetime.utcnow().year,
        )
        resp = HTMLResponse(content=body, status_code=200)
        # empty.html sets its own <meta robots>; reinforce with header.
        resp.headers["X-Robots-Tag"] = "noindex,follow"
        resp.headers["Cache-Control"] = _CACHE_CONTENT
        logger.info("seo.noindex_empty path=%s", request.url.path)
        return resp

    rows = []
    for l in listings:
        item_meta = build_listing_meta(l, lang)
        rows.append(
            {
                "url": item_meta.canonical,
                "title": item_meta.title.split(" — ")[0],
                "price_display": _format_price_for(l, lang),
            }
        )

    total_pages = max(1, (total + _FILTER_PAGE_SIZE - 1) // _FILTER_PAGE_SIZE)
    pagination = {
        "page": page,
        "total_pages": total_pages,
        "prev_url": (
            f"{meta.canonical}?page={page - 1}" if page > 1 else None
        ),
        "next_url": (
            f"{meta.canonical}?page={page + 1}" if page < total_pages else None
        ),
    }

    body = templates.get_template("seo/filter.html").render(
        request=request,
        lang=lang,
        meta=meta,
        intro=None,
        listings=rows,
        pagination=pagination,
        labels=labels,
        deeplink=bot_url,
        year=datetime.utcnow().year,
    )
    resp = HTMLResponse(content=body, status_code=200)
    _set_headers(resp, _CACHE_CONTENT)
    logger.info(
        "seo.rendered path=%s kind=filter total=%d page=%d",
        request.url.path,
        total,
        page,
    )
    return resp


# District-only landing: /{lang}/tashkent/{district}
@router.get("/{lang}/tashkent/{district}")
async def filter_district(
    request: Request,
    lang: str = APIPath(..., pattern=_LANG_REGEX),
    district: str = APIPath(..., pattern=_DISTRICT_SLUG_REGEX),
    page: int = Query(1, ge=1, le=1000),
    db: AsyncSession = Depends(get_seo_db),
) -> Response:
    if bounce := _twa_bounce_response(request):
        return bounce
    district_key = _normalize_district_key(district.replace("-", "_"))
    if district_key is None:
        return _render_gone(request, lang, reason="unknown_district")
    rows, total = await _query_filter_listings(
        db,
        deal=None,
        property_type=None,
        district_key=district_key,
        rooms=None,
        page=page,
    )
    return _render_filter_page(
        request,
        lang,
        {"district": district_key},
        page=page,
        listings=rows,
        total=total,
    )


# 3-param indexable: /{lang}/{deal}/{type}/{rooms}-rooms/{district}
@router.get("/{lang}/{deal}/{property_type}/{rooms_slug}/{district}")
async def filter_rooms_district(
    request: Request,
    lang: str = APIPath(..., pattern=_LANG_REGEX),
    deal: str = APIPath(..., pattern=_DEAL_REGEX),
    property_type: str = APIPath(..., pattern=_PROPERTY_REGEX),
    rooms_slug: str = APIPath(..., pattern=_ROOMS_SLUG_REGEX),
    district: str = APIPath(..., pattern=_DISTRICT_SLUG_REGEX),
    page: int = Query(1, ge=1, le=1000),
    db: AsyncSession = Depends(get_seo_db),
) -> Response:
    if bounce := _twa_bounce_response(request):
        return bounce
    m = re.match(r"^(\d+)-rooms$", rooms_slug)
    rooms = int(m.group(1)) if m else None
    district_key = _normalize_district_key(district.replace("-", "_"))
    if district_key is None or rooms is None:
        return _render_gone(request, lang, reason="malformed_filter")
    rows, total = await _query_filter_listings(
        db,
        deal=deal,
        property_type=property_type,
        district_key=district_key,
        rooms=rooms,
        page=page,
    )
    return _render_filter_page(
        request,
        lang,
        {
            "deal": deal,
            "property_type": property_type,
            "rooms": rooms,
            "district": district_key,
        },
        page=page,
        listings=rows,
        total=total,
    )


# 2-param: /{lang}/{deal}/{property_type}/{district}
@router.get("/{lang}/{deal}/{property_type}/{district}")
async def filter_district_combo(
    request: Request,
    lang: str = APIPath(..., pattern=_LANG_REGEX),
    deal: str = APIPath(..., pattern=_DEAL_REGEX),
    property_type: str = APIPath(..., pattern=_PROPERTY_REGEX),
    district: str = APIPath(..., pattern=_DISTRICT_SLUG_REGEX),
    page: int = Query(1, ge=1, le=1000),
    db: AsyncSession = Depends(get_seo_db),
) -> Response:
    if bounce := _twa_bounce_response(request):
        return bounce
    district_key = _normalize_district_key(district.replace("-", "_"))
    if district_key is None:
        return _render_gone(request, lang, reason="unknown_district")
    rows, total = await _query_filter_listings(
        db,
        deal=deal,
        property_type=property_type,
        district_key=district_key,
        rooms=None,
        page=page,
    )
    return _render_filter_page(
        request,
        lang,
        {"deal": deal, "property_type": property_type, "district": district_key},
        page=page,
        listings=rows,
        total=total,
    )


# 1-param-deal: /{lang}/{deal}/{property_type}
@router.get("/{lang}/{deal}/{property_type}")
async def filter_deal_type(
    request: Request,
    lang: str = APIPath(..., pattern=_LANG_REGEX),
    deal: str = APIPath(..., pattern=_DEAL_REGEX),
    property_type: str = APIPath(..., pattern=_PROPERTY_REGEX),
    page: int = Query(1, ge=1, le=1000),
    db: AsyncSession = Depends(get_seo_db),
) -> Response:
    if bounce := _twa_bounce_response(request):
        return bounce
    rows, total = await _query_filter_listings(
        db,
        deal=deal,
        property_type=property_type,
        district_key=None,
        rooms=None,
        page=page,
    )
    return _render_filter_page(
        request,
        lang,
        {"deal": deal, "property_type": property_type},
        page=page,
        listings=rows,
        total=total,
    )
