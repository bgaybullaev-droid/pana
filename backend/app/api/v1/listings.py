"""Listings API endpoints."""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Literal, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import case, delete, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import (
    get_current_seller,
    get_current_user,
    get_current_user_optional,
)
from app.core.exceptions import BadRequestException, NotFoundException
from app.db.database import get_db
from app.db.models import (
    AuditLog,
    Favorite,
    Listing,
    ListingImage,
    ListingSale,
    ListingStatus,
    ModerationStatus,
    OLXListing,
    Seller,
    TelegramListing,
    User,
    UserPreferences,
)
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.schemas.common import PaginatedResponse, text_snippet
from app.schemas.listing import (
    DraftPreviewResponse,
    FacetBucket,
    FacetsResponse,
    ListingCreate,
    ListingFilters,
    ListingImageResponse,
    ListingListResponse,
    ListingResponse,
    ListingUpdate,
    RegenerateRequest,
    RegenerateResponse,
    SourceTextResponse,
)
from app.schemas.unified import (
    UnifiedListingImage,
    UnifiedListingListItem,
    UnifiedListingResponse,
)
from app.services.crawler_service import (
    convert_olx_to_listing,
    convert_telegram_to_listing,
)
from app.services.listing_quota import check_can_create_listing
from app.services.listing_views import is_self_view

logger = logging.getLogger(__name__)

router = APIRouter()


def get_content_language(request: Request) -> str:
    """Extract content language from Accept-Language header (ru or uz)."""
    header = request.headers.get("accept-language", "ru")
    lang = header[:2].lower()
    return lang if lang in ("ru", "uz") else "ru"


def _dispatch_autopost_for_status_change(
    seller: "Seller",
    listing: "Listing",
    old_status: Optional["ListingStatus"],
) -> None:
    """Enqueue the right autopost Celery task for a listing-status change.

    Block D D4. Pure dispatch — runs after the listing transaction has
    already committed so a task-enqueue failure can never roll back the
    seller's update. Bails silently if the seller hasn't connected a
    channel.
    """
    if not seller or not getattr(seller, "autopost_channel_id", None):
        return
    if not getattr(seller, "autopost_enabled", False):
        return
    if seller.autopost_verified_at is None:
        return

    new_status = listing.status
    # Only relevant transitions: into / out of ACTIVE, or into SOLD.
    if old_status == new_status:
        return

    try:
        from app.workers.tasks.autopost import (
            delete_channel_post,
            mark_channel_post_sold,
            publish_listing_to_channel,
        )

        if new_status == ListingStatus.ACTIVE:
            publish_listing_to_channel.delay(str(listing.id), str(seller.id))
            return
        if new_status == ListingStatus.SOLD:
            mark_channel_post_sold.delay(str(listing.id))
            return
        if new_status in (
            ListingStatus.PAUSED,
            ListingStatus.DELETED,
            ListingStatus.EXPIRED,
        ):
            delete_channel_post.delay(str(listing.id))
    except Exception:
        # Task-broker hiccups must not break the API request.
        logger.warning(
            "autopost dispatch failed listing=%s status=%s -> %s",
            listing.id,
            old_status,
            new_status,
            exc_info=True,
        )


def _resolve_field(listing, field: str, lang: str) -> Optional[str]:
    """Resolve a text field to the requested language with fallback."""
    localized = getattr(listing, f"{field}_{lang}", None)
    return localized or getattr(listing, field, None)


def _is_translated(listing, lang: str) -> bool:
    """Check if listing content is served in a translated language."""
    orig = getattr(listing, "original_language", None) or "ru"
    return orig != lang and getattr(listing, "translation_status", None) == "completed"


# Uzbek-specific Cyrillic characters (not present in Russian)
_UZ_CYRILLIC = set("ҳғқўҲҒҚЎ")


def _detect_language(text: str) -> str:
    """Detect language from text using character-set heuristic."""
    if not text:
        return "ru"
    cyrillic = len(re.findall(r"[\u0400-\u04FF]", text))
    latin = len(re.findall(r"[a-zA-Z]", text))
    total = cyrillic + latin
    if total == 0:
        return "ru"
    if cyrillic > 0 and any(ch in _UZ_CYRILLIC for ch in text):
        return "uz"
    if cyrillic / total > 0.5:
        return "ru"
    return "uz"


def _populate_listing_lang_columns(listing: Listing) -> None:
    """Detect language from content and populate the corresponding _lang columns."""
    text = listing.description or listing.title or listing.address or ""
    lang = _detect_language(text)
    listing.original_language = lang
    if listing.description:
        setattr(listing, f"description_{lang}", listing.description)
    if listing.title:
        setattr(listing, f"title_{lang}", listing.title)
    if listing.address:
        setattr(listing, f"address_{lang}", listing.address)
    listing.translation_status = "pending"
    listing.translated_at = None


# ── State transition engine (T-024) ──
#
# Visibility matrix — MUST match frontend/.../listing-form/lib/visibility.ts.
# Keys are (property_type, deal_type) tuples. Values are the set of field
# names visible in that combo. Fields not in the set are "incompatible" and
# will be cleared to their canonical empty value by _clear_incompatible_fields.

# Fields that only make sense for sale listings (rule P2 wipes these on type=rent).
_SALE_ONLY_FIELDS = frozenset(
    {
        "mortgage_ok",
        "installment_ok",
        "halol_ok",
        "deed_type",
    }
)

# Fields that only make sense for rent listings (rule P2 wipes these on type=sell).
_RENT_ONLY_FIELDS = frozenset(
    {
        "rent_period",
        "deposit",
        "utilities_incl",
        "min_rent_months",
        "allowed_students",
        "allowed_pets",
        "rent_payment",
    }
)

# Property-type allowlists before the sell/rent split — end-state per
# blueprint §2.1 (Sprints 3–6 added). MUST stay in lockstep with
# frontend/.../visibility.ts (test_matrix_parity.py guards this).
_APARTMENT_BASE_FIELDS = frozenset(
    {
        "rooms",
        "area",
        "living_area",
        "kitchen_area",
        "floor",
        "total_floors",
        "ceiling_height",  # optional, all types except land
        "building_type",  # S5: kept during dual-read
        "market_type",  # S5
        "wall_material",  # S5
        "condition",
        "is_furnished",  # S5: kept during dual-read
        "furniture",  # S5
        "amenities",
        "nearby_amenities",
        "jk_name",  # S3
        "metro_station",  # S3 (sub-gated by region in P5)
        "balcony",  # S6
        "listing_subtype",  # S6
        "floor_plan_url",  # S6
    }
)
_HOUSE_BASE_FIELDS = frozenset(
    {
        "rooms",
        "area",
        "living_area",
        "land_area",
        "total_floors",
        "ceiling_height",  # optional, all types except land
        "house_type",
        "house_condition",
        "location_type",
        "water_supply",
        "electricity",
        "heating",
        "gas_supply",
        "sewage",
        "is_furnished",  # S5: dual-read
        "furniture",  # S5
        "wall_material",  # S5
        "amenities",
        "nearby_amenities",
        "garage",  # S6
        "basement",  # S6
    }
)
_COMMERCIAL_BASE_FIELDS = frozenset(
    {
        "area",
        "floor",
        "total_floors",
        "condition",
        "is_furnished",  # S5: dual-read
        "furniture",  # S5
        "nearby_amenities",
        "metro_station",  # S3
        "commercial_type",  # S4
        "ceiling_height",  # S4
        "entrance",  # S4
        "parking_comm",  # S4
        "building_class",  # S4
    }
)
_LAND_BASE_FIELDS = frozenset(
    {
        "land_area",
        "land_purpose",
        "buildings_exist",  # S6
        "fence",  # S6
        "land_shape",  # S6
    }
)

# Final matrix: base fields ∪ sale-or-rent group for each combo.
_VISIBILITY_MATRIX: dict = {
    ("apartment", "sell"): _APARTMENT_BASE_FIELDS | _SALE_ONLY_FIELDS,
    ("apartment", "rent"): _APARTMENT_BASE_FIELDS | _RENT_ONLY_FIELDS,
    ("house", "sell"): _HOUSE_BASE_FIELDS | _SALE_ONLY_FIELDS,
    ("house", "rent"): _HOUSE_BASE_FIELDS | _RENT_ONLY_FIELDS,
    ("commercial", "sell"): _COMMERCIAL_BASE_FIELDS | _SALE_ONLY_FIELDS,
    ("commercial", "rent"): _COMMERCIAL_BASE_FIELDS | _RENT_ONLY_FIELDS,
    ("land", "sell"): _LAND_BASE_FIELDS | _SALE_ONLY_FIELDS,
    ("land", "rent"): _LAND_BASE_FIELDS | _RENT_ONLY_FIELDS,
}

# Canonical empty value per clearable field.
#   Scalars (int, float, str, Optional[bool]) -> None
#   Arrays -> None (NULL in Postgres; Pydantic response serializes as null)
#   Non-null sale-finance booleans (mortgage_ok, installment_ok, halol_ok)
#     -> False because the DB column is NOT NULL with default false.
_CLEARING_VALUES: dict = {
    # Property details
    "rooms": None,
    "area": None,
    "living_area": None,
    "kitchen_area": None,
    "land_area": None,
    "floor": None,
    "total_floors": None,
    "building_type": None,
    "condition": None,
    "house_type": None,
    "house_condition": None,
    "location_type": None,
    "water_supply": None,
    "electricity": None,
    "heating": None,
    "gas_supply": None,
    "sewage": None,
    "is_furnished": None,
    "land_purpose": None,
    "amenities": None,
    "nearby_amenities": None,
    # Sprint 2 — rent group
    "rent_period": None,
    "deposit": None,
    "utilities_incl": None,
    "min_rent_months": None,
    "allowed_students": None,
    "allowed_pets": None,
    "rent_payment": None,
    # Sprint 2 — sale finance + deed
    "mortgage_ok": False,
    "installment_ok": False,
    "halol_ok": False,
    "deed_type": None,
    # Sprint 3 — matrix-gated location fields (always-visible ones like
    # city, microdistrict, landmark, urgent_flag, seller_telegram are NOT
    # in the matrix and therefore not cleared).
    "jk_name": None,
    "metro_station": None,
    # Sprint 4 — commercial-only
    "commercial_type": None,
    "price_per_sqm": None,
    "ceiling_height": None,
    "entrance": None,
    "parking_comm": None,
    "building_class": None,
    # Sprint 5 — dual-read renames
    "market_type": None,
    "wall_material": None,
    "furniture": None,
    # Sprint 6 — property polish
    "garage": None,
    "basement": None,
    "buildings_exist": None,
    "fence": None,
    "land_shape": None,
    "balcony": None,
    "listing_subtype": None,
    "floor_plan_url": None,
}

_ALL_CLEARABLE_FIELDS = frozenset(_CLEARING_VALUES.keys())


def _is_empty_for_clearing(field: str, current) -> bool:
    """Return True when `current` is already at its canonical empty value
    for `field`, so clearing would be a no-op.

    Booleans with default False are treated as "empty" only when already False,
    so a non-applicable True (e.g. mortgage_ok=True on a rental) still gets
    wiped and logged.
    """
    empty = _CLEARING_VALUES[field]
    if empty is False:
        return current is False or current is None
    # Scalars + arrays: None / [] / "" count as empty.
    return current is None or current == [] or current == ""


def _clear_incompatible_fields(listing: Listing) -> List[str]:
    """
    Enforce the visibility matrix on a Listing instance in-place (T-024).

    Applied BEFORE _validate_required_fields. Rules in execution order
    (blueprint §2.3):

        P1: keep only fields in the allowlist for (property_type, type);
            wipe everything else to its canonical empty value.
        P2: (implicitly handled by the matrix — sale-only and rent-only
            field groups are already excluded from the opposite allowlist.)
        P4: if rent_period != 'long_term', wipe min_rent_months.

    Rule P3 (land forces sell) was retired when land × rent became a legal
    combo with its own matrix entry.

    No-op for fields already at their empty value. Returns the list of fields
    actually cleared, or an empty list if nothing changed. Logged at INFO
    when non-empty.

    Mirrors frontend/.../listing-form/lib/visibility.ts. Changes here MUST
    be reflected in the TypeScript matrix and vice-versa.
    """
    pt = listing.property_type.value if listing.property_type else None
    if not pt:
        return []

    dt = listing.type.value if listing.type else None
    if not dt:
        # No deal type yet (shouldn't happen post-schema-validation); skip.
        return []

    allowlist = _VISIBILITY_MATRIX.get((pt, dt), frozenset())

    cleared: List[str] = []
    # Rule P1 (property_type allowlist) + P2 (implicit via sale/rent split).
    for field in _ALL_CLEARABLE_FIELDS:
        if field in allowlist:
            continue
        current = getattr(listing, field, None)
        if _is_empty_for_clearing(field, current):
            continue
        setattr(listing, field, _CLEARING_VALUES[field])
        cleared.append(field)

    # Rule P4 — rent_period sub-gate on min_rent_months.
    # Only wipe when min_rent_months is still visible per the matrix (i.e. we
    # didn't already clear it above on a type/property_type transition).
    if (
        "min_rent_months" in allowlist
        and listing.rent_period != "long_term"
        and listing.min_rent_months is not None
    ):
        listing.min_rent_months = None
        cleared.append("min_rent_months")

    # Rule P5 (Sprint 3, blueprint §2.2.5) — region sub-gate on
    # metro_station. metro_station only applies inside Tashkent city; on
    # any other region we wipe it even if the matrix would otherwise
    # leave it visible (e.g. apartment × rent in Samarkand).
    if (
        "metro_station" in allowlist
        and getattr(listing, "region", None) != "toshkent_shahri"
        and getattr(listing, "metro_station", None) is not None
    ):
        listing.metro_station = None
        cleared.append("metro_station")

    if cleared:
        logger.info(
            "cleared_incompatible_fields listing_id=%s seller_id=%s pt=%s dt=%s fields=%s",
            getattr(listing, "id", None),
            getattr(listing, "seller_id", None),
            pt,
            dt,
            sorted(cleared),
        )
    return cleared


def _validate_required_fields(listing: Listing, *, is_create: bool = True) -> None:
    """
    Validate that a listing has all fields required for its property_type.

    Mirrors the frontend validation rules in useListingForm.ts so a user
    cannot clear required fields via PATCH and save an incomplete listing.
    Raises BadRequestException on first violation.

    Some required-field rules only apply on CREATE to avoid 400-ing PATCH
    requests on legacy rows that predate the rule (e.g. city added in S3,
    commercial_type added in S4). Callers pass is_create=False on PATCH.
    """
    pt = listing.property_type.value if listing.property_type else None
    if not pt:
        raise BadRequestException("property_type is required")

    is_apt = pt == "apartment"
    is_house = pt == "house"
    is_com = pt == "commercial"
    is_land = pt == "land"

    missing: List[str] = []

    # Deal type (sell/rent) — required for every property type
    if not listing.type:
        missing.append("type")

    # Price — required unless negotiable
    if not listing.is_negotiable and (listing.price is None or listing.price <= 0):
        missing.append("price")

    # Rooms — required for apartment/house
    if (is_apt or is_house) and listing.rooms is None:
        missing.append("rooms")

    # Total area — required for everything except land
    if not is_land and (listing.area is None or listing.area <= 0):
        missing.append("area")

    # Floor — required for apartment/commercial
    if (is_apt or is_com) and listing.floor is None:
        missing.append("floor")

    # Total floors — required for apartment/house/commercial
    if (is_apt or is_house or is_com) and listing.total_floors is None:
        missing.append("total_floors")

    # Apartment-only required fields — S5 dual-read: check the new
    # canonical column (market_type) OR the legacy column (building_type)
    # so rows from both the old and new form submit paths pass.
    if is_apt and not (listing.market_type or listing.building_type):
        missing.append("building_type")

    # Condition — required for apartment/commercial
    if (is_apt or is_com) and not listing.condition:
        missing.append("condition")

    # Furnished — required for everything except land. S5 dual-read:
    # accept either the new enum (furniture) or the legacy bool
    # (is_furnished).
    if not is_land and listing.furniture is None and listing.is_furnished is None:
        missing.append("is_furnished")

    # ── Sprint 2: rent-specific required fields (blueprint §3.3) ──────
    dt = listing.type.value if listing.type else None
    if dt == "rent":
        # rent_period must be chosen for every rental (long_term | daily)
        if not listing.rent_period:
            missing.append("rent_period")
        # long-term rentals must also commit to a minimum term
        elif listing.rent_period == "long_term" and listing.min_rent_months is None:
            missing.append("min_rent_months")

    # Location — required
    if not listing.region:
        missing.append("region")
    if not listing.district:
        missing.append("district")

    # Sprint 3 (T-001 / blueprint §1.3): city promoted to required on CREATE.
    # Legacy rows (pre-S3) may lack `city`; we can't reject their PATCHes or
    # every edit on old data would 400.
    if is_create and not getattr(listing, "city", None):
        missing.append("city")

    # Sprint 4 (T-009 / blueprint §1.3): commercial listings must declare
    # their commercial_type — only on CREATE, for the same legacy-safety
    # reason as `city` above.
    if is_create and is_com and not getattr(listing, "commercial_type", None):
        missing.append("commercial_type")

    # Map coordinates — required
    if listing.latitude is None or listing.longitude is None:
        missing.append("location")

    if missing:
        raise BadRequestException(
            f"Required fields missing or empty: {', '.join(missing)}"
        )


# ── Sprint 5 — Dual-read helpers (T-006, T-008, T-025) ───────────────
#
# Per blueprint §3 the renames `building_type → market_type` and
# `is_furnished → furniture` ship in two phases; during the dual-read
# window we accept BOTH names on input (with conflict → 400) and write
# only to the new column. Responses mirror both names.


def _apply_dual_read_inputs(payload: dict) -> dict:
    """Normalize incoming create/update payloads.

    Accepts either old or new field names; if both are present, raises.
    Returns a payload with ONLY the new names so downstream code never
    has to think about aliases.
    """
    out = dict(payload)

    if (
        "building_type" in out
        and "market_type" in out
        and out["building_type"] is not None
        and out["market_type"] is not None
    ):
        raise BadRequestException(
            "Cannot supply both `building_type` and `market_type`; pick one."
        )
    if out.get("building_type") is not None and out.get("market_type") is None:
        out["market_type"] = out["building_type"]

    if (
        "is_furnished" in out
        and "furniture" in out
        and out["is_furnished"] is not None
        and out["furniture"] is not None
    ):
        raise BadRequestException(
            "Cannot supply both `is_furnished` and `furniture`; pick one."
        )
    if out.get("is_furnished") is not None and out.get("furniture") is None:
        out["furniture"] = (
            "full"
            if out["is_furnished"] is True
            else "none"
            if out["is_furnished"] is False
            else None
        )
    return out


