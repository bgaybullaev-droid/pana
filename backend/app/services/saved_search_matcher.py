"""T-034 — Saved-search matcher.

Pure in-memory matcher that decides whether a single Listing satisfies a
ListingFilters spec. Behavior MUST be byte-identical to the SQL-layer
`_apply_filters` in `app.api.v1.listings`:

    - Same applicability matrix (silent-drop via `_filter_is_applicable`)
    - Same scalar / range / array semantics
    - Same boolean True-only contract for sale-finance flags
    - Same AND-match for amenities / nearby_amenities
    - Same OR-match (overlap) for rent_payment

Used by the new-listing fanout (Celery `_send_new_listing_notifications`)
to decide which `SavedSearch` rows match a freshly created/updated listing
and therefore trigger a buyer notification.

This module imports the matrix helpers from listings.py rather than
duplicating them — single source of truth.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from app.api.v1.listings import _clear_incompatible_fields, _filter_is_applicable
from app.db.models import Listing
from app.schemas.listing import ListingFilters


def _scalar_str(value) -> Optional[str]:
    """Unwrap SQLAlchemy enum values to their .value (string)."""
    if value is None:
        return None
    if hasattr(value, "value"):
        return value.value
    return value


def _match_listing_to_filters(listing: Listing, filters: ListingFilters) -> bool:
    """Return True iff `listing` satisfies every applicable clause in
    `filters`.

    Mirrors `_apply_filters` clause-for-clause. Each clause:
      1. consults `_filter_is_applicable` for matrix-gated fields,
      2. reads listing.<column> if applicable,
      3. returns False on the first mismatch.

    The order of checks is the same as `_apply_filters` so behavior is
    fully predictable when matchers and SQL queries diverge under any
    future refactor.
    """
    pt = _scalar_str(listing.property_type)
    dt = _scalar_str(listing.type)

    # ── Always-applicable filters ────────────────────────────────────
    if filters.type and dt is not None and dt != filters.type:
        return False
    if filters.property_type and pt is not None and pt != filters.property_type:
        return False
    if filters.region and listing.region not in filters.region:
        return False
    if filters.district and listing.district not in filters.district:
        return False
    if filters.seller_id and listing.seller_id != filters.seller_id:
        return False
    if filters.source_type:
        ls = _scalar_str(listing.source_type)
        if ls != filters.source_type:
            return False
    if filters.price_min is not None and (
        listing.price is None or listing.price < filters.price_min
    ):
        return False
    if filters.price_max is not None and (
        listing.price is None or listing.price > filters.price_max
    ):
        return False
    if filters.q:
        # SQL uses ILIKE across title/description/district/address.
        haystack = " ".join(
            x
            for x in (
                listing.title,
                listing.description,
                listing.district,
                listing.address,
            )
            if x
        ).lower()
        if filters.q.lower() not in haystack:
            return False

    # ── Matrix-gated filters (silent-drop when not applicable) ───────
    if filters.rooms and _filter_is_applicable("rooms", pt, dt):
        if listing.rooms not in filters.rooms:
            return False

    if filters.area_min is not None and _filter_is_applicable("area_min", pt, dt):
        if listing.area is None or listing.area < filters.area_min:
            return False
    if filters.area_max is not None and _filter_is_applicable("area_max", pt, dt):
        if listing.area is None or listing.area > filters.area_max:
            return False

    if filters.floor_min is not None and _filter_is_applicable("floor_min", pt, dt):
        if listing.floor is None or listing.floor < filters.floor_min:
            return False
    if filters.floor_max is not None and _filter_is_applicable("floor_max", pt, dt):
        if listing.floor is None or listing.floor > filters.floor_max:
            return False

    if filters.land_area_min is not None and _filter_is_applicable(
        "land_area_min", pt, dt
    ):
        if listing.land_area is None or listing.land_area < filters.land_area_min:
            return False
    if filters.land_area_max is not None and _filter_is_applicable(
        "land_area_max", pt, dt
    ):
        if listing.land_area is None or listing.land_area > filters.land_area_max:
            return False

    if filters.building_type and _filter_is_applicable("building_type", pt, dt):
        if listing.building_type != filters.building_type:
            return False
    if filters.condition and _filter_is_applicable("condition", pt, dt):
        if listing.condition not in filters.condition:
            return False
    if filters.furnished is not None and _filter_is_applicable("furnished", pt, dt):
        # `furnished` filter maps to `is_furnished` column (same as SQL).
        if listing.is_furnished != filters.furnished:
            return False

    # amenities / nearby_amenities — AND match (filter ⊆ listing).
    if filters.amenities and _filter_is_applicable("amenities", pt, dt):
        listing_amenities = set(listing.amenities or [])
        if not set(filters.amenities).issubset(listing_amenities):
            return False
    if filters.nearby_amenities and _filter_is_applicable("nearby_amenities", pt, dt):
        listing_nearby = set(listing.nearby_amenities or [])
        if not set(filters.nearby_amenities).issubset(listing_nearby):
            return False

    # ── Rent group ──
    if filters.rent_period and _filter_is_applicable("rent_period", pt, dt):
        if listing.rent_period != filters.rent_period:
            return False
    if filters.utilities_incl is not None and _filter_is_applicable(
        "utilities_incl", pt, dt
    ):
        if listing.utilities_incl != filters.utilities_incl:
            return False
    if filters.min_rent_months and _filter_is_applicable("min_rent_months", pt, dt):
        if listing.min_rent_months not in filters.min_rent_months:
            return False
    if filters.allowed_students is not None and _filter_is_applicable(
        "allowed_students", pt, dt
    ):
        if listing.allowed_students != filters.allowed_students:
            return False
    if filters.allowed_pets is not None and _filter_is_applicable(
        "allowed_pets", pt, dt
    ):
        if listing.allowed_pets != filters.allowed_pets:
            return False
    # rent_payment — OR-match (overlap), mirrors PG `&&`.
    if filters.rent_payment and _filter_is_applicable("rent_payment", pt, dt):
        listing_payments = set(listing.rent_payment or [])
        if listing_payments.isdisjoint(filters.rent_payment):
            return False

    if filters.deposit_min is not None and _filter_is_applicable("deposit_min", pt, dt):
        if listing.deposit is None or listing.deposit < filters.deposit_min:
            return False
    if filters.deposit_max is not None and _filter_is_applicable("deposit_max", pt, dt):
        if listing.deposit is None or listing.deposit > filters.deposit_max:
            return False

    # ── Sale finance + deed (booleans are True-only, mirror SQL) ──
    if filters.mortgage_ok and _filter_is_applicable("mortgage_ok", pt, dt):
        if not listing.mortgage_ok:
            return False
    if filters.installment_ok and _filter_is_applicable("installment_ok", pt, dt):
        if not listing.installment_ok:
            return False
    if filters.halol_ok and _filter_is_applicable("halol_ok", pt, dt):
        if not listing.halol_ok:
            return False
    if filters.deed_type and _filter_is_applicable("deed_type", pt, dt):
        if listing.deed_type != filters.deed_type:
            return False

    # ── Sprint 3 (T-001) — location (urgent True-only) ────────────────
    if getattr(filters, "urgent_flag", None):
        if not getattr(listing, "urgent_flag", False):
            return False
    if getattr(filters, "city", None):
        if getattr(listing, "city", None) != filters.city:
            return False
    if getattr(filters, "microdistrict", None):
        if getattr(listing, "microdistrict", None) != filters.microdistrict:
            return False
    if getattr(filters, "jk_name", None) and _filter_is_applicable("jk_name", pt, dt):
        if getattr(listing, "jk_name", None) != filters.jk_name:
            return False
    if getattr(filters, "metro_station", None) and _filter_is_applicable(
        "metro_station", pt, dt
    ):
        if getattr(listing, "metro_station", None) != filters.metro_station:
            return False

    # ── Sprint 4 (T-009) — commercial ─────────────────────────────────
    if getattr(filters, "commercial_type", None) and _filter_is_applicable(
        "commercial_type", pt, dt
    ):
        if getattr(listing, "commercial_type", None) != filters.commercial_type:
            return False
    if getattr(filters, "building_class", None) and _filter_is_applicable(
        "building_class", pt, dt
    ):
        if getattr(listing, "building_class", None) != filters.building_class:
            return False
    if getattr(filters, "entrance", None) and _filter_is_applicable("entrance", pt, dt):
        if getattr(listing, "entrance", None) != filters.entrance:
            return False
    if getattr(filters, "parking_comm", None) is not None and _filter_is_applicable(
        "parking_comm", pt, dt
    ):
        if getattr(listing, "parking_comm", None) != filters.parking_comm:
            return False
    if getattr(
        filters, "ceiling_height_min", None
    ) is not None and _filter_is_applicable("ceiling_height_min", pt, dt):
        ch = getattr(listing, "ceiling_height", None)
        if ch is None or ch < filters.ceiling_height_min:
            return False
    if getattr(
        filters, "ceiling_height_max", None
    ) is not None and _filter_is_applicable("ceiling_height_max", pt, dt):
        ch = getattr(listing, "ceiling_height", None)
        if ch is None or ch > filters.ceiling_height_max:
            return False
    if getattr(
        filters, "price_per_sqm_min", None
    ) is not None and _filter_is_applicable("price_per_sqm_min", pt, dt):
        pps = getattr(listing, "price_per_sqm", None)
        if pps is None or pps < filters.price_per_sqm_min:
            return False
    if getattr(
        filters, "price_per_sqm_max", None
    ) is not None and _filter_is_applicable("price_per_sqm_max", pt, dt):
        pps = getattr(listing, "price_per_sqm", None)
        if pps is None or pps > filters.price_per_sqm_max:
            return False

    # ── Sprint 5 (T-006, T-008) — dual-read columns ───────────────────
    if getattr(filters, "market_type", None) and _filter_is_applicable(
        "market_type", pt, dt
    ):
        if getattr(listing, "market_type", None) != filters.market_type:
            return False
    if getattr(filters, "wall_material", None) and _filter_is_applicable(
        "wall_material", pt, dt
    ):
        if getattr(listing, "wall_material", None) != filters.wall_material:
            return False
    if getattr(filters, "furniture", None) and _filter_is_applicable(
        "furniture", pt, dt
    ):
        if getattr(listing, "furniture", None) != filters.furniture:
            return False

    # ── Sprint 6 (T-011, T-014, T-015) — property polish ──────────────
    if getattr(filters, "garage", None) is not None and _filter_is_applicable(
        "garage", pt, dt
    ):
        if getattr(listing, "garage", None) != filters.garage:
            return False
    if getattr(filters, "basement", None) is not None and _filter_is_applicable(
        "basement", pt, dt
    ):
        if getattr(listing, "basement", None) != filters.basement:
            return False
    if getattr(filters, "buildings_exist", None) is not None and _filter_is_applicable(
        "buildings_exist", pt, dt
    ):
        if getattr(listing, "buildings_exist", None) != filters.buildings_exist:
            return False
    if getattr(filters, "fence", None) is not None and _filter_is_applicable(
        "fence", pt, dt
    ):
        if getattr(listing, "fence", None) != filters.fence:
            return False
    if getattr(filters, "land_shape", None) and _filter_is_applicable(
        "land_shape", pt, dt
    ):
        if getattr(listing, "land_shape", None) != filters.land_shape:
            return False
    if getattr(filters, "balcony", None) and _filter_is_applicable("balcony", pt, dt):
        if getattr(listing, "balcony", None) != filters.balcony:
            return False
    if getattr(filters, "listing_subtype", None) and _filter_is_applicable(
        "listing_subtype", pt, dt
    ):
        if getattr(listing, "listing_subtype", None) != filters.listing_subtype:
            return False

    # ── Sprint 7 (T-027) — jk_id always-applicable ─────────────────────
    if getattr(filters, "jk_id", None):
        if getattr(listing, "jk_id", None) != filters.jk_id:
            return False

    return True


def match_listing_against_saved_searches(
    listing: Listing,
    saved_searches: Iterable[ListingFilters],
) -> List[ListingFilters]:
    """Return the subset of `saved_searches` whose filters match `listing`.

    The listing is normalized once via `_clear_incompatible_fields` before
    matching. For listings written through the API this is an idempotent
    no-op (the helper already ran on create/update); for crawler-imported
    rows it ensures matrix-stale fields are wiped before comparison so a
    rent listing carrying a leftover `mortgage_ok=True` from raw data
    can't accidentally match a sale-finance saved search.
    """
    _clear_incompatible_fields(listing)
    return [s for s in saved_searches if _match_listing_to_filters(listing, s)]
