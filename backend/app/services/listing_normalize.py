"""BACKLOG #4 — single normalization layer for listings (Variant A).

One place that converts a row from **any** source — native :class:`Listing`,
crawled :class:`TelegramListing` / :class:`OLXListing` — into the canonical
:class:`~app.schemas.unified.UnifiedListingResponse` (all ~80 display fields)
with a **ready** human ``title`` and language-resolved ``description``.

Every surface reads from here instead of mapping rows itself:

- the app detail endpoint ``GET /listings/resolve`` returns the canonical
  object directly;
- the app feed ``GET /listings/feed`` and the bot (inline / ``/search``)
  build the canonical object and take a light projection.

Crawled rows have no ``title``; :func:`generate_title` synthesises one
("rooms + property type + district") identically for every surface, reusing
the same localized vocabulary the AI copy fallback uses
(:mod:`app.core.listing_i18n`). Normalization is **not** enrichment — a field
the parser never captured stays ``None``; we do not invent data.
"""

from __future__ import annotations

from typing import List, Optional

from app.core import listing_i18n
from app.core.listing_i18n import localize_district, localize_property_type
from app.schemas.unified import UnifiedListingImage, UnifiedListingResponse
from app.services.query_parser import canonical_district

# ─────────────────────────────────────────────────────────────────────
# Source-value normalization (canonical home for these maps)
# ─────────────────────────────────────────────────────────────────────
#
# Crawled tables store raw parser strings ("sale", "daily_rent", "office")
# that must collapse onto the platform enums ("sell"/"rent", apartment/
# house/commercial/land). Native rows already hold enum members.

LISTING_TYPE_MAP = {
    "sale": "sell",
    "daily_rent": "rent",
    "rent": "rent",
    "sell": "sell",
}
PROPERTY_TYPE_MAP = {"office": "commercial"}


def normalize_listing_type(val: Optional[str]) -> Optional[str]:
    return LISTING_TYPE_MAP.get(val, val) if val is not None else None


def normalize_property_type(val: Optional[str]) -> Optional[str]:
    return PROPERTY_TYPE_MAP.get(val, val) if val is not None else None


# ─────────────────────────────────────────────────────────────────────
# Localized text helpers (shared by every mapper)
# ─────────────────────────────────────────────────────────────────────


def resolve_field(listing, field: str, lang: str) -> Optional[str]:
    """Resolve a text field to the requested language with fallback."""
    localized = getattr(listing, f"{field}_{lang}", None)
    return localized or getattr(listing, field, None)


def is_translated(listing, lang: str) -> bool:
    """Check if listing content is served in a translated language."""
    orig = getattr(listing, "original_language", None) or "ru"
    return orig != lang and getattr(listing, "translation_status", None) == "completed"


def normalize_crawler_images(images) -> List[UnifiedListingImage]:
    """Crawled ``images`` JSONB → list of unified images (URL-only strings)."""
    if not images:
        return []
    if isinstance(images, list):
        return [UnifiedListingImage(url=img) for img in images if isinstance(img, str)]
    return []


# ─────────────────────────────────────────────────────────────────────
# Display-photo selection (shared by feed + bot)
# ─────────────────────────────────────────────────────────────────────


def native_primary_photo(listing) -> Optional[str]:
    """Best display photo for a native Listing: the ``is_primary`` image,
    else the first, preferring a lighter variant. Relies on the caller
    eager-loading ``images`` so this never triggers a lazy load.
    """
    try:
        images = list(getattr(listing, "images", None) or [])
    except Exception:
        return None
    if not images:
        return None
    chosen = next((im for im in images if getattr(im, "is_primary", False)), images[0])
    return (
        getattr(chosen, "medium_url", None)
        or getattr(chosen, "large_url", None)
        or getattr(chosen, "original_url", None)
    )


def crawled_photo_url(images) -> Optional[str]:
    """First usable image URL from a crawled listing's JSONB ``images``
    (stored as a list of absolute URL strings)."""
    if isinstance(images, list):
        for img in images:
            if isinstance(img, str) and img:
                return img
    return None


# ─────────────────────────────────────────────────────────────────────
# Human title generation (single source for all surfaces)
# ─────────────────────────────────────────────────────────────────────
#
# Shares the wording convention of the AI copy template fallback
# (``ai_generation._template_fallback``): "{rooms}-комн. {type}, {district}".
# The abbreviated "-комн." form is gender-safe across property types
# (avoids "3-комнатная дом") and matches the bot's existing headline style.

_ROOMS_SUFFIX = {"ru": "-комн.", "uz": " xonali", "uz_cyrl": " хонали"}
_EMPTY_TITLE = {"ru": "Объявление", "uz": "E'lon", "uz_cyrl": "Эълон"}