def _apply_dual_read_response(listing) -> dict:
    """Mirror the new columns back into the deprecated names so existing
    clients keep receiving `building_type` / `is_furnished`. Returns a
    dict suitable for spreading into a ListingResponse builder."""
    market_type = getattr(listing, "market_type", None)
    building_type = getattr(listing, "building_type", None) or market_type

    furniture = getattr(listing, "furniture", None)
    if getattr(listing, "is_furnished", None) is None and furniture is not None:
        is_furnished = True if furniture in ("full", "partial", "built_in") else False
    else:
        is_furnished = getattr(listing, "is_furnished", None)

    return {
        "building_type": building_type,
        "market_type": market_type,
        "is_furnished": is_furnished,
        "furniture": furniture,
    }


# ── S3–S8 response kwargs (single source of truth) ───────────────────
#
# Prevents drift across the three ListingResponse builders in this file
# (get_listing, create_listing, update_listing). Each builder spreads the
# returned dict via `**` so adding a new S3–S8 field here propagates to
# every response path automatically.
#
# NOTE: Caller MUST NOT also pass `building_type` or `is_furnished` as
# explicit kwargs — those come from the dual-read mirror in this dict.
def _build_full_response_kwargs(listing) -> dict:
    """Return S3–S8 DB fields + S5 dual-read mirrors as response kwargs."""
    return {
        # S3 — location
        "urgent_flag": getattr(listing, "urgent_flag", None),
        "city": getattr(listing, "city", None),
        "microdistrict": getattr(listing, "microdistrict", None),
        "jk_name": getattr(listing, "jk_name", None),
        "landmark": getattr(listing, "landmark", None),
        "metro_station": getattr(listing, "metro_station", None),
        "seller_telegram": getattr(listing, "seller_telegram", None),
        # S4 — commercial
        "commercial_type": getattr(listing, "commercial_type", None),
        "price_per_sqm": getattr(listing, "price_per_sqm", None),
        "ceiling_height": getattr(listing, "ceiling_height", None),
        "entrance": getattr(listing, "entrance", None),
        "parking_comm": getattr(listing, "parking_comm", None),
        "building_class": getattr(listing, "building_class", None),
        # S5 — wall_material (dual-read mirrors supplied below)
        "wall_material": getattr(listing, "wall_material", None),
        # S6 — property polish
        "garage": getattr(listing, "garage", None),
        "basement": getattr(listing, "basement", None),
        "buildings_exist": getattr(listing, "buildings_exist", None),
        "fence": getattr(listing, "fence", None),
        "land_shape": getattr(listing, "land_shape", None),
        "balcony": getattr(listing, "balcony", None),
        "listing_subtype": getattr(listing, "listing_subtype", None),
        "floor_plan_url": getattr(listing, "floor_plan_url", None),
        # S7 — roles/media
        "jk_id": getattr(listing, "jk_id", None),
        # S8 — discoverability
        "slug": getattr(listing, "slug", None),
        # F1 — Block F AI description per locale. The frontend picks
        # the active locale on its side; we expose all three so a
        # language toggle on the buyer side never requires a refetch.
        "ai_description_ru": getattr(listing, "ai_description_ru", None),
        "ai_description_uz": getattr(listing, "ai_description_uz", None),
        "ai_description_uz_cyrl": getattr(listing, "ai_description_uz_cyrl", None),
        # S5 — dual-read mirrors: supplies building_type, market_type,
        # is_furnished, furniture. MUST come last to override any earlier
        # keys.
        **_apply_dual_read_response(listing),
    }


# ── Filter applicability engine (T-018) ──────────────────────────────
#
# Silent-drop rule: filters whose underlying column isn't visible for the
# caller's (property_type, deal_type) combo are quietly dropped instead of
# 4xx'd. Underlying source of truth is _VISIBILITY_MATRIX, so this stays in
# lockstep with the state machine and the frontend visibility.ts.

# Filter name → column name. Filters not in this map are considered always-
# applicable (q, type, property_type, region, district, price_min/max,
# seller_id, source_type, sort_by, sort_order, rooms for free-text search).
_FILTER_TO_FIELD = {
    # Rent group
    "rent_period": "rent_period",
    "utilities_incl": "utilities_incl",
    "min_rent_months": "min_rent_months",
    "allowed_students": "allowed_students",
    "allowed_pets": "allowed_pets",
    "rent_payment": "rent_payment",
    "deposit_min": "deposit",
    "deposit_max": "deposit",
    # Sale finance + deed
    "mortgage_ok": "mortgage_ok",
    "installment_ok": "installment_ok",
    "halol_ok": "halol_ok",
    "deed_type": "deed_type",
    # Matrix-gated Phase-2 fields
    "building_type": "building_type",
    "condition": "condition",
    "furnished": "is_furnished",
    "amenities": "amenities",
    "nearby_amenities": "nearby_amenities",
    "land_area_min": "land_area",
    "land_area_max": "land_area",
    "rooms": "rooms",
    "area_min": "area",
    "area_max": "area",
    "floor_min": "floor",
    "floor_max": "floor",
    # A2 — house-specific filters (visible only in the house matrix
    # combos; mapped here so _filter_is_applicable gates them just
    # like building_type/condition/amenities).
    "house_type": "house_type",
    "house_condition": "house_condition",
    "water_supply": "water_supply",
    # ── Sprint 3 (T-001) — location filters ──────────────────────────
    # city/microdistrict/urgent_flag/jk_name are always-applicable at the
    # listing level (they aren't in the matrix as "visible-only" fields)
    # but we still map them so _filter_is_applicable can look them up.
    # `jk_name` and `metro_station` ARE matrix-gated.
    "jk_name": "jk_name",
    "metro_station": "metro_station",
    # ── Sprint 4 (T-009) — commercial filters ────────────────────────
    "commercial_type": "commercial_type",
    "building_class": "building_class",
    "entrance": "entrance",
    "parking_comm": "parking_comm",
    "ceiling_height_min": "ceiling_height",
    "ceiling_height_max": "ceiling_height",
    "price_per_sqm_min": "price_per_sqm",
    "price_per_sqm_max": "price_per_sqm",
    # ── Sprint 5 (T-006, T-008) — dual-read columns ──────────────────
    "market_type": "market_type",
    "wall_material": "wall_material",
    "furniture": "furniture",
    # ── Sprint 6 (T-011, T-014, T-015) — property polish ─────────────
    "garage": "garage",
    "basement": "basement",
    "buildings_exist": "buildings_exist",
    "fence": "fence",
    "land_shape": "land_shape",
    "balcony": "balcony",
    "listing_subtype": "listing_subtype",
    # Note: city, microdistrict, urgent_flag, jk_id are intentionally NOT
    # mapped — they're not matrix-gated, so they fall through the default-
    # open branch in _filter_is_applicable and always apply.
}

# Filters that always run regardless of property_type/type.
_ALWAYS_APPLICABLE = frozenset(
    {
        "q",
        "type",
        "property_type",
        "region",
        "district",
        "price_min",
        "price_max",
        "seller_id",
        "source_type",
        "sort_by",
        "sort_order",
    }
)


def _filter_is_applicable(
    filter_key: str, pt: Optional[str], dt: Optional[str]
) -> bool:
    """Decide whether `filter_key` applies to the requested `(pt, dt)`.

    When the caller pins both pt and dt, we apply the matrix exactly —
    filters whose column isn't visible for that combo are silently dropped
    (per blueprint §4.3 and sprint-2 tech doc §2.4).

    When the caller pins only pt (or only dt, or neither), we widen: the
    filter applies iff its column is visible in AT LEAST ONE matching combo.
    This keeps the filter useful for cross-type searches.
    """
    if filter_key in _ALWAYS_APPLICABLE:
        return True
    field = _FILTER_TO_FIELD.get(filter_key)
    if field is None:
        # Unknown filter — default open. Pydantic will have already rejected
        # anything malformed, so this branch is for forward-compat.
        return True
    if pt and dt:
        return field in _VISIBILITY_MATRIX.get((pt, dt), frozenset())
    if pt:
        return any(
            field in _VISIBILITY_MATRIX.get((pt, d), frozenset())
            for d in ("sell", "rent")
        )
    if dt:
        return any(
            field in _VISIBILITY_MATRIX.get((p, dt), frozenset())
            for p in ("apartment", "house", "commercial", "land")
        )
    return True


def _apply_filters(query, filters: "ListingFilters"):
    """Apply a ListingFilters to a base SELECT.

    Respects the applicability matrix: irrelevant filters are silently
    skipped, not rejected. Returns the mutated query.
    """
    pt = filters.property_type
    dt = filters.type

    # ── Always-applicable filters (free-form + pinning) ──────────────
    if filters.type:
        query = query.where(Listing.type == filters.type)
    if filters.property_type:
        query = query.where(Listing.property_type == filters.property_type)
    if filters.region:
        query = query.where(Listing.region.in_(filters.region))
    if filters.district:
        query = query.where(Listing.district.in_(filters.district))
    if filters.seller_id:
        query = query.where(Listing.seller_id == filters.seller_id)
    if filters.source_type:
        query = query.where(Listing.source_type == filters.source_type)
    if filters.price_min is not None:
        query = query.where(Listing.price >= filters.price_min)
    if filters.price_max is not None:
        query = query.where(Listing.price <= filters.price_max)
    if filters.q:
        term = f"%{filters.q}%"
        query = query.where(
            or_(
                Listing.title.ilike(term),
                Listing.description.ilike(term),
                Listing.district.ilike(term),
                Listing.address.ilike(term),
            )
        )

    # ── Matrix-gated filters ─────────────────────────────────────────
    # rooms
    if filters.rooms and _filter_is_applicable("rooms", pt, dt):
        query = query.where(Listing.rooms.in_(filters.rooms))
    # area range
    if filters.area_min is not None and _filter_is_applicable("area_min", pt, dt):
        query = query.where(Listing.area >= filters.area_min)
    if filters.area_max is not None and _filter_is_applicable("area_max", pt, dt):
        query = query.where(Listing.area <= filters.area_max)
    # floor range
    if filters.floor_min is not None and _filter_is_applicable("floor_min", pt, dt):
        query = query.where(Listing.floor >= filters.floor_min)
    if filters.floor_max is not None and _filter_is_applicable("floor_max", pt, dt):
        query = query.where(Listing.floor <= filters.floor_max)
    # land area range
    if filters.land_area_min is not None and _filter_is_applicable(
        "land_area_min", pt, dt
    ):
        query = query.where(Listing.land_area >= filters.land_area_min)
    if filters.land_area_max is not None and _filter_is_applicable(
        "land_area_max", pt, dt
    ):
        query = query.where(Listing.land_area <= filters.land_area_max)

    # building_type / condition / furnished
    if filters.building_type and _filter_is_applicable("building_type", pt, dt):
        query = query.where(Listing.building_type == filters.building_type)
    if filters.condition and _filter_is_applicable("condition", pt, dt):
        query = query.where(Listing.condition.in_(filters.condition))
    if filters.furnished is not None and _filter_is_applicable("furnished", pt, dt):
        query = query.where(Listing.is_furnished == filters.furnished)

    # amenities / nearby_amenities: AND-match via Postgres @> (contains).
    if filters.amenities and _filter_is_applicable("amenities", pt, dt):
        query = query.where(Listing.amenities.contains(filters.amenities))
    if filters.nearby_amenities and _filter_is_applicable("nearby_amenities", pt, dt):
        query = query.where(Listing.nearby_amenities.contains(filters.nearby_amenities))

    # ── A2 — house-specific filters (visibility-matrix gated) ───────
    # house_type is a scalar equality match. house_condition and
    # water_supply are ARRAY columns; use Postgres `&&` (overlap) so a
    # buyer who selected ANY of the chosen options matches — the same
    # pattern as `rent_payment` above (whereas amenities uses `@>`
    # for AND-match, which is intentionally stricter).
    if filters.house_type and _filter_is_applicable("house_type", pt, dt):
        query = query.where(Listing.house_type == filters.house_type)
    if filters.house_condition and _filter_is_applicable("house_condition", pt, dt):
        query = query.where(Listing.house_condition.overlap(filters.house_condition))
    if filters.water_supply and _filter_is_applicable("water_supply", pt, dt):
        query = query.where(Listing.water_supply.overlap(filters.water_supply))

    # ── Rent group (silently dropped when type=sell etc.) ────────────
    if filters.rent_period and _filter_is_applicable("rent_period", pt, dt):
        query = query.where(Listing.rent_period == filters.rent_period)
    if filters.utilities_incl is not None and _filter_is_applicable(
        "utilities_incl", pt, dt
    ):
        query = query.where(Listing.utilities_incl == filters.utilities_incl)
    if filters.min_rent_months and _filter_is_applicable("min_rent_months", pt, dt):
        query = query.where(Listing.min_rent_months.in_(filters.min_rent_months))
    if filters.allowed_students is not None and _filter_is_applicable(
        "allowed_students", pt, dt
    ):
        query = query.where(Listing.allowed_students == filters.allowed_students)
    if filters.allowed_pets is not None and _filter_is_applicable(
        "allowed_pets", pt, dt
    ):
        query = query.where(Listing.allowed_pets == filters.allowed_pets)
    # rent_payment: OVERLAP (listing supports ANY of the selected methods).
    if filters.rent_payment and _filter_is_applicable("rent_payment", pt, dt):
        query = query.where(Listing.rent_payment.overlap(filters.rent_payment))
    if filters.deposit_min is not None and _filter_is_applicable("deposit_min", pt, dt):
        query = query.where(Listing.deposit >= filters.deposit_min)
    if filters.deposit_max is not None and _filter_is_applicable("deposit_max", pt, dt):
        query = query.where(Listing.deposit <= filters.deposit_max)

    # ── Sale finance + deed (silently dropped when type=rent etc.) ───
    # Booleans: we only filter on `True`. The matrix hides these columns on
    # rent listings, so "mortgage_ok=false" is semantically meaningless
    # there (the flag itself isn't exposed).
    if filters.mortgage_ok and _filter_is_applicable("mortgage_ok", pt, dt):
        query = query.where(Listing.mortgage_ok.is_(True))
    if filters.installment_ok and _filter_is_applicable("installment_ok", pt, dt):
        query = query.where(Listing.installment_ok.is_(True))
    if filters.halol_ok and _filter_is_applicable("halol_ok", pt, dt):
        query = query.where(Listing.halol_ok.is_(True))
    if filters.deed_type and _filter_is_applicable("deed_type", pt, dt):
        query = query.where(Listing.deed_type == filters.deed_type)

    # ── Sprint 3 (T-001) — location filters ──────────────────────────
    # city / microdistrict / urgent_flag / jk_id are always-applicable.
    # jk_name and metro_station are matrix-gated.
    if filters.urgent_flag:
        # True-only, mirrors sale-finance booleans.
        query = query.where(Listing.urgent_flag.is_(True))
    if filters.city:
        query = query.where(Listing.city == filters.city)
    if filters.microdistrict:
        query = query.where(Listing.microdistrict == filters.microdistrict)
    if filters.jk_name and _filter_is_applicable("jk_name", pt, dt):
        query = query.where(Listing.jk_name == filters.jk_name)
    if filters.metro_station and _filter_is_applicable("metro_station", pt, dt):
        query = query.where(Listing.metro_station == filters.metro_station)

    # ── Sprint 4 (T-009) — commercial filters ────────────────────────
    if filters.commercial_type and _filter_is_applicable("commercial_type", pt, dt):
        query = query.where(Listing.commercial_type == filters.commercial_type)
    if filters.building_class and _filter_is_applicable("building_class", pt, dt):
        query = query.where(Listing.building_class == filters.building_class)
    if filters.entrance and _filter_is_applicable("entrance", pt, dt):
        query = query.where(Listing.entrance == filters.entrance)
    if filters.parking_comm is not None and _filter_is_applicable(
        "parking_comm", pt, dt
    ):
        query = query.where(Listing.parking_comm == filters.parking_comm)
    if filters.ceiling_height_min is not None and _filter_is_applicable(
        "ceiling_height_min", pt, dt
    ):
        query = query.where(Listing.ceiling_height >= filters.ceiling_height_min)
    if filters.ceiling_height_max is not None and _filter_is_applicable(
        "ceiling_height_max", pt, dt
    ):
        query = query.where(Listing.ceiling_height <= filters.ceiling_height_max)
    if filters.price_per_sqm_min is not None and _filter_is_applicable(
        "price_per_sqm_min", pt, dt
    ):
        query = query.where(Listing.price_per_sqm >= filters.price_per_sqm_min)
    if filters.price_per_sqm_max is not None and _filter_is_applicable(
        "price_per_sqm_max", pt, dt
    ):
        query = query.where(Listing.price_per_sqm <= filters.price_per_sqm_max)

    # ── Sprint 5 (T-006, T-008) — dual-read columns ──────────────────
    if filters.market_type and _filter_is_applicable("market_type", pt, dt):
        query = query.where(Listing.market_type == filters.market_type)
    if filters.wall_material and _filter_is_applicable("wall_material", pt, dt):
        query = query.where(Listing.wall_material == filters.wall_material)
    if filters.furniture and _filter_is_applicable("furniture", pt, dt):
        query = query.where(Listing.furniture == filters.furniture)

    # ── Sprint 6 (T-011, T-014, T-015) — property polish ─────────────
    if filters.garage is not None and _filter_is_applicable("garage", pt, dt):
        query = query.where(Listing.garage == filters.garage)
    if filters.basement is not None and _filter_is_applicable("basement", pt, dt):
        query = query.where(Listing.basement == filters.basement)
    if filters.buildings_exist is not None and _filter_is_applicable(
        "buildings_exist", pt, dt
    ):
        query = query.where(Listing.buildings_exist == filters.buildings_exist)
    if filters.fence is not None and _filter_is_applicable("fence", pt, dt):
        query = query.where(Listing.fence == filters.fence)
    if filters.land_shape and _filter_is_applicable("land_shape", pt, dt):
        query = query.where(Listing.land_shape == filters.land_shape)
    if filters.balcony and _filter_is_applicable("balcony", pt, dt):
        query = query.where(Listing.balcony == filters.balcony)
    if filters.listing_subtype and _filter_is_applicable("listing_subtype", pt, dt):
        query = query.where(Listing.listing_subtype == filters.listing_subtype)

    # ── Sprint 7 (T-027) — jk_id (always-applicable) ─────────────────
    if filters.jk_id:
        query = query.where(Listing.jk_id == filters.jk_id)

    return query


