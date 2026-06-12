"""PR8 — Meilisearch search index management (ADDITIVE).

Prepares the `listings` Meilisearch index with the correct filterable and
sortable attributes, and mirrors Listing row changes into the index as an
optional side effect. Postgres remains the source of truth: the /listings
endpoint still runs its SQL filter via `_apply_filters`. This module only
keeps the search index in sync so a future PR can route reads through
Meilisearch without schema migration.

Safety contract:
    - Every public function is wrapped in try/except at the call site.
    - If Meilisearch is unreachable, misconfigured, or out of disk space,
      writes to Postgres still succeed. No user-visible degradation.
    - All failures are logged at WARNING (not ERROR) because the feature
      is optional for this PR.
"""

from __future__ import annotations

import logging
from typing import Iterable, List, Optional

from app.core.config import settings
from app.db.models import Listing, ListingStatus

logger = logging.getLogger(__name__)

# Name of the Meilisearch index that holds unified Listing documents.
INDEX_NAME = "listings"

# Filterable attributes — MUST mirror the columns referenced in
# `_apply_filters` (PR3) + facet aggregation (PR4). Adding a new filter in
# PR3 requires adding its column here too, otherwise Meilisearch will
# reject the query when search switches over to it in a later PR.
FILTERABLE_ATTRIBUTES: List[str] = [
    # Sprint 1/2 (PR3/PR4)
    "type",
    "property_type",
    "region",
    "district",
    "price",
    "rooms",
    "area",
    "land_area",
    "rent_period",
    "mortgage_ok",
    "installment_ok",
    "halol_ok",
    "amenities",
    "rent_payment",
    # Sprint 3 (T-001)
    "city",
    "microdistrict",
    "jk_name",
    "metro_station",
    "urgent_flag",
    # Sprint 4 (T-009)
    "commercial_type",
    "ceiling_height",
    "entrance",
    "parking_comm",
    "building_class",
    # Sprint 5 (T-006, T-008)
    "market_type",
    "wall_material",
    "furniture",
    # Sprint 6 (T-011, T-014, T-015)
    "garage",
    "basement",
    "buildings_exist",
    "fence",
    "land_shape",
    "balcony",
    "listing_subtype",
    # Sprint 7 (T-027)
    "jk_id",
    # Sprint 8 (T-023)
    "slug",
]

# Sortable attributes per spec. Keep small — Meilisearch builds an extra
# index per sortable attribute.
#
# FIX 3 — `boost_rank` mirrors the Postgres primary sort tier
# (`ORDER BY is_boosted DESC, ...`). By making it the leading sort key on
# the Meili path, promoted listings stay at the top across both engines.
SORTABLE_ATTRIBUTES: List[str] = [
    "boost_rank",
    "price",
    "created_at",
]

# Searchable (free-text) attributes. Left out of spec but declared for
# completeness — search will use these when query switches over.
SEARCHABLE_ATTRIBUTES: List[str] = [
    "title",
    "description",
    "district",
    "address",
    # Sprint 3 — landmark / jk_name / microdistrict become searchable
    "landmark",
    "jk_name",
    "microdistrict",
]


# ─────────────────────────────────────────────────────────────────────
# Client (lazy, process-singleton)
# ─────────────────────────────────────────────────────────────────────


_client = None  # populated on first successful connection