def _district_key(district: Optional[str]) -> Optional[str]:
    """Canonical district key for localization.

    Native rows store the key already ("olmazor"); crawled rows store a raw
    spelling ("Чиланзар") that must be mapped via the query parser. Unknown
    spellings return ``None`` so the caller can fall back to the raw text.
    """
    if not district:
        return None
    if district in listing_i18n.DISTRICT_NAMES:
        return district
    return canonical_district(district)


def generate_title(
    *,
    property_type: Optional[str],
    rooms: Optional[int],
    district: Optional[str],
    lang: str,
) -> str:
    """Human listing title: "{rooms}-комн. {type}, {district}" (localized).

    ``district`` is the raw stored value (canonical key for native rows, free
    spelling for crawled). Rooms are shown only when present; the district is
    localized when recognised, otherwise the raw spelling is kept; when no
    district is known it is omitted.
    """
    suffix = _ROOMS_SUFFIX.get(lang, _ROOMS_SUFFIX["ru"])

    lead_bits: list[str] = []
    if rooms:
        lead_bits.append(f"{rooms}{suffix}")
    pt_name = localize_property_type(property_type, lang) if property_type else ""
    if pt_name:
        # Lowercase the type only mid-phrase (after the room count); keep it
        # capitalized when it leads the title.
        lead_bits.append(pt_name.lower() if lead_bits else pt_name)

    segments: list[str] = []
    lead = " ".join(lead_bits).strip()
    if lead:
        segments.append(lead)

    key = _district_key(district)
    district_label = localize_district(key, lang) if key else (district or "")
    if district_label:
        segments.append(district_label)

    return ", ".join(s for s in segments if s) or _EMPTY_TITLE.get(lang, _EMPTY_TITLE["ru"])


# ─────────────────────────────────────────────────────────────────────
# Canonical builders: source row → UnifiedListingResponse
# ─────────────────────────────────────────────────────────────────────


def native_to_canonical(
    listing,
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

    db_title = resolve_field(listing, "title", lang)
    title = (
        db_title
        if (db_title and db_title.strip())
        else generate_title(
            property_type=listing.property_type.value if listing.property_type else None,
            rooms=listing.rooms,
            district=listing.district,
            lang=lang,
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
        address=resolve_field(listing, "address", lang),
        latitude=listing.latitude,
        longitude=listing.longitude,
        description=resolve_field(listing, "description", lang),
        images=images,
        contact_phone=listing.phone,
        created_at=listing.created_at,
        title=title,
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
        is_translated=is_translated(listing, lang),
    )


def telegram_to_canonical(
    listing,
    is_favorited: bool = False,
    favorites_count: int = 0,
    lang: str = "ru",
) -> UnifiedListingResponse:
    property_type = normalize_property_type(listing.property_type)
    return UnifiedListingResponse(
        source="telegram",
        id=listing.id,
        type=normalize_listing_type(listing.listing_type),
        property_type=property_type,
        price=listing.price,
        currency=(listing.currency or "").upper(),
        rooms=listing.rooms,
        area=listing.area_sqm,
        floor=listing.floor,
        total_floors=listing.total_floors,
        region=listing.region,
        district=listing.district,
        address=resolve_field(listing, "address", lang),
        description=resolve_field(listing, "description", lang),
        raw_text=listing.raw_text,
        images=normalize_crawler_images(listing.images),
        contact_phone=listing.contact_phone,
        created_at=listing.created_at,
        title=generate_title(
            property_type=property_type,
            rooms=listing.rooms,
            district=listing.district,
            lang=lang,
        ),
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
        is_translated=is_translated(listing, lang),
    )


def olx_to_canonical(
    listing,
    is_favorited: bool = False,
    favorites_count: int = 0,
    lang: str = "ru",
) -> UnifiedListingResponse:
    property_type = normalize_property_type(listing.property_type)
    return UnifiedListingResponse(
        source="olx",
        id=listing.id,
        type=normalize_listing_type(listing.listing_type),
        property_type=property_type,
        price=listing.price,
        currency=(listing.currency or "").upper(),
        rooms=listing.rooms,
        area=listing.area_sqm,
        floor=listing.floor,
        total_floors=listing.total_floors,
        region=listing.region,
        district=listing.district,
        address=resolve_field(listing, "address", lang),
        description=resolve_field(listing, "description", lang),
        raw_text=listing.raw_text,
        images=normalize_crawler_images(listing.images),
        contact_phone=listing.contact_phone,
        created_at=listing.created_at,
        title=generate_title(
            property_type=property_type,
            rooms=listing.rooms,
            district=listing.district,
            lang=lang,
        ),
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
        is_translated=is_translated(listing, lang),
    )


__all__ = (
    "LISTING_TYPE_MAP",
    "PROPERTY_TYPE_MAP",
    "normalize_listing_type",
    "normalize_property_type",
    "resolve_field",
    "is_translated",
    "normalize_crawler_images",
    "native_primary_photo",
    "crawled_photo_url",
    "generate_title",
    "native_to_canonical",
    "telegram_to_canonical",
    "olx_to_canonical",
)