@router.get("", response_model=PaginatedResponse[ListingListResponse])
async def list_listings(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    # ── Sprint 1 filters (unchanged names) ──────────────────────────
    q: Optional[str] = Query(None, max_length=200),
    type: Optional[str] = Query(None, pattern="^(sell|rent)$"),
    property_type: Optional[str] = Query(
        None, pattern="^(apartment|house|commercial|land)$"
    ),
    rooms: Optional[List[int]] = Query(None),
    price_min: Optional[int] = Query(None, ge=0),
    price_max: Optional[int] = Query(None, le=100000000),
    area_min: Optional[float] = Query(None, ge=0),
    area_max: Optional[float] = Query(None, le=100000),
    floor_min: Optional[int] = Query(None, ge=-5),
    floor_max: Optional[int] = Query(None, le=100),
    region: Optional[List[str]] = Query(None),
    district: Optional[List[str]] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|price|area|views_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    # ── Sprint 2 filters (T-018); silently dropped when (pt, dt) excludes them ──
    land_area_min: Optional[float] = Query(None, ge=0),
    land_area_max: Optional[float] = Query(None, le=100000),
    # Matrix-gated shared
    building_type: Optional[str] = Query(None, pattern="^(new|secondary)$"),
    condition: Optional[List[str]] = Query(None),
    furnished: Optional[bool] = Query(None),
    amenities: Optional[List[str]] = Query(None),
    nearby_amenities: Optional[List[str]] = Query(None),
    # A2 — house-specific filters
    house_type: Optional[str] = Query(None, max_length=50),
    house_condition: Optional[List[str]] = Query(None),
    water_supply: Optional[List[str]] = Query(None),
    # Rent group
    rent_period: Optional[str] = Query(None, pattern="^(long_term|daily)$"),
    utilities_incl: Optional[bool] = Query(None),
    min_rent_months: Optional[List[int]] = Query(None),
    allowed_students: Optional[bool] = Query(None),
    allowed_pets: Optional[bool] = Query(None),
    rent_payment: Optional[List[str]] = Query(None),
    deposit_min: Optional[int] = Query(None, ge=0),
    deposit_max: Optional[int] = Query(None, ge=0),
    # Sale finance + deed
    mortgage_ok: Optional[bool] = Query(None),
    installment_ok: Optional[bool] = Query(None),
    halol_ok: Optional[bool] = Query(None),
    deed_type: Optional[str] = Query(None, pattern="^(cadastre|order|other)$"),
    # ── Sprint 3 (T-001) filters ────────────────────────────────────
    urgent_flag: Optional[bool] = Query(None),
    city: Optional[str] = Query(None, max_length=100),
    microdistrict: Optional[str] = Query(None, max_length=200),
    jk_name: Optional[str] = Query(None, max_length=200),
    metro_station: Optional[str] = Query(None, max_length=50),
    # ── Sprint 4 (T-009) filters ────────────────────────────────────
    commercial_type: Optional[str] = Query(
        None, pattern="^(office|shop|warehouse|production|restaurant|hotel|other)$"
    ),
    building_class: Optional[str] = Query(
        None, pattern="^(standalone|embedded|business_center|mall)$"
    ),
    entrance: Optional[str] = Query(None, pattern="^(separate|yard|street|mall)$"),
    parking_comm: Optional[bool] = Query(None),
    ceiling_height_min: Optional[float] = Query(None, gt=0, le=30),
    ceiling_height_max: Optional[float] = Query(None, gt=0, le=30),
    price_per_sqm_min: Optional[int] = Query(None, ge=0),
    price_per_sqm_max: Optional[int] = Query(None, ge=0),
    # ── Sprint 5 (T-006, T-008) filters — dual-read ─────────────────
    market_type: Optional[str] = Query(None, pattern="^(new|secondary)$"),
    wall_material: Optional[str] = Query(
        None, pattern="^(brick|gasblock|panel|monolith|other)$"
    ),
    furniture: Optional[str] = Query(None, pattern="^(none|partial|full|built_in)$"),
    # ── Sprint 6 (T-011, T-014, T-015) filters ──────────────────────
    garage: Optional[bool] = Query(None),
    basement: Optional[bool] = Query(None),
    buildings_exist: Optional[bool] = Query(None),
    fence: Optional[bool] = Query(None),
    land_shape: Optional[str] = Query(None, pattern="^(rectangular|irregular)$"),
    balcony: Optional[str] = Query(None, pattern="^(none|balcony|loggia|terrace)$"),
    listing_subtype: Optional[str] = Query(
        None, pattern="^(standard|studio|free_plan)$"
    ),
    # ── Sprint 7 (T-027) filters ────────────────────────────────────
    jk_id: Optional[UUID] = Query(None),
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    List and search listings with filters (T-018).

    Filters are applied via the applicability matrix: a filter whose
    underlying column isn't visible for the caller's (property_type, type)
    combo is silently dropped (blueprint §4.3). This preserves the
    lenient-read / strict-write policy — a buyer passing a filter that
    doesn't make sense for their type selection still gets results, just
    with that filter ignored.
    """
    # Build ListingFilters from query params. Pydantic runs its validators
    # here (range pairs, enum members, array elements).
    try:
        filters = ListingFilters(
            q=q,
            type=type,
            property_type=property_type,
            rooms=rooms,
            price_min=price_min,
            price_max=price_max,
            area_min=area_min,
            area_max=area_max,
            floor_min=floor_min,
            floor_max=floor_max,
            region=region,
            district=district,
            seller_id=None,
            source_type=None,
            sort_by=sort_by,
            sort_order=sort_order,
            land_area_min=land_area_min,
            land_area_max=land_area_max,
            building_type=building_type,
            condition=condition,
            furnished=furnished,
            amenities=amenities,
            nearby_amenities=nearby_amenities,
            house_type=house_type,
            house_condition=house_condition,
            water_supply=water_supply,
            rent_period=rent_period,
            utilities_incl=utilities_incl,
            min_rent_months=min_rent_months,
            allowed_students=allowed_students,
            allowed_pets=allowed_pets,
            rent_payment=rent_payment,
            deposit_min=deposit_min,
            deposit_max=deposit_max,
            mortgage_ok=mortgage_ok,
            installment_ok=installment_ok,
            halol_ok=halol_ok,
            deed_type=deed_type,
            urgent_flag=urgent_flag,
            city=city,
            microdistrict=microdistrict,
            jk_name=jk_name,
            metro_station=metro_station,
            commercial_type=commercial_type,
            building_class=building_class,
            entrance=entrance,
            parking_comm=parking_comm,
            ceiling_height_min=ceiling_height_min,
            ceiling_height_max=ceiling_height_max,
            price_per_sqm_min=price_per_sqm_min,
            price_per_sqm_max=price_per_sqm_max,
            market_type=market_type,
            wall_material=wall_material,
            furniture=furniture,
            garage=garage,
            basement=basement,
            buildings_exist=buildings_exist,
            fence=fence,
            land_shape=land_shape,
            balcony=balcony,
            listing_subtype=listing_subtype,
            jk_id=jk_id,
        )
    except ValueError as exc:
        raise BadRequestException(str(exc))

    # PR10 — route through the search router. `meili_ids` is None for the
    # Postgres path (default) or a list of IDs when Meili returned hits;
    # the runner closure handles both. Any Meili failure falls back to
    # the Postgres path with `meili_ids=None`.
    async def _run_pg(**kw):
        return await _postgres_listings_search(request=request, **kw)

    from app.services import search_router

    return await search_router.get_listings(
        filters=filters,
        db_session=db,
        page=page,
        per_page=per_page,
        current_user=current_user,
        postgres_runner=_run_pg,
    )


async def _postgres_listings_search(
    *,
    filters: ListingFilters,
    db_session: AsyncSession,
    page: int,
    per_page: int,
    current_user,
    request: Request,
    meili_ids=None,
    meili_total=None,
):
    """The canonical Postgres read path for GET /listings.

    When `meili_ids` is None (default), runs `_apply_filters` against the
    DB — this is byte-identical to the pre-PR10 endpoint.

    When `meili_ids` is a list, bypasses `_apply_filters` and fetches
    exactly those IDs in the order Meili returned them; `meili_total` is
    used as the paginated total. This keeps the response schema
    identical regardless of which backend decided the result set.
    """
    db = db_session

    # ── Fetch rows ─────────────────────────────────────────────────
    if meili_ids is not None:
        # Meili path: hydrate the specific rows Meili matched, preserve
        # Meili's ordering.
        if not meili_ids:
            return PaginatedResponse.create(
                items=[],
                total=int(meili_total or 0),
                page=page,
                per_page=per_page,
            )
        hydrate_q = (
            select(Listing)
            .where(Listing.id.in_(meili_ids))
            .options(
                selectinload(Listing.images),
                selectinload(Listing.seller),
            )
        )
        result = await db.execute(hydrate_q)
        by_id = {item.id: item for item in result.scalars().all()}
        # Preserve Meili rank order; silently skip IDs no longer in PG
        # (listing was deleted between the Meili query and the hydrate).
        from uuid import UUID as _UUID

        listings = []
        for raw_id in meili_ids:
            key = raw_id if isinstance(raw_id, _UUID) else _UUID(str(raw_id))
            row = by_id.get(key)
            if row is not None:
                listings.append(row)
        total = int(meili_total or 0)
    else:
        # Default Postgres path — unchanged from pre-PR10.
        # Block A V2.0: ACTIVE + GENERATION_FAILED both surface in B2C; the
        # latter renders with a template description instead of AI text.
        # PENDING_GENERATION and UNCONFIRMED are explicitly excluded.
        query = select(Listing).where(
            Listing.status.in_(
                [ListingStatus.ACTIVE, ListingStatus.GENERATION_FAILED]
            ),
            Listing.moderation_status == ModerationStatus.APPROVED,
            Listing.deleted_at.is_(None),
            # F108: hide non-canonical duplicates from the public feed.
            Listing.master_record_id.is_(None),
        )
        query = _apply_filters(query, filters)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        sort_column = getattr(Listing, filters.sort_by)
        # F108: claimed listings (claimed_at IS NOT NULL) outrank unclaimed
        # ones at the same age. Boosted still wins overall.
        claim_rank = (Listing.claimed_at.is_not(None)).desc()
        if filters.sort_order == "desc":
            query = query.order_by(
                Listing.is_boosted.desc(), claim_rank, sort_column.desc()
            )
        else:
            query = query.order_by(
                Listing.is_boosted.desc(), claim_rank, sort_column.asc()
            )

        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        query = query.options(
            selectinload(Listing.images),
            selectinload(Listing.seller),
        )
        result = await db.execute(query)
        listings = result.scalars().all()

    # ── Build response (shared by both paths) ──────────────────────
    user_favorites = set()
    if current_user:
        fav_result = await db.execute(
            select(Favorite.listing_id).where(Favorite.user_id == current_user.id)
        )
        user_favorites = set(fav_result.scalars().all())

    lang = get_content_language(request)
    items = []
    for listing in listings:
        primary_image = next(
            (img for img in listing.images if img.is_primary),
            listing.images[0] if listing.images else None,
        )
        items.append(
            ListingListResponse(
                id=listing.id,
                type=listing.type.value,
                property_type=listing.property_type.value,
                rooms=listing.rooms,
                area=listing.area,
                floor=listing.floor,
                total_floors=listing.total_floors,
                region=listing.region,
                district=listing.district,
                price=listing.price,
                currency=listing.currency.value,
                title=_resolve_field(listing, "title", lang),
                description=text_snippet(_resolve_field(listing, "description", lang)),
                views_count=listing.views_count,
                favorites_count=listing.favorites_count,
                comments_count=listing.comments_count,
                is_boosted=listing.is_boosted,
                is_highlighted=listing.is_highlighted,
                created_at=listing.created_at,
                primary_image_url=primary_image.medium_url if primary_image else None,
                is_favorited=listing.id in user_favorites,
                rent_period=listing.rent_period,
                land_area=listing.land_area,
                mortgage_ok=listing.mortgage_ok,
                installment_ok=listing.installment_ok,
                halol_ok=listing.halol_ok,
                urgent_flag=None,
                is_verified=(listing.seller.is_verified if listing.seller else None),
            )
        )

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


# =============================================================================
# T-019 Facets endpoint (must be above /{listing_id} catch-all)
# =============================================================================
#
# Returns aggregated value counts for the 10 facet dimensions. Reuses the
# T-018 filter engine verbatim — no duplicated WHERE clauses — and honors
# the applicability matrix: a facet whose underlying filter is silently
# dropped for the caller's (property_type, type) combo is OMITTED from the
# response entirely (per spec: "DO NOT include empty facets, DO NOT include
# null values").
#
# Redis 60s TTL cache; safe fallback — if Redis is unavailable we compute
# fresh and return without error.

# Facet spec: response_key → (filter_key for applicability, style).
# `filter_key` matches _FILTER_TO_FIELD / _ALWAYS_APPLICABLE so the same
# applicability gate used by /listings also governs /facets.
#
# Styles:
#   "scalar_enum"  — group by Listing.<column>, emit {value: str, count}
#   "scalar_int"   — group by Listing.<column>, emit {value: int, count}
#   "array"        — unnest Listing.<column>, group, emit {value: str, count}
#   "boolean_true" — WHERE <column> = TRUE, count, emit [{value: true, count}]
_FACET_SPECS: list = [
    # (response_key, filter_key, column_name, style, enum_value_accessor)
    # enum_value_accessor is a callable to unwrap SQLAlchemy Enum rows.
    (
        "deal_type",
        "type",
        "type",
        "scalar_enum",
        lambda v: v.value if hasattr(v, "value") else v,
    ),
    (
        "property_type",
        "property_type",
        "property_type",
        "scalar_enum",
        lambda v: v.value if hasattr(v, "value") else v,
    ),
    ("region", "region", "region", "scalar_enum", lambda v: v),
    ("district", "district", "district", "scalar_enum", lambda v: v),
    ("rooms", "rooms", "rooms", "scalar_int", lambda v: v),
    ("rent_period", "rent_period", "rent_period", "scalar_enum", lambda v: v),
    ("rent_payment", "rent_payment", "rent_payment", "array", lambda v: v),
    ("mortgage_ok", "mortgage_ok", "mortgage_ok", "boolean_true", None),
    ("installment_ok", "installment_ok", "installment_ok", "boolean_true", None),
    ("halol_ok", "halol_ok", "halol_ok", "boolean_true", None),
    # ── Sprint 3 (T-001) — urgent flag facet ─────────────────────────
    ("urgent_flag", "urgent_flag", "urgent_flag", "boolean_true", None),
    # ── Sprint 4 (T-009) — commercial ────────────────────────────────
    (
        "commercial_type",
        "commercial_type",
        "commercial_type",
        "scalar_enum",
        lambda v: v,
    ),
    ("building_class", "building_class", "building_class", "scalar_enum", lambda v: v),
    # ── Sprint 5 (T-006, T-008) — dual-read ──────────────────────────
    ("market_type", "market_type", "market_type", "scalar_enum", lambda v: v),
    ("furniture", "furniture", "furniture", "scalar_enum", lambda v: v),
]


def _facets_cache_key(filters: ListingFilters) -> str:
    """Stable cache key from filter state. JSON-dumped and SHA-256'd so
    equivalent filter sets map to the same key regardless of insertion
    order.
    """
    import hashlib
    import json

    payload = filters.model_dump(mode="json", exclude_none=False)
    # Lists serialize order-sensitive; buyers typically pass a set-like
    # filter so we sort list values for cache stability. Dict keys are
    # already sorted via sort_keys=True.
    for k, v in list(payload.items()):
        if isinstance(v, list):
            payload[k] = sorted(
                v, key=lambda x: ("", "") if x is None else (type(x).__name__, str(x))
            )
    serialized = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
    return f"facets:{digest}"


async def _compute_facets(db: AsyncSession, filters: ListingFilters) -> dict:
    """Run one aggregate SELECT per applicable facet against the filtered
    base set. Returns a dict mapping response_key -> list[{value, count}].
    Skips non-applicable facets (per _filter_is_applicable) and empty
    result sets.
    """
    from sqlalchemy import literal_column

    # Build the SAME filtered base query /listings uses. Reusing
    # _apply_filters is non-negotiable — no duplicated WHERE logic.
    base = select(Listing.id).where(
        Listing.status == ListingStatus.ACTIVE,
        Listing.moderation_status == ModerationStatus.APPROVED,
        Listing.deleted_at.is_(None),
    )
    base = _apply_filters(base, filters)
    # A subquery lets us inject arbitrary aggregate columns without
    # disturbing the carefully-tuned filter WHERE tree.
    filtered_ids = base.subquery("filtered")

    pt = filters.property_type
    dt = filters.type
    result: dict = {}

    for response_key, filter_key, column_name, style, accessor in _FACET_SPECS:
        if not _filter_is_applicable(filter_key, pt, dt):
            # Spec: non-applicable facets are OMITTED entirely.
            continue

        col = getattr(Listing, column_name)

        if style == "boolean_true":
            q = (
                select(func.count())
                .select_from(Listing)
                .join(filtered_ids, Listing.id == filtered_ids.c.id)
                .where(col.is_(True))
            )
            n = (await db.execute(q)).scalar() or 0
            if n > 0:
                result[response_key] = [FacetBucket(value=True, count=int(n))]
            # n == 0 → empty facet → OMIT
            continue

        if style == "array":
            unnested = func.unnest(col).label("v")
            q = (
                select(unnested, func.count().label("c"))
                .select_from(Listing)
                .join(filtered_ids, Listing.id == filtered_ids.c.id)
                .where(col.isnot(None))
                .group_by(literal_column("v"))
                .order_by(func.count().desc())
            )
            rows = (await db.execute(q)).all()
            buckets = [
                FacetBucket(value=(accessor(v) if accessor else v), count=int(c))
                for v, c in rows
                if v is not None and v != ""
            ]
            if buckets:
                result[response_key] = buckets
            continue

        # scalar_enum / scalar_int
        q = (
            select(col, func.count())
            .select_from(Listing)
            .join(filtered_ids, Listing.id == filtered_ids.c.id)
            .where(col.isnot(None))
            .group_by(col)
            .order_by(func.count().desc())
        )
        rows = (await db.execute(q)).all()
        buckets = [
            FacetBucket(
                value=(accessor(v) if accessor else v),
                count=int(c),
            )
            for v, c in rows
            if v is not None and v != ""
        ]
        if buckets:
            result[response_key] = buckets

    return result


@router.get(
    "/facets",
    response_model=FacetsResponse,
    response_model_exclude_none=True,
)
async def list_facets(
    request: Request,
    # ── Sprint 1 filters ─────────────────────────────────────────────
    q: Optional[str] = Query(None, max_length=200),
    type: Optional[str] = Query(None, pattern="^(sell|rent)$"),
    property_type: Optional[str] = Query(
        None, pattern="^(apartment|house|commercial|land)$"
    ),
    rooms: Optional[List[int]] = Query(None),
    price_min: Optional[int] = Query(None, ge=0),
    price_max: Optional[int] = Query(None, le=100000000),
    area_min: Optional[float] = Query(None, ge=0),
    area_max: Optional[float] = Query(None, le=100000),
    floor_min: Optional[int] = Query(None, ge=-5),
    floor_max: Optional[int] = Query(None, le=100),
    region: Optional[List[str]] = Query(None),
    district: Optional[List[str]] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|price|area|views_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    # ── Sprint 2 filters (T-018) ─────────────────────────────────────
    land_area_min: Optional[float] = Query(None, ge=0),
    land_area_max: Optional[float] = Query(None, le=100000),
    building_type: Optional[str] = Query(None, pattern="^(new|secondary)$"),
    condition: Optional[List[str]] = Query(None),
    furnished: Optional[bool] = Query(None),
    amenities: Optional[List[str]] = Query(None),
    nearby_amenities: Optional[List[str]] = Query(None),
    # A2 — house-specific filters (parity with GET /listings)
    house_type: Optional[str] = Query(None, max_length=50),
    house_condition: Optional[List[str]] = Query(None),
    water_supply: Optional[List[str]] = Query(None),
    rent_period: Optional[str] = Query(None, pattern="^(long_term|daily)$"),
    utilities_incl: Optional[bool] = Query(None),
    min_rent_months: Optional[List[int]] = Query(None),
    allowed_students: Optional[bool] = Query(None),
    allowed_pets: Optional[bool] = Query(None),
    rent_payment: Optional[List[str]] = Query(None),
    deposit_min: Optional[int] = Query(None, ge=0),
    deposit_max: Optional[int] = Query(None, ge=0),
    mortgage_ok: Optional[bool] = Query(None),
    installment_ok: Optional[bool] = Query(None),
    halol_ok: Optional[bool] = Query(None),
    deed_type: Optional[str] = Query(None, pattern="^(cadastre|order|other)$"),
    # ── Sprint 3–7 filters (parity with GET /listings) ──────────────
    urgent_flag: Optional[bool] = Query(None),
    city: Optional[str] = Query(None, max_length=100),
    microdistrict: Optional[str] = Query(None, max_length=200),
    jk_name: Optional[str] = Query(None, max_length=200),
    metro_station: Optional[str] = Query(None, max_length=50),
    commercial_type: Optional[str] = Query(
        None, pattern="^(office|shop|warehouse|production|restaurant|hotel|other)$"
    ),
    building_class: Optional[str] = Query(
        None, pattern="^(standalone|embedded|business_center|mall)$"
    ),
    entrance: Optional[str] = Query(None, pattern="^(separate|yard|street|mall)$"),
    parking_comm: Optional[bool] = Query(None),
    ceiling_height_min: Optional[float] = Query(None, gt=0, le=30),
    ceiling_height_max: Optional[float] = Query(None, gt=0, le=30),
    price_per_sqm_min: Optional[int] = Query(None, ge=0),
    price_per_sqm_max: Optional[int] = Query(None, ge=0),
    market_type: Optional[str] = Query(None, pattern="^(new|secondary)$"),
    wall_material: Optional[str] = Query(
        None, pattern="^(brick|gasblock|panel|monolith|other)$"
    ),
    furniture: Optional[str] = Query(None, pattern="^(none|partial|full|built_in)$"),
    garage: Optional[bool] = Query(None),
    basement: Optional[bool] = Query(None),
    buildings_exist: Optional[bool] = Query(None),
    fence: Optional[bool] = Query(None),
    land_shape: Optional[str] = Query(None, pattern="^(rectangular|irregular)$"),
    balcony: Optional[str] = Query(None, pattern="^(none|balcony|loggia|terrace)$"),
    listing_subtype: Optional[str] = Query(
        None, pattern="^(standard|studio|free_plan)$"
    ),
    jk_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """T-019 — filter-aware facet counts for the buyer-side sidebar.

    Accepts the same query params as GET /listings. Returns one bucket
    list per facet dimension that applies to the caller's (property_type,
    type) combo. Non-applicable facets are OMITTED from the response.

    Cached in Redis under `facets:{sha256(filters)}` for 60s. If Redis is
    unreachable we compute fresh (safe fallback) rather than 5xx-ing.
    """
    try:
        filters = ListingFilters(
            q=q,
            type=type,
            property_type=property_type,
            rooms=rooms,
            price_min=price_min,
            price_max=price_max,
            area_min=area_min,
            area_max=area_max,
            floor_min=floor_min,
            floor_max=floor_max,
            region=region,
            district=district,
            seller_id=None,
            source_type=None,
            sort_by=sort_by,
            sort_order=sort_order,
            land_area_min=land_area_min,
            land_area_max=land_area_max,
            building_type=building_type,
            condition=condition,
            furnished=furnished,
            amenities=amenities,
            nearby_amenities=nearby_amenities,
            house_type=house_type,
            house_condition=house_condition,
            water_supply=water_supply,
            rent_period=rent_period,
            utilities_incl=utilities_incl,
            min_rent_months=min_rent_months,
            allowed_students=allowed_students,
            allowed_pets=allowed_pets,
            rent_payment=rent_payment,
            deposit_min=deposit_min,
            deposit_max=deposit_max,
            mortgage_ok=mortgage_ok,
            installment_ok=installment_ok,
            halol_ok=halol_ok,
            deed_type=deed_type,
            urgent_flag=urgent_flag,
            city=city,
            microdistrict=microdistrict,
            jk_name=jk_name,
            metro_station=metro_station,
            commercial_type=commercial_type,
            building_class=building_class,
            entrance=entrance,
            parking_comm=parking_comm,
            ceiling_height_min=ceiling_height_min,
            ceiling_height_max=ceiling_height_max,
            price_per_sqm_min=price_per_sqm_min,
            price_per_sqm_max=price_per_sqm_max,
            market_type=market_type,
            wall_material=wall_material,
            furniture=furniture,
            garage=garage,
            basement=basement,
            buildings_exist=buildings_exist,
            fence=fence,
            land_shape=land_shape,
            balcony=balcony,
            listing_subtype=listing_subtype,
            jk_id=jk_id,
        )
    except ValueError as exc:
        raise BadRequestException(str(exc))

    cache_key = _facets_cache_key(filters)

    # ── Redis cache read (safe fallback) ────────────────────────────
    try:
        import json

        from app.db.redis import get_redis

        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return FacetsResponse(**json.loads(cached))
    except Exception as exc:
        # Never fail the request on Redis issues.
        logger.warning("facets cache read failed: %s", exc)

    # PR10 — route via search_router: Meili if the feature flag is on,
    # Postgres otherwise. Fallback to Postgres on any Meili error.
    async def _run_pg_facets(**kw):
        return await _compute_facets(kw["db_session"], kw["filters"])

    from app.services import search_router

    facets = await search_router.get_facets(
        filters=filters,
        db_session=db,
        postgres_runner=_run_pg_facets,
    )
    response = FacetsResponse(**facets)

    # ── Redis cache write (safe fallback) ───────────────────────────
    try:
        import json

        from app.db.redis import get_redis

        redis = await get_redis()
        payload = response.model_dump(mode="json", exclude_none=True)
        await redis.set(cache_key, json.dumps(payload), ex=60)
    except Exception as exc:
        logger.warning("facets cache write failed: %s", exc)

    return response


# =============================================================================
# Unified resolve & feed endpoints (must be above /{listing_id} catch-all)
# =============================================================================

LISTING_TYPE_MAP = {
    "sale": "sell",
    "daily_rent": "rent",
    "rent": "rent",
    "sell": "sell",
}
PROPERTY_TYPE_MAP = {"office": "commercial"}


def _normalize_type(val: str) -> str:
    return LISTING_TYPE_MAP.get(val, val)


def _normalize_property_type(val: str) -> str:
    return PROPERTY_TYPE_MAP.get(val, val)


def _normalize_crawler_images(images) -> List[UnifiedListingImage]:
    if not images:
        return []
    if isinstance(images, list):
        return [UnifiedListingImage(url=img) for img in images if isinstance(img, str)]
    return []


def _main_listing_to_unified(
    listing: Listing,
    is_favorited: bool = False,
    lang: str = "ru",
) -> UnifiedListingResponse:
    images = []
    if listing.images:
        for img in listing.images:
            images.append(
                UnifiedListingImage(
                    url=img.large_url or img.original_url,
                    thumbnail=img.thumbnail_url,
                )
            )

    return UnifiedListingResponse(
        source="main",
        id=listing.id,
        type=listing.type.value,
        property_type=listing.property_type.value,
        price=listing.price,
        currency=listing.currency.value,
        rooms=listing.rooms,
        area=listing.area,
        floor=listing.floor,
        total_floors=listing.total_floors,
        region=listing.region,
        district=listing.district,
        address=_resolve_field(listing, "address", lang),
        latitude=listing.latitude,
        longitude=listing.longitude,
        description=_resolve_field(listing, "description", lang),
        images=images,
        contact_phone=listing.phone,
        created_at=listing.created_at,
        title=_resolve_field(listing, "title", lang),
        views_count=listing.views_count or 0,
        favorites_count=listing.favorites_count or 0,
        comments_count=listing.comments_count or 0,
        is_favorited=is_favorited,
        is_boosted=listing.is_boosted or False,
        is_highlighted=listing.is_highlighted or False,
        seller_id=listing.seller_id,
        seller_name=(
            (
                listing.seller.company_name
                or (listing.seller.user.first_name if listing.seller.user else None)
            )
            if listing.seller
            else None
        ),
        seller_avatar_url=(
            (
                listing.seller.logo_url
                or (listing.seller.user.avatar_url if listing.seller.user else None)
            )
            if listing.seller
            else None
        ),
        seller_verified=listing.seller.is_verified if listing.seller else False,
        seller_type=listing.seller_type,
        seller_telegram=listing.seller_telegram,
        amenities=listing.amenities,
        building_type=listing.building_type,
        condition=listing.condition,
        land_purpose=listing.land_purpose,
        market_type=listing.market_type,
        wall_material=listing.wall_material,
        listing_subtype=listing.listing_subtype,
        balcony=listing.balcony,
        house_type=listing.house_type,
        house_condition=listing.house_condition,
        location_type=listing.location_type,
        living_area=listing.living_area,
        kitchen_area=listing.kitchen_area,
        land_area=listing.land_area,
        furniture=listing.furniture,
        is_furnished=listing.is_furnished,
        garage=listing.garage,
        basement=listing.basement,
        buildings_exist=listing.buildings_exist,
        fence=listing.fence,
        land_shape=listing.land_shape,
        ceiling_height=listing.ceiling_height,
        water_supply=listing.water_supply,
        electricity=listing.electricity,
        heating=listing.heating,
        gas_supply=listing.gas_supply,
        sewage=listing.sewage,
        commercial_type=listing.commercial_type,
        price_per_sqm=listing.price_per_sqm,
        entrance=listing.entrance,
        parking_comm=listing.parking_comm,
        building_class=listing.building_class,
        is_negotiable=listing.is_negotiable or False,
        deed_type=listing.deed_type,
        urgent_flag=listing.urgent_flag or False,
        rent_period=listing.rent_period,
        deposit=listing.deposit,
        utilities_incl=listing.utilities_incl,
        min_rent_months=listing.min_rent_months,
        allowed_students=listing.allowed_students,
        allowed_pets=listing.allowed_pets,
        rent_payment=listing.rent_payment,
        mortgage_ok=listing.mortgage_ok or False,
        installment_ok=listing.installment_ok or False,
        halol_ok=listing.halol_ok or False,
        city=listing.city,
        microdistrict=listing.microdistrict,
        jk_name=listing.jk_name,
        landmark=listing.landmark,
        metro_station=listing.metro_station,
        nearby_amenities=listing.nearby_amenities,
        original_language=listing.original_language,
        is_translated=_is_translated(listing, lang),
    )


def _telegram_listing_to_unified(
    listing: TelegramListing,
    is_favorited: bool = False,
    favorites_count: int = 0,
    lang: str = "ru",
) -> UnifiedListingResponse:
    return UnifiedListingResponse(
        source="telegram",
        id=listing.id,
        type=_normalize_type(listing.listing_type),
        property_type=_normalize_property_type(listing.property_type),
        price=listing.price,
        currency=listing.currency,
        rooms=listing.rooms,
        area=listing.area_sqm,
        floor=listing.floor,
        total_floors=listing.total_floors,
        district=listing.district,
        address=_resolve_field(listing, "address", lang),
        description=_resolve_field(listing, "description", lang),
        raw_text=listing.raw_text,
        images=_normalize_crawler_images(listing.images),
        contact_phone=listing.contact_phone,
        created_at=listing.created_at,
        amenities=listing.amenities,
        confidence=listing.confidence,
        source_url=listing.source_channel,
        seller_name=listing.source_channel,
        building_type=listing.building_type,
        condition=listing.condition,
        land_purpose=listing.land_purpose,
        favorites_count=favorites_count,
        is_favorited=is_favorited,
        original_language=listing.original_language,
        is_translated=_is_translated(listing, lang),
    )


def _olx_listing_to_unified(
    listing: OLXListing,
    is_favorited: bool = False,
    favorites_count: int = 0,
    lang: str = "ru",
) -> UnifiedListingResponse:
    return UnifiedListingResponse(
        source="olx",
        id=listing.id,
        type=_normalize_type(listing.listing_type),
        property_type=_normalize_property_type(listing.property_type),
        price=listing.price,
        currency=listing.currency,
        rooms=listing.rooms,
        area=listing.area_sqm,
        floor=listing.floor,
        total_floors=listing.total_floors,
        district=listing.district,
        address=_resolve_field(listing, "address", lang),
        description=_resolve_field(listing, "description", lang),
        raw_text=listing.raw_text,
        images=_normalize_crawler_images(listing.images),
        contact_phone=listing.contact_phone,
        created_at=listing.created_at,
        views_count=listing.views_count or 0,
        amenities=listing.amenities,
        confidence=listing.confidence,
        source_url=listing.url,
        seller_name=listing.seller_name,
        building_type=listing.building_type,
        condition=listing.condition,
        land_purpose=listing.land_purpose,
        favorites_count=favorites_count,
        is_favorited=is_favorited,
        original_language=listing.original_language,
        is_translated=_is_translated(listing, lang),
    )


@router.get("/resolve/{listing_id}", response_model=UnifiedListingResponse)
async def resolve_listing(
    request: Request,
    listing_id: UUID,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a listing by ID from any source (main, telegram, olx)."""
    lang = get_content_language(request)
    # Try main listings first
    main_res = await db.execute(
        select(Listing)
        .where(Listing.id == listing_id, Listing.deleted_at.is_(None))
        .options(
            selectinload(Listing.images),
            selectinload(Listing.seller).selectinload(Seller.user),
        )
    )
    main_listing = main_res.scalar_one_or_none()
    if main_listing:
        # Self-view guard: don't inflate a seller's own view counter.
        if not is_self_view(current_user, main_listing):
            main_listing.views_count = (main_listing.views_count or 0) + 1
            await db.commit()
            await db.refresh(main_listing)

        is_favorited = False
        if current_user:
            fav_result = await db.execute(
                select(Favorite).where(
                    Favorite.user_id == current_user.id,
                    Favorite.listing_id == listing_id,
                )
            )
            is_favorited = fav_result.scalar_one_or_none() is not None

        return _main_listing_to_unified(main_listing, is_favorited, lang=lang)

    # Check favorite status and count for crawler listings
    is_favorited = False
    if current_user:
        fav_result = await db.execute(
            select(Favorite).where(
                Favorite.user_id == current_user.id,
                Favorite.listing_id == listing_id,
            )
        )
        is_favorited = fav_result.scalar_one_or_none() is not None

    fav_count_result = await db.execute(
        select(func.count()).where(Favorite.listing_id == listing_id)
    )
    favorites_count = fav_count_result.scalar() or 0

    # Try telegram listings
    telegram_res = await db.execute(
        select(TelegramListing).where(TelegramListing.id == listing_id)
    )
    telegram_listing = telegram_res.scalar_one_or_none()
    if telegram_listing:
        return _telegram_listing_to_unified(
            telegram_listing, is_favorited, favorites_count, lang=lang
        )

    # Try OLX listings
    olx_res = await db.execute(select(OLXListing).where(OLXListing.id == listing_id))
    olx_listing = olx_res.scalar_one_or_none()
    if olx_listing:
        # If already claimed, resolve to the platform Listing instead
        if olx_listing.converted_listing_id:
            conv_res = await db.execute(
                select(Listing)
                .where(
                    Listing.id == olx_listing.converted_listing_id,
                    Listing.deleted_at.is_(None),
                )
                .options(
                    selectinload(Listing.images),
                    selectinload(Listing.seller).selectinload(Seller.user),
                )
            )
            conv_listing = conv_res.scalar_one_or_none()
            if conv_listing:
                conv_listing.views_count = (conv_listing.views_count or 0) + 1
                await db.commit()
                await db.refresh(conv_listing)
                return _main_listing_to_unified(conv_listing, is_favorited, lang=lang)
        return _olx_listing_to_unified(
            olx_listing, is_favorited, favorites_count, lang=lang
        )

    raise HTTPException(status_code=404, detail="Listing not found in any source")