def _get_client():
    """Return a meilisearch.Client, or None if the library isn't
    installed / host isn't reachable. Intentionally silent on failure."""
    global _client
    if _client is not None:
        return _client
    try:
        import meilisearch  # type: ignore
    except ImportError:
        logger.warning("meilisearch package not installed; indexing disabled")
        return None
    try:
        _client = meilisearch.Client(
            settings.meilisearch_host,
            settings.meilisearch_api_key or None,
        )
        return _client
    except Exception as exc:
        logger.warning("Failed to init Meilisearch client: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────
# Index bootstrap
# ─────────────────────────────────────────────────────────────────────


def ensure_index_exists(index_name: str = INDEX_NAME):
    """Create `index_name` if it doesn't already exist. Returns the
    meilisearch.Index instance, or None on failure."""
    client = _get_client()
    if client is None:
        return None
    try:
        # Meilisearch 0.31 Python SDK: `create_index` is idempotent-ish —
        # raises on duplicate, so we guard explicitly.
        try:
            client.create_index(index_name, {"primaryKey": "id"})
        except Exception:
            # Already exists, that's fine.
            pass
        return client.index(index_name)
    except Exception as exc:
        logger.warning("ensure_index_exists(%s) failed: %s", index_name, exc)
        return None


def set_filterable_attributes(
    attrs: Iterable[str] = FILTERABLE_ATTRIBUTES,
    index_name: str = INDEX_NAME,
) -> bool:
    """Push the filterable-attribute list to Meilisearch. Returns True on
    success. Safe to call repeatedly — Meilisearch treats the call as
    idempotent."""
    index = ensure_index_exists(index_name)
    if index is None:
        return False
    try:
        index.update_filterable_attributes(list(attrs))
        return True
    except Exception as exc:
        logger.warning("set_filterable_attributes failed: %s", exc)
        return False


def set_sortable_attributes(
    attrs: Iterable[str] = SORTABLE_ATTRIBUTES,
    index_name: str = INDEX_NAME,
) -> bool:
    index = ensure_index_exists(index_name)
    if index is None:
        return False
    try:
        index.update_sortable_attributes(list(attrs))
        return True
    except Exception as exc:
        logger.warning("set_sortable_attributes failed: %s", exc)
        return False


def set_searchable_attributes(
    attrs: Iterable[str] = SEARCHABLE_ATTRIBUTES,
    index_name: str = INDEX_NAME,
) -> bool:
    index = ensure_index_exists(index_name)
    if index is None:
        return False
    try:
        index.update_searchable_attributes(list(attrs))
        return True
    except Exception as exc:
        logger.warning("set_searchable_attributes failed: %s", exc)
        return False


def init_meilisearch_index() -> bool:
    """One-shot bootstrap: create the index and push all three attribute
    lists. Call from app startup or from a management script. Returns
    True only if every step succeeded; logs + returns False otherwise."""
    if ensure_index_exists() is None:
        return False
    ok1 = set_filterable_attributes()
    ok2 = set_sortable_attributes()
    ok3 = set_searchable_attributes()
    return ok1 and ok2 and ok3


# ─────────────────────────────────────────────────────────────────────
# Document mapping
# ─────────────────────────────────────────────────────────────────────


def _enum_value(v) -> Optional[str]:
    """Unwrap SQLAlchemy enum objects to their declared NAME.

    Matches the Postgres storage convention used by `Enum(ListingType)`
    without values_callable — values land in PG in UPPER-CASE (e.g. `SELL`,
    `APARTMENT`, `ACTIVE`). The Meili document uses the same casing so
    filter predicates like `type = "SELL"` are consistent across engines.
    """
    if v is None:
        return None
    if hasattr(v, "name"):
        return v.name  # 'SELL', 'APARTMENT', …
    return v


def _primary_image(listing) -> Optional[str]:
    """Best display photo URL for the search document, mirroring the
    autopost card: prefer the ``is_primary`` image, else the lowest-
    position one, and within that image prefer a lighter resized variant
    (medium → large → original) so inline/result cards load fast.

    Defensive by design — if the ``images`` relationship isn't loaded
    (e.g. a per-write ``index_listing`` call without an eager load),
    return None instead of triggering an async lazy load that would
    raise. The periodic ``sync_to_meilisearch`` backfill eager-loads
    images, so the field is filled in there within one cycle.
    """
    try:
        images = list(getattr(listing, "images", None) or [])
    except Exception:
        return None
    if not images:
        return None
    chosen = next(
        (im for im in images if getattr(im, "is_primary", False)), images[0]
    )
    return (
        getattr(chosen, "medium_url", None)
        or getattr(chosen, "large_url", None)
        or getattr(chosen, "original_url", None)
    )


def _map_listing_to_document(listing: Listing) -> dict:
    """Flatten a Listing row into a Meilisearch document.

    Included fields (exactly what filter/search uses):
        - primary key (id)
        - type, property_type, status, moderation_status (enums UPPER-CASE)
        - free-text: title, description, district, address
        - scalar filters: rooms, area, land_area, floor, total_floors,
          price, currency, rent_period, deed_type, building_type,
          condition, is_furnished
        - boolean filters: mortgage_ok, installment_ok, halol_ok
        - array filters: amenities, rent_payment, nearby_amenities
        - geo + region: region, district, latitude, longitude
        - sortable: created_at (ISO string)

    Arrays stay arrays; None stays None. The document contract is keyed
    only to the PR3/PR4 filter surface — do NOT add columns that aren't
    queried, or the index will bloat without purpose.
    """
    return {
        "id": str(listing.id),
        # Enums — UPPER-CASE per PG storage
        "type": _enum_value(listing.type),
        "property_type": _enum_value(listing.property_type),
        "status": _enum_value(listing.status),
        "moderation_status": _enum_value(listing.moderation_status),
        "currency": _enum_value(listing.currency),
        # Free-text
        "title": listing.title,
        "description": listing.description,
        "district": listing.district,
        "address": listing.address,
        # Primary image for result cards (bot inline / search). May be None.
        "photo_url": _primary_image(listing),
        # Location
        "region": listing.region,
        "latitude": listing.latitude,
        "longitude": listing.longitude,
        # Scalar filters
        "rooms": listing.rooms,
        "area": listing.area,
        "land_area": listing.land_area,
        "floor": listing.floor,
        "total_floors": listing.total_floors,
        "price": listing.price,
        "rent_period": listing.rent_period,
        "deed_type": listing.deed_type,
        "building_type": listing.building_type,
        "condition": listing.condition,
        "is_furnished": listing.is_furnished,
        # Sale-finance booleans
        "mortgage_ok": bool(listing.mortgage_ok),
        "installment_ok": bool(listing.installment_ok),
        "halol_ok": bool(listing.halol_ok),
        # Array filters — None → [] for Meili compatibility
        "amenities": list(listing.amenities or []),
        "nearby_amenities": list(listing.nearby_amenities or []),
        "rent_payment": list(listing.rent_payment or []),
        # Sortable
        "created_at": (
            listing.created_at.isoformat() if listing.created_at is not None else None
        ),
        # FIX 3 — mirrors Postgres `ORDER BY is_boosted DESC` primary tier.
        # 1 for boosted rows, 0 otherwise; always the leading sort key on
        # the Meili read path.
        "boost_rank": 1 if getattr(listing, "is_boosted", False) else 0,
        # ── Sprint 3 (T-001) ────────────────────────────────────────
        "city": getattr(listing, "city", None),
        "microdistrict": getattr(listing, "microdistrict", None),
        "jk_name": getattr(listing, "jk_name", None),
        "landmark": getattr(listing, "landmark", None),
        "metro_station": getattr(listing, "metro_station", None),
        "urgent_flag": bool(getattr(listing, "urgent_flag", False)),
        # ── Sprint 4 (T-009) ────────────────────────────────────────
        "commercial_type": getattr(listing, "commercial_type", None),
        "price_per_sqm": getattr(listing, "price_per_sqm", None),
        "ceiling_height": getattr(listing, "ceiling_height", None),
        "entrance": getattr(listing, "entrance", None),
        "parking_comm": getattr(listing, "parking_comm", None),
        "building_class": getattr(listing, "building_class", None),
        # ── Sprint 5 (T-006, T-008) — both old and new during dual-read
        "market_type": getattr(listing, "market_type", None),
        "wall_material": getattr(listing, "wall_material", None),
        "furniture": getattr(listing, "furniture", None),
        # ── Sprint 6 (T-011, T-014, T-015) ──────────────────────────
        "garage": getattr(listing, "garage", None),
        "basement": getattr(listing, "basement", None),
        "buildings_exist": getattr(listing, "buildings_exist", None),
        "fence": getattr(listing, "fence", None),
        "land_shape": getattr(listing, "land_shape", None),
        "balcony": getattr(listing, "balcony", None),
        "listing_subtype": getattr(listing, "listing_subtype", None),
        "floor_plan_url": getattr(listing, "floor_plan_url", None),
        # ── Sprint 7 (T-027) ────────────────────────────────────────
        "jk_id": str(listing.jk_id) if getattr(listing, "jk_id", None) else None,
        # ── Sprint 8 (T-023) ────────────────────────────────────────
        "slug": getattr(listing, "slug", None),
    }


# ─────────────────────────────────────────────────────────────────────
# Crawled listings (Telegram / OLX) — index into the SAME index so bot
# search returns the full aggregated inventory, like the app's feed.
# ─────────────────────────────────────────────────────────────────────

# Crawled listing_type / property_type → platform taxonomy. Mirrors
# api.v1.listings._normalize_* but kept local: importing the API layer
# here would create a circular import (listings.py imports this module).
_CRAWLER_TYPE_MAP = {"sale": "sell", "daily_rent": "rent", "rent": "rent", "sell": "sell"}
_CRAWLER_PROPERTY_TYPE_MAP = {"office": "commercial"}


def _crawler_photo_url(images) -> Optional[str]:
    """First usable image URL from a crawled listing's JSONB ``images``.

    Crawled rows store ``images`` as a list of absolute URL strings (see
    the unified feed builder in api.v1.listings). Returns the first
    string, or None.
    """
    if isinstance(images, list):
        for img in images:
            if isinstance(img, str) and img:
                return img
    return None


def _map_crawled_to_document(row, source: str) -> dict:
    """Map a TelegramListing / OLXListing row into the shared Meili doc
    schema, so bot search returns crawled inventory next to native rows.

    Only the fields the bot card + filters need are populated. NOTE the
    deliberate omission of ``status`` / ``moderation_status``: the app's
    native Meili query requires ``status = "ACTIVE" AND moderation_status
    = "APPROVED"``, so crawled rows (lacking those) never leak into the
    app's native results — only the bot's status-agnostic query sees them.
    The doc ``id`` is the crawled row's own UUID, which ``GET
    /listings/resolve/{id}`` already resolves, so ``build_listing_link``
    deep-links work unchanged.
    """
    from app.services.query_parser import canonical_district

    lt = (getattr(row, "listing_type", None) or "").lower()
    pt = (getattr(row, "property_type", None) or "").lower()
    price = getattr(row, "price", None)
    created = getattr(row, "created_at", None)
    raw_district = getattr(row, "district", None)
    return {
        "id": str(row.id),
        "source": source,
        "type": _CRAWLER_TYPE_MAP.get(lt, lt) or None,
        "property_type": _CRAWLER_PROPERTY_TYPE_MAP.get(pt, pt) or None,
        # Normalize to the canonical key so the bot's district filter
        # (same parser) matches; fall back to the raw value if unknown.
        "district": canonical_district(raw_district) or raw_district,
        "region": getattr(row, "region", None),
        "address": getattr(row, "address", None),
        "description": getattr(row, "description", None),
        "rooms": getattr(row, "rooms", None),
        "area": getattr(row, "area_sqm", None),
        "price": int(price) if price is not None else None,
        "currency": getattr(row, "currency", None),
        "photo_url": _crawler_photo_url(getattr(row, "images", None)),
        # Crawled rows are never boosted; keep the sort key present so the
        # bot's created_at sort behaves the same as for native docs.
        "boost_rank": 0,
        "created_at": created.isoformat() if created is not None else None,
    }


# ─────────────────────────────────────────────────────────────────────
# Sync helpers (safe — all failures swallowed)
# ─────────────────────────────────────────────────────────────────────


def index_listing(listing: Listing) -> bool:
    """Upsert a single listing document into Meilisearch. Returns True on
    success, False on any error. Never raises — Postgres writes must
    still succeed if Meili is down.

    Block F F1 — DRAFT listings are skipped explicitly: they are never
    B2C-visible and should not occupy index space. PATCH on a DRAFT
    therefore does not introduce a temporary index entry.
    """
    if getattr(listing, "status", None) == ListingStatus.DRAFT:
        return False
    index = ensure_index_exists()
    if index is None:
        _BACKFILL_COUNTERS["meili_index_failure_total"] += 1
        return False
    try:
        doc = _map_listing_to_document(listing)
        index.add_documents([doc], primary_key="id")
        _BACKFILL_COUNTERS["meili_index_success_total"] += 1
        return True
    except Exception as exc:
        logger.warning(
            "index_listing(%s) failed: %s", getattr(listing, "id", None), exc
        )
        _BACKFILL_COUNTERS["meili_index_failure_total"] += 1
        return False


def delete_listing(listing_id) -> bool:
    """Remove a document from the index. Returns True on success. Never
    raises."""
    index = ensure_index_exists()
    if index is None:
        _BACKFILL_COUNTERS["meili_delete_failure_total"] += 1
        return False
    try:
        index.delete_document(str(listing_id))
        _BACKFILL_COUNTERS["meili_delete_success_total"] += 1
        return True
    except Exception as exc:
        logger.warning("delete_listing(%s) failed: %s", listing_id, exc)
        _BACKFILL_COUNTERS["meili_delete_failure_total"] += 1
        return False


# ─────────────────────────────────────────────────────────────────────
# PR9 — Backfill (additive; safe-fallback; never raises)
# ─────────────────────────────────────────────────────────────────────

# Lightweight in-process counters. A future PR can swap these for a
# Prometheus collector without changing call sites. Read via
# `get_backfill_counters()`; reset via `reset_backfill_counters()` (test
# helper).
#
# FIX 4 — also cover the per-write `index_listing` / `delete_listing`
# paths so ops can watch drift accumulate even when the backfill job
# isn't running.
_BACKFILL_COUNTERS: dict = {
    "meili_backfill_success_total": 0,
    "meili_backfill_failure_total": 0,
    "meili_index_success_total": 0,
    "meili_index_failure_total": 0,
    "meili_delete_success_total": 0,
    "meili_delete_failure_total": 0,
}


def get_backfill_counters() -> dict:
    """Snapshot of all in-process Meili counters. Safe to call any time."""
    return dict(_BACKFILL_COUNTERS)


def reset_backfill_counters() -> None:
    """Test helper. Not called from production code."""
    for k in _BACKFILL_COUNTERS:
        _BACKFILL_COUNTERS[k] = 0


def _index_batch(index, listings) -> bool:
    """Bulk-upsert one batch via `add_documents`. Returns True on success,
    False on any failure. NEVER raises."""
    if not listings:
        return True
    try:
        docs = [_map_listing_to_document(listing) for listing in listings]
        index.add_documents(docs, primary_key="id")
        return True
    except Exception as exc:
        logger.warning("backfill batch failed (size=%d): %s", len(listings), exc)
        return False


async def backfill_all_listings(
    db_session,
    batch_size: int = 1000,
) -> dict:
    """Stream every ACTIVE non-deleted listing into Meilisearch in batches.

    Idempotent: Meili upserts by primary key, so re-running this is safe
    and will overwrite stale documents. Pagination uses `WHERE id > last_id
    ORDER BY id LIMIT batch_size` so the full table never lives in memory.

    Per-batch retry policy: on failure, retry ONCE. Logs at WARNING.
    Never raises — Postgres remains source of truth.

    Returns:
        {"indexed_count": int, "failed_count": int}
    """
    # Local imports keep this module importable even when SQLAlchemy or the
    # ORM model graph aren't loaded (e.g. CLI smoke tests / docs build).
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.db.models import Listing, ListingStatus

    indexed = 0
    failed = 0

    # Bail out cleanly if Meili is unreachable / misconfigured. Caller can
    # inspect the zeros in the return dict.
    index = ensure_index_exists()
    if index is None:
        logger.warning("Meilisearch unavailable; backfill aborted")
        return {"indexed_count": 0, "failed_count": 0}

    last_id = None
    while True:
        q = (
            select(Listing)
            # Eager-load images so _primary_image() can read the photo URL
            # without an async lazy load (which would raise mid-mapping).
            .options(selectinload(Listing.images))
            .where(
                Listing.status == ListingStatus.ACTIVE,
                Listing.deleted_at.is_(None),
            )
            .order_by(Listing.id)
            .limit(batch_size)
        )
        if last_id is not None:
            q = q.where(Listing.id > last_id)

        try:
            rows = (await db_session.execute(q)).scalars().all()
        except Exception as exc:
            # Hard DB failure — log and stop. We don't want an infinite
            # loop of failing queries.
            logger.warning("backfill DB read failed: %s", exc)
            break

        if not rows:
            break

        ok = _index_batch(index, rows)
        if not ok:
            # One retry per batch.
            ok = _index_batch(index, rows)

        n = len(rows)
        if ok:
            indexed += n
            _BACKFILL_COUNTERS["meili_backfill_success_total"] += n
        else:
            failed += n
            _BACKFILL_COUNTERS["meili_backfill_failure_total"] += n

        last_id = rows[-1].id

        # Defensive: if the batch was smaller than batch_size, we've
        # reached the end of the dataset.
        if n < batch_size:
            break

    logger.info("backfill complete: indexed=%d failed=%d", indexed, failed)
    return {"indexed_count": indexed, "failed_count": failed}


async def backfill_crawled_listings(
    db_session,
    batch_size: int = 1000,
) -> dict:
    """Stream visible crawled listings (Telegram + OLX) into the index.

    Mirrors the app's mixed feed visibility: skips claimed rows
    (``converted_listing_id`` set — the native Listing is indexed
    separately) and, for Telegram, seller-rejected rows. Idempotent
    (upsert by id); never raises — Postgres stays source of truth.

    Returns ``{"indexed_count": int, "failed_count": int}``.
    """
    from sqlalchemy import select

    from app.db.models import OLXListing, TelegramListing

    index = ensure_index_exists()
    if index is None:
        logger.warning("Meilisearch unavailable; crawled backfill aborted")
        return {"indexed_count": 0, "failed_count": 0}

    indexed = 0
    failed = 0
    # (source label, model, visibility conditions)
    sources = (
        (
            "telegram",
            TelegramListing,
            (
                TelegramListing.converted_listing_id.is_(None),
                TelegramListing.rejected_at.is_(None),
            ),
        ),
        (
            "olx",
            OLXListing,
            (OLXListing.converted_listing_id.is_(None),),
        ),
    )

    for source, model, conds in sources:
        last_id = None
        while True:
            q = select(model).where(*conds).order_by(model.id).limit(batch_size)
            if last_id is not None:
                q = q.where(model.id > last_id)
            try:
                rows = (await db_session.execute(q)).scalars().all()
            except Exception as exc:
                logger.warning("crawled backfill DB read failed (%s): %s", source, exc)
                break
            if not rows:
                break
            try:
                docs = [_map_crawled_to_document(r, source) for r in rows]
                index.add_documents(docs, primary_key="id")
                indexed += len(rows)
            except Exception as exc:
                logger.warning(
                    "crawled backfill batch failed (%s, size=%d): %s",
                    source,
                    len(rows),
                    exc,
                )
                failed += len(rows)
            last_id = rows[-1].id
            if len(rows) < batch_size:
                break

    logger.info("crawled backfill complete: indexed=%d failed=%d", indexed, failed)
    return {"indexed_count": indexed, "failed_count": failed}


# ─────────────────────────────────────────────────────────────────────
# PR10 — Meilisearch read-path query mapper
# ─────────────────────────────────────────────────────────────────────
#
# Converts a ListingFilters object (same model used by the Postgres
# `_apply_filters`) into a Meilisearch filter expression, preserving the
# applicability matrix rule. Any function in this block MAY raise — the
# router layer catches exceptions and falls back to Postgres.
#
# Enum values in the index are UPPER-CASE (see _enum_value), matching the
# Postgres storage of ListingType / PropertyType / ListingStatus /
# ModerationStatus.


def _meili_quote(value) -> str:
    """Quote a Python value for a Meilisearch filter RHS."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    # Strings — escape embedded quotes. Meili filter syntax uses " ".
    s = str(value).replace('"', '\\"')
    return f'"{s}"'


def _filters_to_meili_expression(filters) -> str:
    """Build a Meilisearch `filter` string from a ListingFilters object.

    Imports are local to keep this module import-light (Meili client is
    optional) and because ListingFilters is a Pydantic model from the
    schemas package.

    Respects the silent-drop rule: filters whose underlying column isn't
    visible for the caller's (property_type, type) combo are skipped.

    Always-included: status='ACTIVE' AND moderation_status='APPROVED'
    (matches the Postgres base-query WHERE clause).
    """
    # Local import: keeps startup independent of the schemas module.
    from app.api.v1.listings import _filter_is_applicable

    pt = filters.property_type
    dt = filters.type

    # FIX 5 — removed `deleted_at IS NULL`. The attribute isn't in the
    # indexed document (see _map_listing_to_document), so the clause's
    # behavior relied on Meilisearch's undefined "missing attribute ~=
    # null" semantics. Correctness is preserved by the write hooks:
    # soft-deletes call `delete_listing()`, so deleted rows never live
    # in the index in the first place.
    clauses: list = [
        'status = "ACTIVE"',
        'moderation_status = "APPROVED"',
    ]

    # Always-applicable fields
    if filters.type:
        clauses.append(f"type = {_meili_quote(filters.type.upper())}")
    if filters.property_type:
        clauses.append(f"property_type = {_meili_quote(filters.property_type.upper())}")
    if filters.region:
        opts = " OR ".join(f"region = {_meili_quote(r)}" for r in filters.region)
        clauses.append(f"({opts})")
    if filters.district:
        opts = " OR ".join(f"district = {_meili_quote(d)}" for d in filters.district)
        clauses.append(f"({opts})")
    if filters.price_min is not None:
        clauses.append(f"price >= {int(filters.price_min)}")
    if filters.price_max is not None:
        clauses.append(f"price <= {int(filters.price_max)}")

    # Matrix-gated fields — mirror the Postgres path clause-for-clause
    if filters.rooms and _filter_is_applicable("rooms", pt, dt):
        opts = " OR ".join(f"rooms = {int(r)}" for r in filters.rooms)
        clauses.append(f"({opts})")
    if filters.area_min is not None and _filter_is_applicable("area_min", pt, dt):
        clauses.append(f"area >= {float(filters.area_min)}")
    if filters.area_max is not None and _filter_is_applicable("area_max", pt, dt):
        clauses.append(f"area <= {float(filters.area_max)}")
    if filters.floor_min is not None and _filter_is_applicable("floor_min", pt, dt):
        clauses.append(f"floor >= {int(filters.floor_min)}")
    if filters.floor_max is not None and _filter_is_applicable("floor_max", pt, dt):
        clauses.append(f"floor <= {int(filters.floor_max)}")
    if filters.land_area_min is not None and _filter_is_applicable(
        "land_area_min", pt, dt
    ):
        clauses.append(f"land_area >= {float(filters.land_area_min)}")
    if filters.land_area_max is not None and _filter_is_applicable(
        "land_area_max", pt, dt
    ):
        clauses.append(f"land_area <= {float(filters.land_area_max)}")

    # amenities / nearby_amenities — AND-match (Meili semantics: "col =
    # val" on an array column matches when the array contains val, so we
    # AND the per-element clauses)
    if filters.amenities and _filter_is_applicable("amenities", pt, dt):
        for a in filters.amenities:
            clauses.append(f"amenities = {_meili_quote(a)}")
    if filters.nearby_amenities and _filter_is_applicable("nearby_amenities", pt, dt):
        for a in filters.nearby_amenities:
            clauses.append(f"nearby_amenities = {_meili_quote(a)}")

    # Rent group
    if filters.rent_period and _filter_is_applicable("rent_period", pt, dt):
        clauses.append(f"rent_period = {_meili_quote(filters.rent_period)}")
    # rent_payment — OR-match (intersection)
    if filters.rent_payment and _filter_is_applicable("rent_payment", pt, dt):
        opts = " OR ".join(
            f"rent_payment = {_meili_quote(p)}" for p in filters.rent_payment
        )
        clauses.append(f"({opts})")

    # Sale finance — True-only per PR3 contract
    if filters.mortgage_ok and _filter_is_applicable("mortgage_ok", pt, dt):
        clauses.append("mortgage_ok = true")
    if filters.installment_ok and _filter_is_applicable("installment_ok", pt, dt):
        clauses.append("installment_ok = true")
    if filters.halol_ok and _filter_is_applicable("halol_ok", pt, dt):
        clauses.append("halol_ok = true")
    if filters.deed_type and _filter_is_applicable("deed_type", pt, dt):
        clauses.append(f"deed_type = {_meili_quote(filters.deed_type)}")

    # ── Sprint 3 (T-001) — location filters ──────────────────────────
    # Mirror _apply_filters: city / microdistrict / urgent_flag / jk_id are
    # always-applicable; jk_name and metro_station are matrix-gated.
    if getattr(filters, "urgent_flag", None):
        clauses.append("urgent_flag = true")
    if getattr(filters, "city", None):
        clauses.append(f"city = {_meili_quote(filters.city)}")
    if getattr(filters, "microdistrict", None):
        clauses.append(f"microdistrict = {_meili_quote(filters.microdistrict)}")
    if getattr(filters, "jk_name", None) and _filter_is_applicable("jk_name", pt, dt):
        clauses.append(f"jk_name = {_meili_quote(filters.jk_name)}")
    if getattr(filters, "metro_station", None) and _filter_is_applicable(
        "metro_station", pt, dt
    ):
        clauses.append(f"metro_station = {_meili_quote(filters.metro_station)}")

    # ── Sprint 4 (T-009) — commercial filters ────────────────────────
    if getattr(filters, "commercial_type", None) and _filter_is_applicable(
        "commercial_type", pt, dt
    ):
        clauses.append(f"commercial_type = {_meili_quote(filters.commercial_type)}")
    if getattr(filters, "building_class", None) and _filter_is_applicable(
        "building_class", pt, dt
    ):
        clauses.append(f"building_class = {_meili_quote(filters.building_class)}")
    if getattr(filters, "entrance", None) and _filter_is_applicable("entrance", pt, dt):
        clauses.append(f"entrance = {_meili_quote(filters.entrance)}")
    if getattr(filters, "parking_comm", None) is not None and _filter_is_applicable(
        "parking_comm", pt, dt
    ):
        clauses.append(f"parking_comm = {_meili_quote(bool(filters.parking_comm))}")
    if getattr(
        filters, "ceiling_height_min", None
    ) is not None and _filter_is_applicable("ceiling_height_min", pt, dt):
        clauses.append(f"ceiling_height >= {float(filters.ceiling_height_min)}")
    if getattr(
        filters, "ceiling_height_max", None
    ) is not None and _filter_is_applicable("ceiling_height_max", pt, dt):
        clauses.append(f"ceiling_height <= {float(filters.ceiling_height_max)}")
    if getattr(
        filters, "price_per_sqm_min", None
    ) is not None and _filter_is_applicable("price_per_sqm_min", pt, dt):
        clauses.append(f"price_per_sqm >= {int(filters.price_per_sqm_min)}")
    if getattr(
        filters, "price_per_sqm_max", None
    ) is not None and _filter_is_applicable("price_per_sqm_max", pt, dt):
        clauses.append(f"price_per_sqm <= {int(filters.price_per_sqm_max)}")

    # ── Sprint 5 (T-006, T-008) — dual-read columns ──────────────────
    if getattr(filters, "market_type", None) and _filter_is_applicable(
        "market_type", pt, dt
    ):
        clauses.append(f"market_type = {_meili_quote(filters.market_type)}")
    if getattr(filters, "wall_material", None) and _filter_is_applicable(
        "wall_material", pt, dt
    ):
        clauses.append(f"wall_material = {_meili_quote(filters.wall_material)}")
    if getattr(filters, "furniture", None) and _filter_is_applicable(
        "furniture", pt, dt
    ):
        clauses.append(f"furniture = {_meili_quote(filters.furniture)}")

    # ── Sprint 6 (T-011, T-014, T-015) — property polish ─────────────
    if getattr(filters, "garage", None) is not None and _filter_is_applicable(
        "garage", pt, dt
    ):
        clauses.append(f"garage = {_meili_quote(bool(filters.garage))}")
    if getattr(filters, "basement", None) is not None and _filter_is_applicable(
        "basement", pt, dt
    ):
        clauses.append(f"basement = {_meili_quote(bool(filters.basement))}")
    if getattr(filters, "buildings_exist", None) is not None and _filter_is_applicable(
        "buildings_exist", pt, dt
    ):
        clauses.append(
            f"buildings_exist = {_meili_quote(bool(filters.buildings_exist))}"
        )
    if getattr(filters, "fence", None) is not None and _filter_is_applicable(
        "fence", pt, dt
    ):
        clauses.append(f"fence = {_meili_quote(bool(filters.fence))}")
    if getattr(filters, "land_shape", None) and _filter_is_applicable(
        "land_shape", pt, dt
    ):
        clauses.append(f"land_shape = {_meili_quote(filters.land_shape)}")
    if getattr(filters, "balcony", None) and _filter_is_applicable("balcony", pt, dt):
        clauses.append(f"balcony = {_meili_quote(filters.balcony)}")
    if getattr(filters, "listing_subtype", None) and _filter_is_applicable(
        "listing_subtype", pt, dt
    ):
        clauses.append(f"listing_subtype = {_meili_quote(filters.listing_subtype)}")

    # ── Sprint 7 (T-027) — jk_id (always-applicable) ─────────────────
    if getattr(filters, "jk_id", None):
        clauses.append(f"jk_id = {_meili_quote(str(filters.jk_id))}")

    return " AND ".join(clauses)


def _filters_to_meili_sort(filters) -> list:
    """Map ListingFilters sort_by/sort_order to Meilisearch sort syntax.

    FIX 3 — Always prepend `boost_rank:desc` so promoted listings
    surface first, mirroring the Postgres `ORDER BY is_boosted DESC, …`
    primary tier. The secondary tier is the caller-supplied sort_by;
    unknown keys degrade to `created_at:desc`.

    Meili requires the attribute to be in `sortable_attributes` (set in
    search_index.init / SORTABLE_ATTRIBUTES).
    """
    key = filters.sort_by or "created_at"
    order = filters.sort_order if filters.sort_order in ("asc", "desc") else "desc"
    secondary = f"{key}:{order}" if key in SORTABLE_ATTRIBUTES else "created_at:desc"
    # boost_rank is always the leading tier; collapse duplicate when the
    # caller also asks to sort by boost_rank directly.
    if secondary == "boost_rank:desc":
        return [secondary]
    return ["boost_rank:desc", secondary]


def search_listings_in_meili(filters, page: int, per_page: int) -> tuple[list, int]:
    """Run the listings filter against Meilisearch. Returns (ids, total).

    Raises on any failure — the router catches and falls back to
    Postgres. This is intentional: we never want a silent partial result
    set to leak to the buyer.
    """
    index = ensure_index_exists()
    if index is None:
        raise RuntimeError("Meilisearch client unavailable")
    expr = _filters_to_meili_expression(filters)
    sort = _filters_to_meili_sort(filters)
    offset = max(0, (page - 1) * per_page)
    resp = index.search(
        "" if not filters.q else filters.q,
        {
            "filter": expr,
            "sort": sort,
            "offset": offset,
            "limit": per_page,
            "attributesToRetrieve": ["id"],
        },
    )
    hits = resp.get("hits", []) if isinstance(resp, dict) else []
    total = resp.get("estimatedTotalHits") if isinstance(resp, dict) else None
    total = int(total or 0)
    ids = [h.get("id") for h in hits if isinstance(h, dict) and h.get("id")]
    return ids, total


def search_facets_in_meili(filters) -> dict:
    """Compute facet distributions via Meili's `facets` search option.

    Returns a dict in the same shape `_compute_facets` produces:
        {<response_key>: [{"value": v, "count": n}, ...], ...}

    Non-applicable facets are OMITTED (matches PR4 contract). Raises on
    any problem — router falls back to Postgres.
    """
    from app.api.v1.listings import _FACET_SPECS, _filter_is_applicable

    index = ensure_index_exists()
    if index is None:
        raise RuntimeError("Meilisearch client unavailable")

    # Only ask for facets whose underlying filter is applicable; this
    # preserves PR4's "omit non-applicable" rule and saves Meili work.
    pt = filters.property_type
    dt = filters.type
    applicable_response_keys: list = []
    applicable_meili_keys: list = []
    # Map from response_key -> (meili column, style, accessor)
    key_meta = {}
    for response_key, filter_key, column_name, style, accessor in _FACET_SPECS:
        if not _filter_is_applicable(filter_key, pt, dt):
            continue
        applicable_response_keys.append(response_key)
        applicable_meili_keys.append(column_name)
        key_meta[response_key] = (column_name, style, accessor)

    if not applicable_meili_keys:
        return {}

    expr = _filters_to_meili_expression(filters)
    resp = index.search(
        "" if not filters.q else filters.q,
        {
            "filter": expr,
            "facets": applicable_meili_keys,
            "limit": 0,  # don't return hits, only distribution
            "attributesToRetrieve": [],
        },
    )
    distribution: dict = {}
    if isinstance(resp, dict):
        distribution = resp.get("facetDistribution") or {}

    # FIX 2 — enum column names where the indexed document stores UPPER-
    # CASE labels (per _enum_value → enum.name), but the Postgres facet
    # path emits the enum's `.value` which happens to be lower-case. To
    # keep /listings/facets byte-identical across backends, we lower-case
    # the value for these specific columns. Non-enum string facets (like
    # region, district) are pass-through — the PG path also emits them
    # verbatim.
    _LOWERCASE_VALUE_COLUMNS = {"type", "property_type"}

    result: dict = {}
    for response_key in applicable_response_keys:
        column_name, style, accessor = key_meta[response_key]
        raw_bucket = distribution.get(column_name) or {}
        buckets: list = []
        for value, count in raw_bucket.items():
            if count <= 0 or value is None or value == "":
                continue
            if style == "scalar_int":
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    continue
            elif style == "boolean_true":
                # Meili returns 'true'/'false' for boolean facets; we only
                # want the true-bucket to mirror the PG contract.
                if str(value).lower() != "true":
                    continue
                value = True
            else:
                # scalar_enum / array — lowercase only where the indexed
                # label is upper-case by convention (PG enum names).
                if column_name in _LOWERCASE_VALUE_COLUMNS and isinstance(value, str):
                    value = value.lower()
            buckets.append({"value": value, "count": int(count)})
        if buckets:
            result[response_key] = buckets
    return result