def _jsonb_has_items(col):
    """SQL predicate: a JSONB column holds a non-empty array.

    MUST be a CASE expression: PostgreSQL does not guarantee evaluation
    order of AND operands, so a plain `jsonb_typeof(col) = 'array' AND
    jsonb_array_length(col) > 0` can still evaluate `jsonb_array_length`
    on rows where the column stores an object/scalar and abort the whole
    query with «cannot get array length of a non-array» (crawler rows
    have mixed image shapes). CASE branches are documented to evaluate
    lazily. NULL column → no branch matches → else False.
    """
    return case(
        (func.jsonb_typeof(col) == "array", func.jsonb_array_length(col) > 0),
        else_=False,
    )


@router.get("/feed", response_model=PaginatedResponse[UnifiedListingListItem])
async def listing_feed(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    exclude_id: Optional[UUID] = Query(None),
    q: Optional[str] = Query(None, max_length=200),
    type: Optional[List[Literal["sell", "rent"]]] = Query(None),
    property_type: Optional[
        List[Literal["apartment", "house", "commercial", "land"]]
    ] = Query(None),
    rooms: Optional[List[int]] = Query(None),
    price_min: Optional[int] = Query(None, ge=0),
    price_max: Optional[int] = Query(None, le=100000000),
    region: Optional[List[str]] = Query(None),
    district: Optional[List[str]] = Query(None),
    area_min: Optional[float] = Query(None, ge=0, le=100000),
    area_max: Optional[float] = Query(None, ge=0, le=100000),
    floor_min: Optional[int] = Query(None, ge=-5, le=100),
    floor_max: Optional[int] = Query(None, ge=-5, le=100),
    total_floors_min: Optional[int] = Query(None, ge=1, le=100),
    total_floors_max: Optional[int] = Query(None, ge=1, le=100),
    not_first_floor: bool = Query(False),
    not_last_floor: bool = Query(False),
    building_type: Optional[Literal["new", "secondary"]] = Query(None),
    condition: Optional[List[str]] = Query(None),
    has_photo: bool = Query(False),
    posted_within: Optional[int] = Query(None, ge=1, le=365),
    # Deal-terms filters — only the platform Listing table carries these
    # columns; crawler sources have no equivalent, so an active deal-terms
    # filter restricts the feed to platform listings (see below).
    mortgage_ok: bool = Query(False),
    installment_ok: bool = Query(False),
    halol_ok: bool = Query(False),
    furnished: bool = Query(False),
    allowed_pets: bool = Query(False),
    allowed_students: bool = Query(False),
    utilities_incl: bool = Query(False),
    rent_period: Optional[Literal["long_term", "daily"]] = Query(None),
    sort: Optional[str] = Query(None, pattern="^(newest|price_asc|price_desc)$"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Mixed feed from all listing sources with unified search/filter support.

    `sort` orders the merged feed: `newest` (created_at desc), `price_asc`,
    `price_desc` (listings without a price go last). Omitted → personalised
    relevance ranking (legacy behaviour).

    Wave-1 attribute filters (`area_*`, `floor_*`, `total_floors_*`,
    `not_first_floor`, `not_last_floor`, `building_type`, `condition`,
    `has_photo`, `posted_within`) are applied uniformly to all three
    sources. A row whose value for a filtered field is NULL (e.g. a
    crawled listing whose LLM extraction never captured the floor) is
    excluded by that filter — the result counter reflects the narrowing.
    `posted_within` counts days against `created_at`, which for crawled
    rows is the import time, not the original post date.
    """

    # Build base queries with filters
    main_query = select(Listing).where(
        Listing.status == ListingStatus.ACTIVE,
        Listing.moderation_status == ModerationStatus.APPROVED,
        Listing.deleted_at.is_(None),
    )
    tg_query = select(TelegramListing)
    olx_query = select(OLXListing).where(
        OLXListing.converted_listing_id.is_(None),
    )

    # Apply type filter (multi-value: the UI offers sell+rent chips)
    if type:
        main_query = main_query.where(Listing.type.in_(type))
        tg_query = tg_query.where(TelegramListing.listing_type.in_(type))
        olx_query = olx_query.where(OLXListing.listing_type.in_(type))

    # Apply property_type filter (multi-value)
    if property_type:
        main_query = main_query.where(Listing.property_type.in_(property_type))
        tg_query = tg_query.where(TelegramListing.property_type.in_(property_type))
        olx_query = olx_query.where(OLXListing.property_type.in_(property_type))

    # Apply rooms filter
    if rooms:
        main_query = main_query.where(Listing.rooms.in_(rooms))
        tg_query = tg_query.where(TelegramListing.rooms.in_(rooms))
        olx_query = olx_query.where(OLXListing.rooms.in_(rooms))

    # Apply price filter
    if price_min is not None:
        main_query = main_query.where(Listing.price >= price_min)
        tg_query = tg_query.where(TelegramListing.price >= price_min)
        olx_query = olx_query.where(OLXListing.price >= price_min)
    if price_max is not None:
        main_query = main_query.where(Listing.price <= price_max)
        tg_query = tg_query.where(TelegramListing.price <= price_max)
        olx_query = olx_query.where(OLXListing.price <= price_max)

    # Apply region filter
    if region:
        main_query = main_query.where(Listing.region.in_(region))
        tg_query = tg_query.where(TelegramListing.region.in_(region))
        olx_query = olx_query.where(OLXListing.region.in_(region))

    # Apply district filter
    if district:
        main_query = main_query.where(Listing.district.in_(district))
        tg_query = tg_query.where(TelegramListing.district.in_(district))
        olx_query = olx_query.where(OLXListing.district.in_(district))

    # ── Wave-1 attribute filters (apply to all three sources) ────────────
    # The platform stores area as `area`; crawler tables use `area_sqm`.
    if area_min is not None:
        main_query = main_query.where(Listing.area >= area_min)
        tg_query = tg_query.where(TelegramListing.area_sqm >= area_min)
        olx_query = olx_query.where(OLXListing.area_sqm >= area_min)
    if area_max is not None:
        main_query = main_query.where(Listing.area <= area_max)
        tg_query = tg_query.where(TelegramListing.area_sqm <= area_max)
        olx_query = olx_query.where(OLXListing.area_sqm <= area_max)

    # Apartment floor range
    if floor_min is not None:
        main_query = main_query.where(Listing.floor >= floor_min)
        tg_query = tg_query.where(TelegramListing.floor >= floor_min)
        olx_query = olx_query.where(OLXListing.floor >= floor_min)
    if floor_max is not None:
        main_query = main_query.where(Listing.floor <= floor_max)
        tg_query = tg_query.where(TelegramListing.floor <= floor_max)
        olx_query = olx_query.where(OLXListing.floor <= floor_max)

    # Building storeys range
    if total_floors_min is not None:
        main_query = main_query.where(Listing.total_floors >= total_floors_min)
        tg_query = tg_query.where(TelegramListing.total_floors >= total_floors_min)
        olx_query = olx_query.where(OLXListing.total_floors >= total_floors_min)
    if total_floors_max is not None:
        main_query = main_query.where(Listing.total_floors <= total_floors_max)
        tg_query = tg_query.where(TelegramListing.total_floors <= total_floors_max)
        olx_query = olx_query.where(OLXListing.total_floors <= total_floors_max)

    # "Not first floor" — floor must be known and not equal to 1.
    if not_first_floor:
        main_query = main_query.where(Listing.floor.isnot(None), Listing.floor != 1)
        tg_query = tg_query.where(
            TelegramListing.floor.isnot(None), TelegramListing.floor != 1
        )
        olx_query = olx_query.where(
            OLXListing.floor.isnot(None), OLXListing.floor != 1
        )

    # "Not last floor" — floor and total_floors known and floor != total_floors.
    if not_last_floor:
        main_query = main_query.where(
            Listing.floor.isnot(None),
            Listing.total_floors.isnot(None),
            Listing.floor != Listing.total_floors,
        )
        tg_query = tg_query.where(
            TelegramListing.floor.isnot(None),
            TelegramListing.total_floors.isnot(None),
            TelegramListing.floor != TelegramListing.total_floors,
        )
        olx_query = olx_query.where(
            OLXListing.floor.isnot(None),
            OLXListing.total_floors.isnot(None),
            OLXListing.floor != OLXListing.total_floors,
        )

    # New-build vs secondary. Crawler values are LLM free-text, so only rows
    # whose value happens to be canonical ("new"/"secondary") match.
    if building_type:
        main_query = main_query.where(Listing.building_type == building_type)
        tg_query = tg_query.where(TelegramListing.building_type == building_type)
        olx_query = olx_query.where(OLXListing.building_type == building_type)

    # Renovation/condition (multi-select OR-match via IN).
    if condition:
        main_query = main_query.where(Listing.condition.in_(condition))
        tg_query = tg_query.where(TelegramListing.condition.in_(condition))
        olx_query = olx_query.where(OLXListing.condition.in_(condition))

    # Only listings that have at least one photo. Platform images live in a
    # related table; crawler images are a JSONB array.
    if has_photo:
        main_query = main_query.where(Listing.images.any())
        tg_query = tg_query.where(_jsonb_has_items(TelegramListing.images))
        olx_query = olx_query.where(_jsonb_has_items(OLXListing.images))

    # Freshness window against created_at (import time for crawled rows).
    if posted_within:
        cutoff = datetime.utcnow() - timedelta(days=posted_within)
        main_query = main_query.where(Listing.created_at >= cutoff)
        tg_query = tg_query.where(TelegramListing.created_at >= cutoff)
        olx_query = olx_query.where(OLXListing.created_at >= cutoff)

    # ── Deal-terms filters (platform-only) ───────────────────────────────
    # These columns exist only on the platform Listing table. A crawler
    # listing can never be *confirmed* to offer e.g. a mortgage, so when any
    # deal-terms filter is active we restrict the feed to platform listings
    # (the crawler queries are short-circuited to empty). The live result
    # counter reflects this narrowing.
    if mortgage_ok:
        main_query = main_query.where(Listing.mortgage_ok.is_(True))
    if installment_ok:
        main_query = main_query.where(Listing.installment_ok.is_(True))
    if halol_ok:
        main_query = main_query.where(Listing.halol_ok.is_(True))
    if furnished:
        # Canonical "has furniture" — the seller form writes `furniture`
        # (none/partial/full/built_in), not the legacy is_furnished boolean.
        main_query = main_query.where(
            Listing.furniture.in_(["partial", "full", "built_in"])
        )
    if allowed_pets:
        main_query = main_query.where(Listing.allowed_pets.is_(True))
    if allowed_students:
        main_query = main_query.where(Listing.allowed_students.is_(True))
    if utilities_incl:
        main_query = main_query.where(Listing.utilities_incl.is_(True))
    if rent_period:
        main_query = main_query.where(Listing.rent_period == rent_period)

    deal_terms_active = any(
        [
            mortgage_ok,
            installment_ok,
            halol_ok,
            furnished,
            allowed_pets,
            allowed_students,
            utilities_incl,
            rent_period,
        ]
    )
    if deal_terms_active:
        tg_query = tg_query.where(false())
        olx_query = olx_query.where(false())

    # Apply text search
    if q:
        search_term = f"%{q}%"
        main_query = main_query.where(
            or_(
                Listing.title.ilike(search_term),
                Listing.description.ilike(search_term),
                Listing.district.ilike(search_term),
                Listing.address.ilike(search_term),
            )
        )
        tg_query = tg_query.where(
            or_(
                TelegramListing.description.ilike(search_term),
                TelegramListing.district.ilike(search_term),
                TelegramListing.address.ilike(search_term),
                TelegramListing.raw_text.ilike(search_term),
            )
        )
        olx_query = olx_query.where(
            or_(
                OLXListing.description.ilike(search_term),
                OLXListing.district.ilike(search_term),
                OLXListing.address.ilike(search_term),
                OLXListing.raw_text.ilike(search_term),
            )
        )

    # Count totals from each table with filters
    main_count_res = await db.execute(
        select(func.count()).select_from(main_query.subquery())
    )
    tg_count_res = await db.execute(
        select(func.count()).select_from(tg_query.subquery())
    )
    olx_count_res = await db.execute(
        select(func.count()).select_from(olx_query.subquery())
    )
    total = (
        (main_count_res.scalar() or 0)
        + (tg_count_res.scalar() or 0)
        + (olx_count_res.scalar() or 0)
    )

    # Fetch enough items from each table to fill the page after sorting.
    # Each per-source window MUST be ordered by the same key as the final
    # merge sort — otherwise the global top of a price sort may fall outside
    # a created_at-ordered window and silently disappear from the page.
    fetch_limit = per_page * page  # fetch enough for offset + page

    if sort == "price_asc":
        main_order = Listing.price.asc().nulls_last()
        tg_order = TelegramListing.price.asc().nulls_last()
        olx_order = OLXListing.price.asc().nulls_last()
    elif sort == "price_desc":
        main_order = Listing.price.desc().nulls_last()
        tg_order = TelegramListing.price.desc().nulls_last()
        olx_order = OLXListing.price.desc().nulls_last()
    else:  # "newest" and the default relevance ranking both window by recency
        main_order = Listing.created_at.desc()
        tg_order = TelegramListing.created_at.desc()
        olx_order = OLXListing.created_at.desc()

    main_res = await db.execute(
        main_query.options(selectinload(Listing.images))
        .order_by(main_order)
        .limit(fetch_limit)
    )
    tg_res = await db.execute(tg_query.order_by(tg_order).limit(fetch_limit))
    olx_res = await db.execute(olx_query.order_by(olx_order).limit(fetch_limit))

    # Build unified list items
    items: List[UnifiedListingListItem] = []

    for listing in main_res.scalars().all():
        if exclude_id and listing.id == exclude_id:
            continue
        primary_image = next(
            (img for img in listing.images if img.is_primary),
            listing.images[0] if listing.images else None,
        )
        items.append(
            UnifiedListingListItem(
                id=listing.id,
                source="main",
                type=listing.type.value,
                property_type=listing.property_type.value,
                price=listing.price,
                currency=listing.currency.value,
                rooms=listing.rooms,
                area=listing.area,
                floor=listing.floor,
                total_floors=listing.total_floors,
                region=listing.region,
                district=listing.district,
                building_type=listing.building_type,
                condition=listing.condition,
                land_purpose=listing.land_purpose,
                primary_image_url=primary_image.medium_url if primary_image else None,
                created_at=listing.created_at,
            )
        )

    for listing in tg_res.scalars().all():
        if exclude_id and listing.id == exclude_id:
            continue
        first_img = (
            listing.images[0]
            if listing.images and isinstance(listing.images, list)
            else None
        )
        items.append(
            UnifiedListingListItem(
                id=listing.id,
                source="telegram",
                type=_normalize_type(listing.listing_type),
                property_type=_normalize_property_type(listing.property_type),
                price=listing.price,
                currency=listing.currency,
                rooms=listing.rooms,
                area=listing.area_sqm,
                floor=listing.floor,
                total_floors=listing.total_floors,
                region=listing.region,
                district=listing.district,
                building_type=listing.building_type,
                condition=listing.condition,
                land_purpose=listing.land_purpose,
                primary_image_url=first_img if isinstance(first_img, str) else None,
                created_at=listing.created_at,
            )
        )

    for listing in olx_res.scalars().all():
        if exclude_id and listing.id == exclude_id:
            continue
        first_img = (
            listing.images[0]
            if listing.images and isinstance(listing.images, list)
            else None
        )
        items.append(
            UnifiedListingListItem(
                id=listing.id,
                source="olx",
                type=_normalize_type(listing.listing_type),
                property_type=_normalize_property_type(listing.property_type),
                price=listing.price,
                currency=listing.currency,
                rooms=listing.rooms,
                area=listing.area_sqm,
                floor=listing.floor,
                total_floors=listing.total_floors,
                region=listing.region,
                district=listing.district,
                building_type=listing.building_type,
                condition=listing.condition,
                land_purpose=listing.land_purpose,
                primary_image_url=first_img if isinstance(first_img, str) else None,
                created_at=listing.created_at,
            )
        )

    # Load user preferences and exchange rate for ranking (if authenticated).
    # Skipped for explicit sorts — relevance scoring is not used there.
    prefs = None
    usd_uzs_rate = 0.0
    if current_user and sort is None:
        prefs_result = await db.execute(
            select(UserPreferences).where(UserPreferences.user_id == current_user.id)
        )
        prefs = prefs_result.scalar_one_or_none()
        if prefs and (prefs.price_min is not None or prefs.price_max is not None):
            from app.utils.price import get_usd_uzs_rate

            usd_uzs_rate = await get_usd_uzs_rate()

    def _relevance_score(item: UnifiedListingListItem) -> int:
        if not prefs:
            return 0
        score = 0
        if prefs.regions and item.region and item.region in prefs.regions:
            score += 1
        if prefs.districts and item.district and item.district in prefs.districts:
            score += 2  # district is more specific
        if (
            prefs.property_types
            and item.property_type
            and item.property_type in prefs.property_types
        ):
            score += 1
        if prefs.listing_types and item.type and item.type in prefs.listing_types:
            score += 1
        if prefs.rooms and item.rooms and item.rooms in prefs.rooms:
            score += 1
        if item.price and (prefs.price_min is not None or prefs.price_max is not None):
            from app.utils.price import normalize_price_to_usd

            price_usd = normalize_price_to_usd(item.price, item.currency, usd_uzs_rate)
            if price_usd is not None:
                in_range = True
                if prefs.price_min is not None and price_usd < prefs.price_min:
                    in_range = False
                if prefs.price_max is not None and price_usd > prefs.price_max:
                    in_range = False
                if in_range:
                    score += 1
        return score

    # Order the merged list. Explicit sorts mirror the per-source SQL order;
    # the default remains relevance DESC, then created_at DESC. Items without
    # a price sink to the bottom of both price sorts.
    if sort == "newest":
        items.sort(key=lambda x: -x.created_at.timestamp())
    elif sort == "price_asc":
        items.sort(
            key=lambda x: (
                x.price is None,
                float(x.price) if x.price is not None else 0.0,
                -x.created_at.timestamp(),
            )
        )
    elif sort == "price_desc":
        items.sort(
            key=lambda x: (
                x.price is None,
                -float(x.price) if x.price is not None else 0.0,
                -x.created_at.timestamp(),
            )
        )
    else:
        items.sort(key=lambda x: (-_relevance_score(x), -x.created_at.timestamp()))

    # Paginate
    offset = (page - 1) * per_page
    page_items = items[offset : offset + per_page]

    return PaginatedResponse.create(
        items=page_items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/claim-olx/{olx_listing_id}", response_model=ListingResponse, status_code=201
)
async def claim_olx_listing(
    olx_listing_id: UUID,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """Claim an OLX listing by converting it into a platform Listing owned by the seller.

    Returns 201 with the new Listing on success.
    Returns 403 if phone doesn't match or OLX listing has no phone.
    Returns 404 if OLX listing not found.
    Returns 409 if already claimed (returns the existing converted Listing).
    Returns 429 if daily claim limit (5) exceeded.
    """
    from app.utils.phone import normalize_phone_e164

    # Rate limit: max 5 claims per seller per 24h
    cutoff = datetime.utcnow() - timedelta(hours=24)
    count_q = select(func.count()).select_from(
        select(OLXListing.id)
        .where(
            OLXListing.converted_listing_id.isnot(None),
        )
        .join(
            Listing,
            Listing.id == OLXListing.converted_listing_id,
        )
        .where(
            Listing.seller_id == seller.id,
            Listing.created_at >= cutoff,
        )
        .subquery()
    )
    claimed_today = (await db.execute(count_q)).scalar() or 0
    if claimed_today >= 5:
        raise HTTPException(
            status_code=429,
            detail="Daily claim limit reached (5 per 24 hours)",
        )

    # Lock the OLX listing row for update
    olx_q = select(OLXListing).where(OLXListing.id == olx_listing_id).with_for_update()
    olx_result = await db.execute(olx_q)
    olx = olx_result.scalar_one_or_none()

    if not olx:
        raise HTTPException(status_code=404, detail="OLX listing not found")

    # Phone ownership validation: OLX listing must have a phone
    olx_phone = normalize_phone_e164(olx.contact_phone)
    if not olx_phone:
        raise HTTPException(
            status_code=403,
            detail="Cannot claim: OLX listing has no contact phone",
        )

    # Phone ownership validation: seller phone must match OLX phone exactly
    seller_phone = normalize_phone_e164(seller.phone)
    if not seller_phone or seller_phone != olx_phone:
        raise HTTPException(
            status_code=403,
            detail="Cannot claim: your phone does not match the listing contact phone",
        )

    # Already claimed? Return 409 with the existing listing
    if olx.converted_listing_id:
        existing_q = (
            select(Listing)
            .where(Listing.id == olx.converted_listing_id, Listing.deleted_at.is_(None))
            .options(selectinload(Listing.images))
        )
        existing_res = await db.execute(existing_q)
        existing = existing_res.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=409,
                detail="This OLX listing has already been claimed",
            )
        # Self-healing: converted listing was deleted, allow re-claim
        olx.converted_listing_id = None

    # Convert
    listing = await convert_olx_to_listing(olx, seller, db)

    # Audit log
    db.add(
        AuditLog(
            user_id=seller.user_id,
            entity_type="olx_listing",
            entity_id=olx.id,
            action="claim_olx",
            new_values={"converted_listing_id": str(listing.id)},
        )
    )

    # FIX — invariant: every write path normalizes through the matrix.
    # OLX-imported rows can carry stale fields (e.g. mortgage_ok=true on a
    # rental); without this call they would land in the listings table
    # post-claim. Mirrors the create/update endpoints.
    _clear_incompatible_fields(listing)

    await db.commit()

    # PR8 — index the newly claimed (auto-approved) listing. Optional.
    try:
        from app.services.search_index import index_listing as _mx_index

        _mx_index(listing)
    except Exception as exc:
        logger.warning("meili index (claim-olx) failed: %s", exc)

    # Drop the now-claimed crawled row from the index so bot search
    # doesn't surface it as a duplicate of the native listing above.
    try:
        from app.services.search_index import delete_listing as _mx_delete

        _mx_delete(olx_listing_id)
    except Exception as exc:
        logger.warning("meili delete (claim-olx crawled) failed: %s", exc)

    # Trigger notifications for the newly claimed (auto-approved) listing.
    # Dispatched via Celery .delay() so the API responds immediately;
    # matching + Telegram delivery happens asynchronously in the worker.
    from app.workers.tasks.notifications import send_new_listing_notifications

    send_new_listing_notifications.delay(str(listing.id))

    # Block A V2.0 (A1 + A7) — flip the freshly claimed listing into
    # PENDING_GENERATION and enqueue F1. The realtor's raw_text was
    # carried over by convert_olx_to_listing so AI has context.
    try:
        from app.workers.tasks.ai_generation import generate_listing_description

        listing.status = ListingStatus.PENDING_GENERATION
        await db.commit()
        generate_listing_description.delay(str(listing.id))
    except Exception as exc:
        logger.warning("F1 enqueue (claim-olx) failed: %s", exc)

    # Reload with images
    reload_q = (
        select(Listing)
        .where(Listing.id == listing.id)
        .options(selectinload(Listing.images))
    )
    listing = (await db.execute(reload_q)).scalar_one()

    logger.info(
        "OLX listing %s claimed by seller %s → listing %s",
        olx_listing_id,
        seller.id,
        listing.id,
    )

    images_list = [
        ListingImageResponse(
            id=img.id,
            original_url=img.original_url,
            thumbnail_url=img.thumbnail_url,
            medium_url=img.medium_url,
            large_url=img.large_url,
            position=img.position,
            is_primary=img.is_primary,
        )
        for img in listing.images
    ]

    return ListingResponse(
        id=listing.id,
        seller_id=listing.seller_id,
        type=listing.type.value,
        property_type=listing.property_type.value,
        rooms=listing.rooms,
        area=listing.area,
        floor=listing.floor,
        total_floors=listing.total_floors,
        region=listing.region,
        district=listing.district,
        address=listing.address,
        latitude=listing.latitude,
        longitude=listing.longitude,
        price=listing.price,
        currency=listing.currency.value,
        title=listing.title,
        description=listing.description,
        phone=listing.phone,
        seller_type=listing.seller_type,
        living_area=listing.living_area,
        kitchen_area=listing.kitchen_area,
        land_area=listing.land_area,
        condition=listing.condition,
        house_type=listing.house_type,
        house_condition=listing.house_condition,
        location_type=listing.location_type,
        water_supply=listing.water_supply,
        electricity=listing.electricity,
        heating=listing.heating,
        gas_supply=listing.gas_supply,
        sewage=listing.sewage,
        is_negotiable=listing.is_negotiable,
        land_purpose=listing.land_purpose,
        amenities=listing.amenities,
        nearby_amenities=listing.nearby_amenities,
        rent_period=listing.rent_period,
        deposit=listing.deposit,
        utilities_incl=listing.utilities_incl,
        min_rent_months=listing.min_rent_months,
        allowed_students=listing.allowed_students,
        allowed_pets=listing.allowed_pets,
        rent_payment=listing.rent_payment,
        mortgage_ok=listing.mortgage_ok,
        installment_ok=listing.installment_ok,
        halol_ok=listing.halol_ok,
        deed_type=listing.deed_type,
        source_type=listing.source_type.value,
        status=listing.status.value,
        moderation_status=listing.moderation_status.value,
        views_count=listing.views_count,
        contacts_count=listing.contacts_count,
        favorites_count=listing.favorites_count,
        is_boosted=listing.is_boosted,
        boost_until=listing.boost_until,
        is_highlighted=listing.is_highlighted,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        expires_at=listing.expires_at,
        images=images_list,
        # S3–S8 fields + S5 dual-read mirrors.
        **_build_full_response_kwargs(listing),
    )


@router.post("/claim-telegram/{tg_listing_id}", status_code=201)
async def claim_telegram_listing(
    tg_listing_id: UUID,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """Claim a Telegram-crawled listing by converting it into a platform Listing.

    Returns 403 if phone doesn't match the Telegram listing contact.
    Returns 404 if not found. 409 if already claimed. 429 on daily limit.
    """
    from app.utils.phone import normalize_phone_e164

    cutoff = datetime.utcnow() - timedelta(hours=24)
    count_q = select(func.count()).select_from(
        select(TelegramListing.id)
        .where(TelegramListing.converted_listing_id.isnot(None))
        .join(Listing, Listing.id == TelegramListing.converted_listing_id)
        .where(Listing.seller_id == seller.id, Listing.created_at >= cutoff)
        .subquery()
    )
    claimed_today = (await db.execute(count_q)).scalar() or 0
    if claimed_today >= 5:
        raise HTTPException(
            status_code=429,
            detail="Daily claim limit reached (5 per 24 hours)",
        )

    tg_q = (
        select(TelegramListing)
        .where(TelegramListing.id == tg_listing_id)
        .with_for_update()
    )
    tg = (await db.execute(tg_q)).scalar_one_or_none()

    if not tg:
        raise HTTPException(status_code=404, detail="Telegram listing not found")

    tg_phone = normalize_phone_e164(tg.contact_phone)
    seller_phone = normalize_phone_e164(seller.phone)
    if not tg_phone or not seller_phone or tg_phone != seller_phone:
        raise HTTPException(
            status_code=403,
            detail="Cannot claim: your phone does not match the listing contact phone",
        )

    if tg.converted_listing_id:
        existing = (
            await db.execute(
                select(Listing).where(
                    Listing.id == tg.converted_listing_id,
                    Listing.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=409,
                detail="This Telegram listing has already been claimed",
            )
        tg.converted_listing_id = None

    listing = await convert_telegram_to_listing(tg, seller, db)

    db.add(
        AuditLog(
            user_id=seller.user_id,
            entity_type="telegram_listing",
            entity_id=tg.id,
            action="claim_telegram",
            new_values={"converted_listing_id": str(listing.id)},
        )
    )

    _clear_incompatible_fields(listing)

    await db.commit()

    try:
        from app.services.search_index import index_listing as _mx_index

        _mx_index(listing)
    except Exception as exc:
        logger.warning("meili index (claim-telegram) failed: %s", exc)

    # Drop the now-claimed crawled row from the index so bot search
    # doesn't surface it as a duplicate of the native listing above.
    try:
        from app.services.search_index import delete_listing as _mx_delete

        _mx_delete(tg_listing_id)
    except Exception as exc:
        logger.warning("meili delete (claim-telegram crawled) failed: %s", exc)

    from app.workers.tasks.notifications import send_new_listing_notifications

    send_new_listing_notifications.delay(str(listing.id))

    # Block A V2.0 (A1 + A7) — F1 enqueue, mirrors claim-olx.
    try:
        from app.workers.tasks.ai_generation import generate_listing_description

        listing.status = ListingStatus.PENDING_GENERATION
        await db.commit()
        generate_listing_description.delay(str(listing.id))
    except Exception as exc:
        logger.warning("F1 enqueue (claim-telegram) failed: %s", exc)

    logger.info(
        "Telegram listing %s claimed by seller %s → listing %s",
        tg_listing_id,
        seller.id,
        listing.id,
    )

    return {"listing_id": str(listing.id), "status": "claimed"}


@router.post("/reject-crawled/{source}/{crawled_id}", status_code=200)
async def reject_crawled_listing(
    source: str,
    crawled_id: UUID,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """Mark a crawled listing as "not mine" so it disappears from the seller's feed.

    source ∈ {"olx", "telegram"}.
    """
    if source == "olx":
        model = OLXListing
    elif source == "telegram":
        model = TelegramListing
    else:
        raise HTTPException(
            status_code=400, detail="source must be 'olx' or 'telegram'"
        )

    row = (
        await db.execute(select(model).where(model.id == crawled_id).with_for_update())
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail=f"{source} listing not found")

    if row.converted_listing_id:
        raise HTTPException(
            status_code=400, detail="Cannot reject an already-claimed listing"
        )

    row.rejected_by_seller_id = seller.id
    row.rejected_at = datetime.utcnow()

    db.add(
        AuditLog(
            user_id=seller.user_id,
            entity_type=f"{source}_listing",
            entity_id=row.id,
            action=f"reject_{source}",
            new_values={"rejected_by_seller_id": str(seller.id)},
        )
    )

    await db.commit()
    return {"status": "rejected"}


@router.get("/{listing_id}", response_model=ListingResponse)
async def get_listing(
    request: Request,
    listing_id: UUID,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Get listing detail by ID.

    Returns full listing information including all images.
    Increments view count.
    """
    query = (
        select(Listing)
        .where(Listing.id == listing_id, Listing.deleted_at.is_(None))
        .options(selectinload(Listing.images))
    )
    result = await db.execute(query)
    listing = result.scalar_one_or_none()

    if not listing:
        raise NotFoundException("Listing", str(listing_id))

    # Increment view count
    listing.views_count += 1
    await db.commit()
    await db.refresh(listing)

    # Check if favorited by current user
    is_favorited = False
    if current_user:
        fav_result = await db.execute(
            select(Favorite).where(
                Favorite.user_id == current_user.id,
                Favorite.listing_id == listing_id,
            )
        )
        is_favorited = fav_result.scalar_one_or_none() is not None

    # Build images list safely
    images_list = []
    if listing.images:
        for img in listing.images:
            images_list.append(
                ListingImageResponse(
                    id=img.id,
                    original_url=img.original_url,
                    thumbnail_url=img.thumbnail_url,
                    medium_url=img.medium_url,
                    large_url=img.large_url,
                    position=img.position,
                    is_primary=img.is_primary,
                )
            )

    # Build response
    lang = get_content_language(request)
    response = ListingResponse(
        id=listing.id,
        seller_id=listing.seller_id,
        type=listing.type.value,
        property_type=listing.property_type.value,
        rooms=listing.rooms,
        area=listing.area,
        floor=listing.floor,
        total_floors=listing.total_floors,
        region=listing.region,
        district=listing.district,
        address=_resolve_field(listing, "address", lang),
        latitude=listing.latitude,
        longitude=listing.longitude,
        price=listing.price,
        currency=listing.currency.value,
        title=_resolve_field(listing, "title", lang),
        description=_resolve_field(listing, "description", lang),
        phone=listing.phone,
        seller_type=listing.seller_type,
        living_area=listing.living_area,
        kitchen_area=listing.kitchen_area,
        land_area=listing.land_area,
        condition=listing.condition,
        house_type=listing.house_type,
        house_condition=listing.house_condition,
        location_type=listing.location_type,
        water_supply=listing.water_supply,
        electricity=listing.electricity,
        heating=listing.heating,
        gas_supply=listing.gas_supply,
        sewage=listing.sewage,
        is_negotiable=listing.is_negotiable,
        land_purpose=listing.land_purpose,
        amenities=listing.amenities,
        nearby_amenities=listing.nearby_amenities,
        rent_period=listing.rent_period,
        deposit=listing.deposit,
        utilities_incl=listing.utilities_incl,
        min_rent_months=listing.min_rent_months,
        allowed_students=listing.allowed_students,
        allowed_pets=listing.allowed_pets,
        rent_payment=listing.rent_payment,
        mortgage_ok=listing.mortgage_ok,
        installment_ok=listing.installment_ok,
        halol_ok=listing.halol_ok,
        deed_type=listing.deed_type,
        source_type=listing.source_type.value,
        status=listing.status.value,
        moderation_status=listing.moderation_status.value,
        views_count=listing.views_count or 0,
        contacts_count=listing.contacts_count or 0,
        favorites_count=listing.favorites_count or 0,
        comments_count=listing.comments_count or 0,
        is_boosted=listing.is_boosted or False,
        boost_until=listing.boost_until,
        is_highlighted=listing.is_highlighted or False,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        expires_at=listing.expires_at,
        images=images_list,
        is_favorited=is_favorited,
        original_language=listing.original_language,
        is_translated=_is_translated(listing, lang),
        # S3–S8 fields + S5 dual-read mirrors.
        **_build_full_response_kwargs(listing),
    )

    return response


@router.post("", response_model=ListingResponse, status_code=201)
async def create_listing(
    data: ListingCreate,
    request: Request,
    # Block C V2.0 (C2): check_can_create_listing replaces
    # get_current_seller; behaviour identical during test period
    # (settings.test_period_active=true), enforces quota afterwards.
    seller: Seller = Depends(check_can_create_listing),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new listing.

    Only authenticated sellers can create listings.
    Listings start in 'pending' moderation status.

    During test period: no quota enforcement.
    After test period: rejects with 402 if seller is over the free
    limit (per Block C V2.0 / C2 grandfathering policy).
    """
    from app.db.models import Currency, ListingType, PropertyType, SourceType

    # Sprint 5 dual-read: accept either the old name (building_type /
    # is_furnished) or the new name (market_type / furniture). Conflicts raise
    # BadRequestException. After this, only the new-name fields are
    # authoritative; we still also pass `building_type` / `is_furnished` so
    # the legacy columns stay in sync during the dual-read window.
    _dual = _apply_dual_read_inputs(data.model_dump(exclude_unset=True))
    data.market_type = _dual.get("market_type", data.market_type)
    data.furniture = _dual.get("furniture", data.furniture)

    listing = Listing(
        seller_id=seller.id,
        type=ListingType(data.type),
        property_type=PropertyType(data.property_type),
        rooms=data.rooms,
        area=data.area,
        floor=data.floor,
        total_floors=data.total_floors,
        region=data.region,
        district=data.district,
        address=data.address,
        latitude=data.latitude,
        longitude=data.longitude,
        price=data.price,
        currency=Currency(data.currency),
        title=data.title,
        description=data.description,
        phone=data.phone or seller.phone,
        seller_type=data.seller_type,
        source_type=SourceType.MANUAL,
        moderation_status=ModerationStatus.APPROVED,
        # Phase 2 fields
        living_area=data.living_area,
        kitchen_area=data.kitchen_area,
        land_area=data.land_area,
        building_type=data.building_type,
        condition=data.condition,
        house_type=data.house_type,
        house_condition=data.house_condition,
        location_type=data.location_type,
        water_supply=data.water_supply,
        electricity=data.electricity,
        heating=data.heating,
        gas_supply=data.gas_supply,
        sewage=data.sewage,
        is_furnished=data.is_furnished,
        is_negotiable=data.is_negotiable,
        land_purpose=data.land_purpose,
        amenities=data.amenities,
        nearby_amenities=data.nearby_amenities,
        # Sprint 2 — rent fields (matrix-gated by _clear_incompatible_fields)
        rent_period=data.rent_period,
        deposit=data.deposit,
        utilities_incl=data.utilities_incl,
        min_rent_months=data.min_rent_months,
        allowed_students=data.allowed_students,
        allowed_pets=data.allowed_pets,
        rent_payment=data.rent_payment,
        # Sprint 2 — sale finance + deed (matrix-gated by _clear_incompatible_fields)
        mortgage_ok=data.mortgage_ok,
        installment_ok=data.installment_ok,
        halol_ok=data.halol_ok,
        deed_type=data.deed_type,
        # Sprint 3 — location extensions
        urgent_flag=data.urgent_flag,
        city=data.city,
        microdistrict=data.microdistrict,
        jk_name=data.jk_name,
        landmark=data.landmark,
        metro_station=data.metro_station,
        seller_telegram=data.seller_telegram,
        # Sprint 4 — commercial
        commercial_type=data.commercial_type,
        price_per_sqm=data.price_per_sqm,
        ceiling_height=data.ceiling_height,
        entrance=data.entrance,
        parking_comm=data.parking_comm,
        building_class=data.building_class,
        # Sprint 5 — dual-read new columns
        market_type=data.market_type,
        wall_material=data.wall_material,
        furniture=data.furniture,
        # Sprint 6 — property polish
        garage=data.garage,
        basement=data.basement,
        buildings_exist=data.buildings_exist,
        fence=data.fence,
        land_shape=data.land_shape,
        balcony=data.balcony,
        listing_subtype=data.listing_subtype,
        floor_plan_url=data.floor_plan_url,
        # Sprint 7 — housing complex linkage
        jk_id=data.jk_id,
    )

    # Enforce visibility matrix: wipe fields incompatible with this listing's
    # (property_type, deal_type).
    # Runs BEFORE required-field validation so cleared fields don't trip it.
    _clear_incompatible_fields(listing)

    # Validate required fields (mirrors frontend rules)
    _validate_required_fields(listing)

    # Detect language and populate _lang columns for translation
    _populate_listing_lang_columns(listing)

    db.add(listing)
    await db.flush()  # Get the listing ID before creating images

    # Create listing images if provided
    if data.images:
        for idx, img_data in enumerate(data.images):
            listing_image = ListingImage(
                listing_id=listing.id,
                original_url=img_data.original_url,
                thumbnail_url=img_data.thumbnail_url,
                medium_url=img_data.medium_url,
                large_url=img_data.large_url,
                position=img_data.position if img_data.position else idx,
                is_primary=img_data.is_primary if img_data.is_primary else (idx == 0),
                upload_status="completed",
            )
            db.add(listing_image)

    # Update seller listings count
    seller.listings_count += 1

    await db.commit()

    # PR8 — Meilisearch index is ADDITIVE. Postgres stays source of truth;
    # indexing failures must never poison the write.
    try:
        from app.services.search_index import index_listing as _mx_index

        _mx_index(listing)
    except Exception as exc:
        logger.warning("meili index (create) failed: %s", exc)

    # Trigger notifications for the new listing.
    # Dispatched via Celery .delay() so the API responds immediately.
    from app.workers.tasks.notifications import send_new_listing_notifications

    send_new_listing_notifications.delay(str(listing.id))

    # Block D D4 — autopost a fresh ACTIVE listing to the seller's
    # channel (if connected). Listings in PENDING_GENERATION wait
    # for the F1 worker, which calls _enqueue_autopost on completion.
    if listing.status == ListingStatus.ACTIVE:
        _dispatch_autopost_for_status_change(seller, listing, None)

    # Reload listing with images
    query = (
        select(Listing)
        .where(Listing.id == listing.id)
        .options(selectinload(Listing.images))
    )
    result = await db.execute(query)
    listing = result.scalar_one()

    # Build images list
    images_list = [
        ListingImageResponse(
            id=img.id,
            original_url=img.original_url,
            thumbnail_url=img.thumbnail_url,
            medium_url=img.medium_url,
            large_url=img.large_url,
            position=img.position,
            is_primary=img.is_primary,
        )
        for img in listing.images
    ]

    lang = get_content_language(request)
    return ListingResponse(
        id=listing.id,
        seller_id=listing.seller_id,
        type=listing.type.value,
        property_type=listing.property_type.value,
        rooms=listing.rooms,
        area=listing.area,
        floor=listing.floor,
        total_floors=listing.total_floors,
        region=listing.region,
        district=listing.district,
        address=_resolve_field(listing, "address", lang),
        latitude=listing.latitude,
        longitude=listing.longitude,
        price=listing.price,
        currency=listing.currency.value,
        title=_resolve_field(listing, "title", lang),
        description=_resolve_field(listing, "description", lang),
        phone=listing.phone,
        seller_type=listing.seller_type,
        living_area=listing.living_area,
        kitchen_area=listing.kitchen_area,
        land_area=listing.land_area,
        condition=listing.condition,
        house_type=listing.house_type,
        house_condition=listing.house_condition,
        location_type=listing.location_type,
        water_supply=listing.water_supply,
        electricity=listing.electricity,
        heating=listing.heating,
        gas_supply=listing.gas_supply,
        sewage=listing.sewage,
        is_negotiable=listing.is_negotiable,
        land_purpose=listing.land_purpose,
        amenities=listing.amenities,
        nearby_amenities=listing.nearby_amenities,
        rent_period=listing.rent_period,
        deposit=listing.deposit,
        utilities_incl=listing.utilities_incl,
        min_rent_months=listing.min_rent_months,
        allowed_students=listing.allowed_students,
        allowed_pets=listing.allowed_pets,
        rent_payment=listing.rent_payment,
        mortgage_ok=listing.mortgage_ok,
        installment_ok=listing.installment_ok,
        halol_ok=listing.halol_ok,
        deed_type=listing.deed_type,
        source_type=listing.source_type.value,
        status=listing.status.value,
        moderation_status=listing.moderation_status.value,
        views_count=listing.views_count,
        contacts_count=listing.contacts_count,
        favorites_count=listing.favorites_count,
        is_boosted=listing.is_boosted,
        boost_until=listing.boost_until,
        is_highlighted=listing.is_highlighted,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        expires_at=listing.expires_at,
        images=images_list,
        original_language=listing.original_language,
        is_translated=_is_translated(listing, lang),
        # S3–S8 fields + S5 dual-read mirrors (building_type, is_furnished,
        # market_type, furniture).
        **_build_full_response_kwargs(listing),
    )


# =============================================================================
# Block F V2.0 (F1) — DRAFT two-step publish flow
# =============================================================================
#
# Sellers create listings in two stages:
#   Stage 1 (POST /listings/draft): structured params + photos → DRAFT row,
#           AI generation enqueued with triggered_by="manual".
#   Stage 2 (GET /listings/{id}/draft-preview + PATCH status=active):
#           seller reviews + optionally edits the AI text, then publishes.
#
# The worker (PR-F5a) preserves DRAFT through generation — only the
# seller's PATCH flips status to ACTIVE and fires the existing D4
# autopost + A4 saved-search hooks. This keeps Block D interfaces
# untouched: every status transition still routes through the same
# helper as before.


def _build_listing_kwargs(data, seller, source_type) -> dict:
    """Block F F1 — extract Listing-constructor kwargs from a
    ``ListingCreate`` payload. Used by both ``create_listing`` (status
    defaults to ACTIVE) and ``create_draft_listing`` (status=DRAFT).
    Returns a plain dict; caller adds ``status=...`` and constructs.
    """
    from app.db.models import Currency, ListingType, PropertyType

    return dict(
        seller_id=seller.id,
        type=ListingType(data.type),
        property_type=PropertyType(data.property_type),
        rooms=data.rooms,
        area=data.area,
        floor=data.floor,
        total_floors=data.total_floors,
        region=data.region,
        district=data.district,
        address=data.address,
        latitude=data.latitude,
        longitude=data.longitude,
        price=data.price,
        currency=Currency(data.currency),
        title=data.title,
        description=data.description,
        phone=data.phone or seller.phone,
        seller_type=data.seller_type,
        source_type=source_type,
        moderation_status=ModerationStatus.APPROVED,
        living_area=data.living_area,
        kitchen_area=data.kitchen_area,
        land_area=data.land_area,
        building_type=data.building_type,
        condition=data.condition,
        house_type=data.house_type,
        house_condition=data.house_condition,
        location_type=data.location_type,
        water_supply=data.water_supply,
        electricity=data.electricity,
        heating=data.heating,
        gas_supply=data.gas_supply,
        sewage=data.sewage,
        is_furnished=data.is_furnished,
        is_negotiable=data.is_negotiable,
        land_purpose=data.land_purpose,
        amenities=data.amenities,
        nearby_amenities=data.nearby_amenities,
        rent_period=data.rent_period,
        deposit=data.deposit,
        utilities_incl=data.utilities_incl,
        min_rent_months=data.min_rent_months,
        allowed_students=data.allowed_students,
        allowed_pets=data.allowed_pets,
        rent_payment=data.rent_payment,
        mortgage_ok=data.mortgage_ok,
        installment_ok=data.installment_ok,
        halol_ok=data.halol_ok,
        deed_type=data.deed_type,
        urgent_flag=data.urgent_flag,
        city=data.city,
        microdistrict=data.microdistrict,
        jk_name=data.jk_name,
        landmark=data.landmark,
        metro_station=data.metro_station,
        seller_telegram=data.seller_telegram,
        commercial_type=data.commercial_type,
        price_per_sqm=data.price_per_sqm,
        ceiling_height=data.ceiling_height,
        entrance=data.entrance,
        parking_comm=data.parking_comm,
        building_class=data.building_class,
        market_type=data.market_type,
        wall_material=data.wall_material,
        furniture=data.furniture,
        garage=data.garage,
        basement=data.basement,
        buildings_exist=data.buildings_exist,
        fence=data.fence,
        land_shape=data.land_shape,
        balcony=data.balcony,
        listing_subtype=data.listing_subtype,
        floor_plan_url=data.floor_plan_url,
        jk_id=data.jk_id,
    )


class DraftCreateResponse(BaseModel):
    """Minimal response for ``POST /listings/draft``. Stage 2 polls
    ``/draft-preview`` for the full AI text."""

    id: UUID
    status: str


@router.post("/draft", response_model=DraftCreateResponse, status_code=201)
async def create_draft_listing(
    data: ListingCreate,
    seller: Seller = Depends(check_can_create_listing),
    db: AsyncSession = Depends(get_db),
):
    """Block F F1 Stage 1 — create a listing in DRAFT status and
    enqueue AI generation with ``triggered_by="manual"``.

    No notifications, no autopost — those fire only when the seller's
    PATCH later flips status DRAFT → ACTIVE (which uses the existing
    ``_dispatch_autopost_for_status_change`` helper unchanged).

    Quota gate (Block C C2) still applies via ``check_can_create_listing``.
    """
    from app.db.models import SourceType
    from app.workers.tasks.ai_generation import generate_listing_description

    # Sprint 5 dual-read parity with POST "".
    _dual = _apply_dual_read_inputs(data.model_dump(exclude_unset=True))
    data.market_type = _dual.get("market_type", data.market_type)
    data.furniture = _dual.get("furniture", data.furniture)

    kwargs = _build_listing_kwargs(data, seller, SourceType.MANUAL)
    listing = Listing(**kwargs, status=ListingStatus.DRAFT)
    _clear_incompatible_fields(listing)
    _validate_required_fields(listing)
    _populate_listing_lang_columns(listing)

    db.add(listing)
    await db.flush()

    if data.images:
        for idx, img_data in enumerate(data.images):
            db.add(
                ListingImage(
                    listing_id=listing.id,
                    original_url=img_data.original_url,
                    thumbnail_url=img_data.thumbnail_url,
                    medium_url=img_data.medium_url,
                    large_url=img_data.large_url,
                    position=img_data.position if img_data.position else idx,
                    is_primary=img_data.is_primary
                    if img_data.is_primary
                    else (idx == 0),
                    upload_status="completed",
                )
            )

    # DRAFT does NOT count against listings_count — that mirrors the
    # B2C feed which never sees DRAFT. Counter increments on first
    # PATCH DRAFT → ACTIVE (handled in update_listing). This prevents
    # abandoned drafts (purged after 7 days) from inflating quotas.
    await db.commit()

    # Enqueue AI generation. ai_description_* stays null so the
    # frontend polling loop waits for real AI text rather than
    # stopping early on a stale fallback. If the task permanently
    # fails, _write_fallback_on_failure fills the fields.
    from app.workers.tasks.ai_generation import generate_listing_description

    try:
        generate_listing_description.delay(
            str(listing.id), triggered_by="manual", wishes=data.ai_wishes
        )
        logger.info(
            "listing.draft.created seller=%s listing=%s images=%d",
            seller.id,
            listing.id,
            len(data.images or []),
        )
    except Exception as exc:
        logger.warning(
            "listing.draft.ai_enqueue_failed listing=%s: %s",
            listing.id,
            exc,
        )

    return DraftCreateResponse(id=listing.id, status=listing.status.value)


@router.get("/{listing_id}/draft-preview", response_model=DraftPreviewResponse)
async def get_draft_preview(
    listing_id: UUID,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """Block F F1 Stage 2 — poll target. Returns the listing's three
    AI descriptions + the param snapshot at last generation.

    Owner-only. The frontend polls this at 2s × 15 iterations after
    POST /listings/draft until ``ai_description_ru`` is non-null
    (typical p95 ~3s).
    """
    row = await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.seller_id == seller.id,
            Listing.deleted_at.is_(None),
        )
    )
    listing = row.scalar_one_or_none()
    if listing is None:
        raise NotFoundException("Listing", str(listing_id))

    return DraftPreviewResponse(
        id=listing.id,
        status=listing.status.value,
        ai_description_ru=listing.ai_description_ru,
        ai_description_uz=listing.ai_description_uz,
        ai_description_uz_cyrl=listing.ai_description_uz_cyrl,
        last_ai_param_snapshot=listing.last_ai_param_snapshot,
        ai_generation_attempted_at=listing.ai_generation_attempted_at,
    )


@router.post(
    "/{listing_id}/regenerate",
    response_model=RegenerateResponse,
    status_code=202,
)
async def regenerate_listing_text(
    listing_id: UUID,
    data: RegenerateRequest,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """Block F F1 — re-run AI generation for an existing listing.

    Accepted on DRAFT (seller iterating on Stage 2) and on ACTIVE
    (seller asking for a refresh after edits). ``language=None`` is
    the only mode currently emitted by the worker — it always re-emits
    all three locales; the field is reserved for future per-language
    granularity.

    Owner-only; rejects 403 otherwise. Idempotent at the Celery layer
    (multiple in-flight tasks for the same listing converge on the
    same final state — last-write-wins, no consistency invariant).
    """
    from app.workers.tasks.ai_generation import generate_listing_description

    row = await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.seller_id == seller.id,
            Listing.deleted_at.is_(None),
        )
    )
    listing = row.scalar_one_or_none()
    if listing is None:
        raise NotFoundException("Listing", str(listing_id))

    if listing.status not in (
        ListingStatus.DRAFT,
        ListingStatus.ACTIVE,
        ListingStatus.GENERATION_FAILED,
    ):
        raise BadRequestException(
            f"Cannot regenerate listing in status={listing.status.value}"
        )

    # Clear existing text so the frontend polling loop keeps running until
    # the Celery task writes real AI text (or the structured-params fallback
    # on permanent failure via _write_fallback_on_failure).  The old logic
    # never cleared text, so the poll saw the stale fallback on the first
    # fetch and stopped — the AI result was written to DB but never shown.
    listing.ai_description_ru = None
    listing.ai_description_uz = None
    listing.ai_description_uz_cyrl = None
    await db.commit()

    try:
        generate_listing_description.delay(
            str(listing.id), triggered_by=data.triggered_by, wishes=data.wishes
        )
        logger.info(
            "listing.regenerate.queued listing=%s triggered_by=%s",
            listing.id,
            data.triggered_by,
        )
    except Exception as exc:
        logger.warning(
            "listing.regenerate.enqueue_failed listing=%s: %s",
            listing.id,
            exc,
        )
        raise BadRequestException("Could not queue regeneration; try again")

    return RegenerateResponse(status="queued")


@router.get("/{listing_id}/source-text", response_model=SourceTextResponse)
async def get_listing_source_text(
    listing_id: UUID,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """Block F F1 — B2B owner-only access to the parser's raw text.

    Per spec: B2C never sees ``raw_text``. Seller cabinet has an
    expandable "Показать исходный текст из источника" block for
    listings that came from a parser source (CLAIMED or PARSED).
    Returns 404 for manually-created listings — there is no source
    text to show.
    """
    from app.db.models import SourceType

    row = await db.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.seller_id == seller.id,
            Listing.deleted_at.is_(None),
        )
    )
    listing = row.scalar_one_or_none()
    if listing is None:
        raise NotFoundException("Listing", str(listing_id))

    if listing.source_type == SourceType.MANUAL:
        # Manually-created listings have no upstream source. The
        # frontend should not show the expander in this case but we
        # still return 404 as a defensive check.
        raise NotFoundException("Source text", str(listing_id))

    source_label = (
        listing.source_type.value
        if hasattr(listing.source_type, "value")
        else str(listing.source_type)
    )
    return SourceTextResponse(raw_text=listing.raw_text, source=source_label)


# ─────────────────────────────────────────────────────────────────────
# Block F V2.0 F2 — synonym matcher (Stage-2 text hints)
# ─────────────────────────────────────────────────────────────────────


class _AnalyseTextRequest(BaseModel):
    text: str = Field(..., max_length=20_000)
    language: str = Field(..., max_length=8)
    current_params: dict = Field(default_factory=dict)


class _SynonymMatchOut(BaseModel):
    parameter_key: str
    parameter_value: Optional[str] = None
    surface_form: str
    polarity: str
    action: str
    position: int


class _AnalyseTextResponse(BaseModel):
    matches: list[_SynonymMatchOut]


_ANALYSE_TEXT_RATE_LIMIT = 30
_ANALYSE_TEXT_WINDOW_SECONDS = 60


@router.post("/{listing_id}/analyse-text", response_model=_AnalyseTextResponse)
async def analyse_listing_text(
    listing_id: UUID,
    payload: _AnalyseTextRequest,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """Block F F2 — return synonym hints for the seller's Stage-2 text.

    Owner-only. Rate-limited at 30 calls/min/seller via Redis. The
    debounced FE callsite caps natural traffic well below the limit;
    the guard is there for misbehaving clients.
    """
    # Atomic rate-limit (fail-soft on Redis outage).
    try:
        from app.db.redis import get_redis

        client = await get_redis()
        key = f"f2:rl:{seller.id}"
        n = await client.incr(key)
        if n == 1:
            await client.expire(key, _ANALYSE_TEXT_WINDOW_SECONDS)
        if n > _ANALYSE_TEXT_RATE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limited",
                    "retry_after_s": _ANALYSE_TEXT_WINDOW_SECONDS,
                },
            )
    except HTTPException:
        raise
    except Exception:
        logger.warning("synonym_matcher.rate_limit_check_failed seller=%s", seller.id)

    # Ownership check — keep the listing private to its seller.
    listing = (
        await db.execute(
            select(Listing).where(
                Listing.id == listing_id,
                Listing.seller_id == seller.id,
                Listing.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if listing is None:
        raise NotFoundException("Listing", str(listing_id))

    from app.services.synonym_matcher import match_text_to_params

    matches = await match_text_to_params(
        db,
        text=payload.text,
        lang=payload.language,
        current_params=payload.current_params,
    )
    return _AnalyseTextResponse(
        matches=[
            _SynonymMatchOut(
                parameter_key=m.parameter_key,
                parameter_value=m.parameter_value,
                surface_form=m.surface_form,
                polarity=m.polarity,
                action=m.action,
                position=m.position,
            )
            for m in matches
        ]
    )


@router.patch("/{listing_id}", response_model=ListingResponse)
async def update_listing(
    listing_id: UUID,
    data: ListingUpdate,
    request: Request,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a listing.

    Only the owner seller can update their listings.
    """
    query = (
        select(Listing)
        .where(
            Listing.id == listing_id,
            Listing.seller_id == seller.id,
            Listing.deleted_at.is_(None),
        )
        .options(selectinload(Listing.images))
    )
    result = await db.execute(query)
    listing = result.scalar_one_or_none()

    if not listing:
        raise NotFoundException("Listing", str(listing_id))

    # Update fields
    from app.db.models import Currency, ListingStatus, ListingType, PropertyType

    update_data = data.model_dump(exclude_unset=True)

    # Sprint 5 dual-read: if caller supplied the old name (building_type /
    # is_furnished), promote it to the new column (market_type / furniture).
    # Conflicts raise BadRequestException before any DB write.
    update_data = _apply_dual_read_inputs(update_data)

    # Capture old price for price-drop notification
    old_price = listing.price
    old_currency = listing.currency.value
    # Block D D4 — snapshot the status before mutation so we can decide
    # which autopost task (if any) to fire after commit.
    old_status = listing.status

    # Extract images from update_data to handle separately
    new_images_data = update_data.pop("images", None)

    # Block phase-2 — sale capture. Pull the sale-only fields out of
    # update_data before the generic setattr loop so we don't try to
    # write them to non-existent Listing columns. They feed the
    # ListingSale upsert below once the status transition is committed.
    sale_price = update_data.pop("sold_price", None)
    sale_currency = update_data.pop("sold_currency", None)
    sale_notes = update_data.pop("sold_notes", None)

    target_status_raw = update_data.get("status")
    is_target_sold = (
        target_status_raw == ListingStatus.SOLD.value
        if isinstance(target_status_raw, str)
        else target_status_raw == ListingStatus.SOLD
    )
    # Reject the transition before mutating anything if SOLD lacks price.
    if is_target_sold and (sale_price is None or sale_currency is None):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "sold_price_required",
                "message": (
                    "sold_price and sold_currency are required when "
                    "transitioning a listing to SOLD."
                ),
            },
        )

    # Track whether translatable content changed
    _TRANSLATABLE_FIELDS = {"description", "title", "address"}
    content_changed = False

    for field, value in update_data.items():
        if field == "type" and value:
            setattr(listing, field, ListingType(value))
        elif field == "property_type" and value:
            setattr(listing, field, PropertyType(value))
        elif field == "currency" and value:
            setattr(listing, field, Currency(value))
        elif field == "status" and value:
            setattr(listing, field, ListingStatus(value))
        else:
            if field in _TRANSLATABLE_FIELDS and getattr(listing, field) != value:
                content_changed = True
            setattr(listing, field, value)

    # Enforce visibility matrix after applying user updates: if property_type
    # or type changed, wipe fields that are no longer visible for the new
    # combo. Runs BEFORE required-field validation so cleared fields don't
    # trip it.
    _clear_incompatible_fields(listing)

    # Block F F1 — DRAFT → ACTIVE publish. AI prose is an enhancement, not
    # a hard gate: the buyer feed renders the `description` column (see
    # _resolve_field), so a complete listing is publishable from its own
    # text + structured fields. We used to 409 ("ai_generation_pending")
    # until the worker populated ai_description_ru, which stranded sellers
    # who skip AI text (the "Далее" path) or whose generation is slow/down —
    # they hit "не удалось опубликовать" with no way to proceed. When AI
    # text isn't ready yet, fall back to the seller's own description so
    # AI-text consumers (autopost / SEO / export) still have content; the
    # worker's "already_generated" guard then leaves it untouched.
    if (
        old_status == ListingStatus.DRAFT
        and listing.status == ListingStatus.ACTIVE
        and not listing.ai_description_ru
        and listing.description
    ):
        listing.ai_description_ru = listing.description

    # Block F F1 — on the first DRAFT → ACTIVE flip: auto-approve so the
    # listing becomes immediately B2C-visible (no manual moderation queue),
    # and increment the seller's listings_count (drafts don't count).
    if (
        old_status == ListingStatus.DRAFT
        and listing.status == ListingStatus.ACTIVE
    ):
        listing.moderation_status = ModerationStatus.APPROVED
        seller.listings_count += 1
        logger.info(
            "listing.draft.published seller=%s listing=%s", seller.id, listing.id
        )

    # Validate required fields after applying the update — mirrors
    # frontend validation so a PATCH cannot leave a listing incomplete.
    # is_create=False so create-only rules (city, commercial_type) don't
    # reject PATCHes on legacy rows that predate those rules.
    _validate_required_fields(listing, is_create=False)

    # Re-detect language and reset translation if content changed
    if content_changed:
        _populate_listing_lang_columns(listing)

    # Block D D4 — bump the version counter on every successful edit so
    # the cabinet's "post stale" badge becomes accurate. Cheap (one
    # int), no extra schema. Only bumped if SOME field actually changed
    # (update_data is non-empty after the loop above).
    if update_data:
        listing.version = (listing.version or 1) + 1

    # Block phase-2 — sale capture. Now that the status mutation has
    # been applied (and required-fields validated) we materialise the
    # ListingSale row. UNIQUE(listing_id) means a re-confirmation
    # (seller re-PATCHes SOLD with a corrected price) is an in-place
    # update, not a duplicate-key error. We mirror the sale snapshot
    # onto the Listing row in the same transaction so the feed-side
    # filters never observe a half-written sale.
    if is_target_sold and sale_price is not None and sale_currency is not None:
        now = datetime.utcnow()
        existing_sale = (
            await db.execute(
                select(ListingSale).where(ListingSale.listing_id == listing.id)
            )
        ).scalar_one_or_none()
        if existing_sale is None:
            db.add(
                ListingSale(
                    listing_id=listing.id,
                    sold_price=sale_price,
                    sold_currency=sale_currency,
                    sold_at=now,
                    notes=sale_notes,
                )
            )
        else:
            existing_sale.sold_price = sale_price
            existing_sale.sold_currency = sale_currency
            existing_sale.sold_at = now
            if sale_notes is not None:
                existing_sale.notes = sale_notes
        # Mirror onto the Listing row for cheap feed filters.
        listing.sold_price = sale_price
        listing.sold_currency = sale_currency
        listing.sold_at = now

    # Replace images if provided — frontend sends the complete final list
    # (kept existing + newly uploaded). Any existing image NOT in this list
    # was removed by the user, so we delete and recreate from scratch.
    if new_images_data is not None:
        # Delete all existing images for this listing
        await db.execute(
            delete(ListingImage).where(ListingImage.listing_id == listing.id)
        )
        # Insert the new complete list
        for idx, img_data in enumerate(new_images_data):
            listing_image = ListingImage(
                listing_id=listing.id,
                original_url=img_data["original_url"],
                thumbnail_url=img_data.get("thumbnail_url"),
                medium_url=img_data.get("medium_url"),
                large_url=img_data.get("large_url"),
                position=img_data.get("position", idx),
                is_primary=img_data.get("is_primary", idx == 0),
                upload_status="completed",
            )
            db.add(listing_image)

    await db.commit()

    # PR8 — keep the search index in sync on updates. Optional, never blocks
    # the write path.
    try:
        from app.services.search_index import index_listing as _mx_index

        _mx_index(listing)
    except Exception as exc:
        logger.warning("meili index (update) failed: %s", exc)

    # Trigger price-drop notification if price decreased
    new_price = listing.price
    if old_price is not None and new_price is not None and new_price < old_price:
        from app.workers.tasks.notifications import _send_price_drop_notification

        await _send_price_drop_notification(
            str(listing.id),
            old_price,
            new_price,
            old_currency,
        )

    # Block D D4 — autopost status-transition hooks. Fire-and-forget;
    # task failures never block the seller's listing update.
    _dispatch_autopost_for_status_change(seller, listing, old_status)

    # Block F F1 — on DRAFT → ACTIVE the listing becomes B2C-visible
    # for the first time, so saved-search subscribers must be notified
    # exactly as for the legacy POST /listings create path.
    if (
        old_status == ListingStatus.DRAFT
        and listing.status == ListingStatus.ACTIVE
    ):
        from app.workers.tasks.notifications import send_new_listing_notifications

        try:
            send_new_listing_notifications.delay(str(listing.id))
        except Exception as exc:
            logger.warning(
                "listing.draft.notify_enqueue_failed listing=%s: %s",
                listing.id,
                exc,
            )

    # Reload listing with images
    query = (
        select(Listing)
        .where(Listing.id == listing.id)
        .options(selectinload(Listing.images))
    )
    result = await db.execute(query)
    listing = result.scalar_one()

    lang = get_content_language(request)
    return ListingResponse(
        id=listing.id,
        seller_id=listing.seller_id,
        type=listing.type.value,
        property_type=listing.property_type.value,
        rooms=listing.rooms,
        area=listing.area,
        floor=listing.floor,
        total_floors=listing.total_floors,
        region=listing.region,
        district=listing.district,
        address=_resolve_field(listing, "address", lang),
        latitude=listing.latitude,
        longitude=listing.longitude,
        price=listing.price,
        currency=listing.currency.value,
        title=_resolve_field(listing, "title", lang),
        description=_resolve_field(listing, "description", lang),
        phone=listing.phone,
        seller_type=listing.seller_type,
        living_area=listing.living_area,
        kitchen_area=listing.kitchen_area,
        land_area=listing.land_area,
        condition=listing.condition,
        house_type=listing.house_type,
        house_condition=listing.house_condition,
        location_type=listing.location_type,
        water_supply=listing.water_supply,
        electricity=listing.electricity,
        heating=listing.heating,
        gas_supply=listing.gas_supply,
        sewage=listing.sewage,
        is_negotiable=listing.is_negotiable,
        land_purpose=listing.land_purpose,
        amenities=listing.amenities,
        nearby_amenities=listing.nearby_amenities,
        rent_period=listing.rent_period,
        deposit=listing.deposit,
        utilities_incl=listing.utilities_incl,
        min_rent_months=listing.min_rent_months,
        allowed_students=listing.allowed_students,
        allowed_pets=listing.allowed_pets,
        rent_payment=listing.rent_payment,
        mortgage_ok=listing.mortgage_ok,
        installment_ok=listing.installment_ok,
        halol_ok=listing.halol_ok,
        deed_type=listing.deed_type,
        source_type=listing.source_type.value,
        status=listing.status.value,
        moderation_status=listing.moderation_status.value,
        views_count=listing.views_count,
        contacts_count=listing.contacts_count,
        favorites_count=listing.favorites_count,
        is_boosted=listing.is_boosted,
        boost_until=listing.boost_until,
        is_highlighted=listing.is_highlighted,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        expires_at=listing.expires_at,
        images=[
            ListingImageResponse(
                id=img.id,
                original_url=img.original_url,
                thumbnail_url=img.thumbnail_url,
                medium_url=img.medium_url,
                large_url=img.large_url,
                position=img.position,
                is_primary=img.is_primary,
            )
            for img in listing.images
        ],
        original_language=listing.original_language,
        is_translated=_is_translated(listing, lang),
        # S3–S8 fields + S5 dual-read mirrors.
        **_build_full_response_kwargs(listing),
    )


@router.delete("/{listing_id}", status_code=204)
async def delete_listing(
    listing_id: UUID,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a listing (soft delete).

    Only the owner seller can delete their listings.
    """
    from datetime import datetime

    query = select(Listing).where(
        Listing.id == listing_id,
        Listing.seller_id == seller.id,
        Listing.deleted_at.is_(None),
    )
    result = await db.execute(query)
    listing = result.scalar_one_or_none()

    if not listing:
        raise NotFoundException("Listing", str(listing_id))

    old_status = listing.status
    listing.deleted_at = datetime.utcnow()
    listing.status = ListingStatus.DELETED

    # Update seller listings count
    seller.listings_count = max(0, seller.listings_count - 1)

    await db.commit()

    # Block D D4 — autopost cleanup if seller has a connected channel.
    _dispatch_autopost_for_status_change(seller, listing, old_status)

    # PR8 — drop from the search index. Soft-deleted rows must not
    # surface in future Meili-backed reads. Failure is non-fatal.
    try:
        from app.services.search_index import delete_listing as _mx_delete

        _mx_delete(listing.id)
    except Exception as exc:
        logger.warning("meili delete failed: %s", exc)


# =============================================================================
# View / contact event tracking — see spec-kit/partial/EXECUTION_PLAN.md §0.2
# =============================================================================


class _RecordViewIn(BaseModel):
    """Body for POST /listings/{id}/view."""

    dwell_ms: Optional[int] = Field(default=None, ge=0, le=86_400_000)
    # A5 V2.0 — anonymous-viewer cookie identifier. When the request is
    # unauthenticated, the frontend supplies an opaque per-browser id so
    # daily dedup applies to anon traffic too.
    anon_id: Optional[str] = Field(default=None, max_length=64)


def _safe_anon(anon_id: Optional[str]) -> Optional[str]:
    """Reject implausible anon ids; return None if invalid."""
    if not anon_id:
        return None
    s = anon_id.strip()
    if len(s) < 8 or len(s) > 64:
        return None
    # Only allow URL-safe base64 / hex characters
    if not all(c.isalnum() or c in "-_" for c in s):
        return None
    return s


async def _resolve_event_target(
    db: AsyncSession, listing_id: UUID
) -> Tuple[Optional[Listing], Optional[UUID]]:
    """Resolve a view/contact target across every listing source.

    The public feed (``/listings/feed``) and ``/listings/resolve/{id}`` serve
    listings from three tables — native ``listings`` plus crawled
    ``telegram_listings`` / ``olx_listings`` — so a tracked id may belong to any
    of them. A native-only lookup 404s on every crawled listing (the bulk of
    the feed); this resolves the id the same way ``/resolve`` does.

    Returns ``(listing, effective_id)``:
      * ``(Listing, id)`` — native listing, or a *claimed* crawled listing
        mapped to its native row; run the full counter + event path.
      * ``(None, id)`` — an *unclaimed* crawled listing: a real, viewable
        listing, so the event is logged against its id, but native counters are
        skipped (crawled tables carry their own scraped counts).
      * ``(None, None)`` — unknown id; the caller raises ``NotFoundException``.
    """
    native = (
        await db.execute(
            select(Listing)
            .where(Listing.id == listing_id, Listing.deleted_at.is_(None))
            .options(selectinload(Listing.seller))
        )
    ).scalar_one_or_none()
    if native is not None:
        return native, native.id

    # Crawled sources. A claimed crawl (``converted_listing_id`` set) is mapped
    # back to its native listing so counters stay consistent with ``/resolve``.
    for model in (TelegramListing, OLXListing):
        row = (
            await db.execute(
                select(model.id, model.converted_listing_id).where(
                    model.id == listing_id
                )
            )
        ).first()
        if row is None:
            continue
        if row.converted_listing_id is not None:
            claimed = (
                await db.execute(
                    select(Listing)
                    .where(
                        Listing.id == row.converted_listing_id,
                        Listing.deleted_at.is_(None),
                    )
                    .options(selectinload(Listing.seller))
                )
            ).scalar_one_or_none()
            if claimed is not None:
                return claimed, claimed.id
        # Standalone crawl (or a claim pointing at a removed listing): still a
        # real listing — log the event without touching native counters.
        return None, listing_id

    return None, None


async def _record_view_event(
    db: AsyncSession,
    listing_id: UUID,
    body: _RecordViewIn,
    current_user: Optional[User],
) -> None:
    listing, effective_id = await _resolve_event_target(db, listing_id)
    if effective_id is None:
        raise NotFoundException("Listing", str(listing_id))
    if listing is not None and is_self_view(current_user, listing):
        return

    anon = _safe_anon(body.anon_id)
    user_id = current_user.id if current_user else None

    if user_id is None and anon is None:
        # Anonymous viewer without a cookie — nothing to dedup against. Only a
        # native listing has a cached counter to bump; crawled listings keep
        # their own scraped counts, so there is nothing to do for them.
        if listing is not None:
            listing.views_count = (listing.views_count or 0) + 1
            await db.commit()
        return

    await db.execute(
        text(
            """
            INSERT INTO listing_view_event (user_id, anon_id, listing_id, event_type, viewed_at, dwell_ms)
            VALUES (:uid, :anon, :lid, 'view', now(), :dwell)
            ON CONFLICT (
                COALESCE(user_id::text, anon_id),
                listing_id,
                event_type,
                (date(viewed_at))
              )
              WHERE COALESCE(user_id::text, anon_id) IS NOT NULL
            DO UPDATE
              SET dwell_ms = GREATEST(
                              COALESCE(listing_view_event.dwell_ms, 0),
                              COALESCE(EXCLUDED.dwell_ms, 0)
                             )
            RETURNING xmax = 0 AS inserted
            """
        ),
        {
            "uid": user_id,
            "anon": anon,
            "lid": effective_id,
            "dwell": body.dwell_ms,
        },
    )
    # views_count is the cached aggregate; bump only on the first (user/anon,
    # day) event. ON CONFLICT … DO UPDATE hides whether this request created the
    # row, so we re-count today's rows for this viewer and treat a count of
    # exactly one as the first view of the day.
    today_first = await db.execute(
        text(
            """
            SELECT (
                SELECT count(*) FROM listing_view_event
                WHERE listing_id = :lid
                  AND event_type = 'view'
                  AND date(viewed_at) = current_date
                  AND COALESCE(user_id::text, anon_id) = COALESCE(:uid::text, :anon)
            ) = 1 AS is_first
            """
        ),
        {"lid": effective_id, "uid": user_id, "anon": anon},
    )
    if listing is not None and today_first.scalar():
        listing.views_count = (listing.views_count or 0) + 1

    await db.commit()


@router.post("/{listing_id}/view", status_code=204)
async def record_listing_view(
    listing_id: UUID,
    body: _RecordViewIn,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Record a per-listing view event with optional dwell time.

    Authenticated callers write a row keyed by ``user_id``. Anonymous
    callers may supply an opaque ``anon_id`` (cookie, 24h TTL on the
    frontend); when provided, anonymous rows are deduped per day. Without
    a valid id (anonymous, no cookie) the only side-effect is the
    public ``Listing.views_count`` cached counter.

    Self-views (listing belongs to the requester) are no-ops.
    Dedup is one row per (user_or_anon, listing, event_type, calendar-day).

    Telemetry is fire-and-forget: any failure to record the event is logged
    server-side and swallowed so it never surfaces as a 5xx to the client.
    """
    try:
        await _record_view_event(db, listing_id, body, current_user)
    except NotFoundException:
        raise
    except Exception:
        await db.rollback()
        logger.exception("record_listing_view failed for listing %s", listing_id)


async def _record_contact_event(
    db: AsyncSession,
    listing_id: UUID,
    body: Optional[_RecordViewIn],
    current_user: Optional[User],
) -> None:
    listing, effective_id = await _resolve_event_target(db, listing_id)
    if effective_id is None:
        raise NotFoundException("Listing", str(listing_id))
    if listing is not None and is_self_view(current_user, listing):
        return

    anon = _safe_anon(body.anon_id if body else None)
    user_id = current_user.id if current_user else None

    if user_id is None and anon is None:
        # No identifier — bump the native cached counter (crawled listings have
        # none), no event row.
        if listing is not None:
            listing.contacts_count = (listing.contacts_count or 0) + 1
            await db.commit()
        return

    inserted = await db.execute(
        text(
            """
            INSERT INTO listing_view_event (user_id, anon_id, listing_id, event_type, viewed_at)
            VALUES (:uid, :anon, :lid, 'contact', now())
            ON CONFLICT (
                COALESCE(user_id::text, anon_id),
                listing_id,
                event_type,
                (date(viewed_at))
              )
              WHERE COALESCE(user_id::text, anon_id) IS NOT NULL
            DO NOTHING
            RETURNING id
            """
        ),
        {"uid": user_id, "anon": anon, "lid": effective_id},
    )
    if listing is not None and inserted.scalar_one_or_none() is not None:
        listing.contacts_count = (listing.contacts_count or 0) + 1
    await db.commit()


@router.post("/{listing_id}/contact", status_code=204)
async def record_listing_contact(
    listing_id: UUID,
    body: Optional[_RecordViewIn] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Record a contact event ("Связаться" tap).

    Same dedup contract as ``/view`` — auth user_id or anonymous anon_id.
    Only the first tap of the day increments ``Listing.contacts_count``.
    Self-contacts are no-ops.

    Fire-and-forget: failures are logged server-side and swallowed, never a 5xx.
    """
    try:
        await _record_contact_event(db, listing_id, body, current_user)
    except NotFoundException:
        raise
    except Exception:
        await db.rollback()
        logger.exception(
            "record_listing_contact failed for listing %s", listing_id
        )
