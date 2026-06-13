"""Crawler import service — handles dedup and bulk import for Telegram and OLX listings."""

import hashlib
import logging
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.regions import infer_district_from_address, infer_region
from app.db.models import (
    Currency,
    Listing,
    ListingImage,
    ListingStatus,
    ListingType,
    ModerationStatus,
    OLXListing,
    PropertyType,
    Seller,
    SourceType,
    TelegramListing,
)
from app.schemas.crawler import (
    CrawlerImportItemResult,
    CrawlerImportResult,
    OLXListingImport,
    TelegramListingImport,
)
from app.utils.phone import normalize_phone

logger = logging.getLogger(__name__)


def _populate_lang_columns(listing, original_language: str) -> None:
    """Copy description/address into the appropriate _lang columns.

    Sets original_language and translation_status on the listing model.
    For 'en' (English) source, both _ru and _uz columns are left empty
    so the translation task will fill both.
    """
    listing.original_language = original_language or "ru"
    lang = listing.original_language

    if lang in ("ru", "uz"):
        if listing.description:
            setattr(listing, f"description_{lang}", listing.description)
        if listing.address:
            setattr(listing, f"address_{lang}", listing.address)
    # For 'en' — description/address stay in base columns only;
    # the translation task will translate to both ru and uz.

    listing.translation_status = "pending"


# ── Type mapping for OLX → platform enums ──────────────────────────
_LISTING_TYPE_MAP = {
    "sell": ListingType.SELL,
    "sale": ListingType.SELL,
    "rent": ListingType.RENT,
    "daily_rent": ListingType.RENT,
}

_PROPERTY_TYPE_MAP = {
    "apartment": PropertyType.APARTMENT,
    "house": PropertyType.HOUSE,
    "commercial": PropertyType.COMMERCIAL,
    "office": PropertyType.COMMERCIAL,
    "land": PropertyType.LAND,
}

_CURRENCY_MAP = {
    "USD": Currency.USD,
    "UZS": Currency.UZS,
    "usd": Currency.USD,
    "uzs": Currency.UZS,
    "у.е.": Currency.USD,
}

# Fields that can be updated when a duplicate OLX listing is re-crawled
OLX_UPDATABLE_FIELDS: List[str] = [
    "url",
    "price",
    "currency",
    "description",
    "rooms",
    "area_sqm",
    "floor",
    "total_floors",
    "district",
    "address",
    "amenities",
    "contact_phone",
    "images",
    "seller_name",
    "seller_type",
    "condition",
    "furnishing",
    "building_type",
    "land_purpose",
    "views_count",
    "bathroom",
    "ceiling_height",
    "raw_text",
]


def generate_signature(
    phone: Optional[str],
    address: Optional[str],  # kept in signature for backward compat with extra dim
    price: Optional[float],
    rooms: Optional[int],
    area: Optional[float],
    floor: Optional[int] = None,
) -> str:
    """Generate a deduplication hash from core listing fields.

    Per Block A V2.0 (A7) the signature is dominated by ``phone + area + floor +
    price`` with a ±5% price bucket. ``address`` and ``rooms`` are kept as
    extra noise-reducing dimensions but address-only differences will not split
    duplicates because the price/area/floor/phone tuple collapses them.

    Returns a 32-char hex string.
    """
    normalized_phone = normalize_phone(phone)

    # Normalize address (kept as a soft dim — see docstring)
    normalized_address = (address or "").lower().strip()

    # Bucket the price into ±5% windows so small fluctuations between sources
    # don't produce false-distinct signatures.
    price_bucket = ""
    if price and price > 0:
        # Bucket size = max(1, 5% of price). int() floors to bucket index.
        bucket_size = max(1.0, price * 0.05)
        price_bucket = str(int(price / bucket_size))

    components = [
        normalized_phone,
        normalized_address,
        price_bucket,
        str(rooms) if rooms is not None else "",
        str(int(area)) if area else "",
        str(floor) if floor is not None else "",
    ]

    signature_string = "|".join(components)
    return hashlib.md5(signature_string.encode()).hexdigest()


async def _find_by_signature(
    db: AsyncSession,
    model,
    signature_hash: str,
):
    """Find an existing listing by signature hash."""
    result = await db.execute(
        select(model).where(model.signature_hash == signature_hash)
    )
    return result.scalar_one_or_none()


async def _find_olx_by_olx_id(
    db: AsyncSession,
    olx_id: str,
) -> Optional[OLXListing]:
    """Find an existing OLX listing by olx_id."""
    result = await db.execute(select(OLXListing).where(OLXListing.olx_id == olx_id))
    return result.scalar_one_or_none()


async def import_telegram_listing(
    data: TelegramListingImport,
    db: AsyncSession,
) -> Tuple[Optional[TelegramListing], bool]:
    """Import a single Telegram listing. Returns (listing, is_duplicate)."""
    signature = generate_signature(
        data.contact_phone,
        data.address,
        data.price,
        data.rooms,
        data.area_sqm,
        floor=data.floor,
    )

    existing = await _find_by_signature(db, TelegramListing, signature)
    if existing:
        return existing, True

    # Resolve district/region; fall back to address landmark matching
    district = data.district
    region = infer_region(district)
    if not district and data.address:
        result = infer_district_from_address(data.address)
        if result:
            district, region = result

    listing = TelegramListing(
        property_type=data.property_type,
        listing_type=data.listing_type,
        price=data.price,
        currency=data.currency,
        rooms=data.rooms,
        area_sqm=data.area_sqm,
        floor=data.floor,
        total_floors=data.total_floors,
        building_type=data.building_type,
        condition=data.condition,
        land_purpose=data.land_purpose,
        region=region,
        district=district,
        address=data.address,
        description=data.description,
        amenities=data.amenities,
        contact_phone=data.contact_phone,
        confidence=data.confidence,
        images=data.images,
        raw_text=data.raw_text,
        source_channel=data.source_channel,
        message_id=data.message_id,
        signature_hash=signature,
    )
    _populate_lang_columns(listing, data.original_language)
    db.add(listing)
    await db.flush()
    return listing, False


async def _update_olx_if_changed(
    existing: OLXListing,
    data: OLXListingImport,
    db: AsyncSession,
) -> bool:
    """Compare fields and update the existing OLX listing if anything changed.

    Returns True if at least one field was updated.
    """
    changed = False
    content_changed = False
    for field in OLX_UPDATABLE_FIELDS:
        new_val = getattr(data, field, None)
        if new_val is None:
            continue
        old_val = getattr(existing, field, None)
        if new_val != old_val:
            setattr(existing, field, new_val)
            changed = True
            if field in ("description", "address"):
                content_changed = True

    if changed:
        # Re-populate lang columns when translatable content changes
        if content_changed:
            _populate_lang_columns(
                existing, data.original_language or existing.original_language or "ru"
            )

        # Recalculate district/region from address fallback if needed
        if not existing.district and existing.address:
            result = infer_district_from_address(existing.address)
            if result:
                existing.district, existing.region = result
        elif existing.district:
            existing.region = infer_region(existing.district)

        # Recalculate signature in case dedup-relevant fields changed
        existing.signature_hash = generate_signature(
            data.contact_phone,
            data.address,
            data.price,
            data.rooms,
            data.area_sqm,
            floor=data.floor,
        )
        # Refresh crawled_at
        crawled_at = data.crawled_at
        if crawled_at and crawled_at.tzinfo:
            crawled_at = crawled_at.replace(tzinfo=None)
        existing.crawled_at = crawled_at
        db.add(existing)
        await db.flush()
        logger.info(f"Updated OLX listing {data.olx_id}")

    return changed


async def import_olx_listing(
    data: OLXListingImport,
    db: AsyncSession,
) -> Tuple[Optional[OLXListing], bool, bool]:
    """Import a single OLX listing.

    Returns (listing, is_duplicate, is_updated).
    """
    # Fast-path dedup: check olx_id first
    existing = await _find_olx_by_olx_id(db, data.olx_id)
    if existing:
        updated = await _update_olx_if_changed(existing, data, db)
        return existing, True, updated

    # Signature-based dedup
    signature = generate_signature(
        data.contact_phone,
        data.address,
        data.price,
        data.rooms,
        data.area_sqm,
        floor=data.floor,
    )
    existing = await _find_by_signature(db, OLXListing, signature)
    if existing:
        return existing, True, False

    # Resolve district/region; fall back to address landmark matching
    district = data.district
    region = infer_region(district)
    if not district and data.address:
        result = infer_district_from_address(data.address)
        if result:
            district, region = result

    listing = OLXListing(
        olx_id=data.olx_id,
        url=data.url,
        property_type=data.property_type,
        listing_type=data.listing_type,
        price=data.price,
        currency=data.currency,
        rooms=data.rooms,
        area_sqm=data.area_sqm,
        floor=data.floor,
        total_floors=data.total_floors,
        region=region,
        district=district,
        address=data.address,
        description=data.description,
        amenities=data.amenities,
        contact_phone=data.contact_phone,
        confidence=data.confidence,
        images=data.images,
        source=data.source,
        crawled_at=(
            data.crawled_at.replace(tzinfo=None)
            if data.crawled_at and data.crawled_at.tzinfo
            else data.crawled_at
        ),
        seller_type=data.seller_type,
        seller_name=data.seller_name,
        views_count=data.views_count,
        posted_date=data.posted_date,
        building_type=data.building_type,
        condition=data.condition,
        land_purpose=getattr(data, "land_purpose", None),
        furnishing=data.furnishing,
        ceiling_height=data.ceiling_height,
        bathroom=data.bathroom,
        raw_text=data.raw_text,
        signature_hash=signature,
    )
    _populate_lang_columns(listing, data.original_language)
    db.add(listing)
    await db.flush()
    return listing, False, False


async def import_telegram_bulk(
    listings: list[TelegramListingImport],
    db: AsyncSession,
) -> CrawlerImportResult:
    """Bulk import Telegram listings with transaction."""
    results = []
    created = 0
    duplicates = 0
    errors = 0
    new_listings_data: list[dict] = []

    for idx, data in enumerate(listings):
        try:
            listing, is_dup = await import_telegram_listing(data, db)
            if is_dup:
                duplicates += 1
                results.append(
                    CrawlerImportItemResult(
                        index=idx,
                        success=True,
                        listing_id=str(listing.id) if listing else None,
                        is_duplicate=True,
                    )
                )
            else:
                created += 1
                results.append(
                    CrawlerImportItemResult(
                        index=idx,
                        success=True,
                        listing_id=str(listing.id) if listing else None,
                        is_duplicate=False,
                    )
                )
                if listing:
                    new_listings_data.append(
                        {
                            "id": str(listing.id),
                            "listing_type": listing.listing_type,
                            "property_type": listing.property_type,
                            "district": listing.district,
                            "price": listing.price,
                            "rooms": listing.rooms,
                            "currency": listing.currency,
                        }
                    )
        except Exception as e:
            errors += 1
            logger.error(f"Failed to import Telegram listing at index {idx}: {e}")
            results.append(
                CrawlerImportItemResult(
                    index=idx,
                    success=False,
                    error=str(e),
                )
            )

    await db.commit()

    # Trigger notifications for newly created listings (after commit so IDs are stable)
    if new_listings_data:
        from app.workers.tasks.notifications import send_crawler_listing_notifications

        for listing_data in new_listings_data:
            send_crawler_listing_notifications.delay(listing_data)

    return CrawlerImportResult(
        total=len(listings),
        created=created,
        duplicates=duplicates,
        errors=errors,
        results=results,
    )


async def import_olx_bulk(
    listings: list[OLXListingImport],
    db: AsyncSession,
) -> CrawlerImportResult:
    """Bulk import OLX listings with transaction."""
    results = []
    created = 0
    updated = 0
    duplicates = 0
    errors = 0
    new_listings_data: list[dict] = []

    for idx, data in enumerate(listings):
        try:
            listing, is_dup, is_updated = await import_olx_listing(data, db)
            if is_dup and is_updated:
                updated += 1
                results.append(
                    CrawlerImportItemResult(
                        index=idx,
                        success=True,
                        listing_id=str(listing.id) if listing else None,
                        is_duplicate=True,
                        is_updated=True,
                    )
                )
            elif is_dup:
                duplicates += 1
                results.append(
                    CrawlerImportItemResult(
                        index=idx,
                        success=True,
                        listing_id=str(listing.id) if listing else None,
                        is_duplicate=True,
                    )
                )
            else:
                created += 1
                results.append(
                    CrawlerImportItemResult(
                        index=idx,
                        success=True,
                        listing_id=str(listing.id) if listing else None,
                        is_duplicate=False,
                    )
                )
                if listing:
                    new_listings_data.append(
                        {
                            "id": str(listing.id),
                            "listing_type": listing.listing_type,
                            "property_type": listing.property_type,
                            "district": listing.district,
                            "price": listing.price,
                            "rooms": listing.rooms,
                            "currency": listing.currency,
                        }
                    )
        except Exception as e:
            errors += 1
            logger.error(f"Failed to import OLX listing at index {idx}: {e}")
            results.append(
                CrawlerImportItemResult(
                    index=idx,
                    success=False,
                    error=str(e),
                )
            )

    await db.commit()

    # Trigger notifications for newly created listings (after commit so IDs are stable)
    if new_listings_data:
        from app.workers.tasks.notifications import send_crawler_listing_notifications

        for listing_data in new_listings_data:
            send_crawler_listing_notifications.delay(listing_data)

    return CrawlerImportResult(
        total=len(listings),
        created=created,
        updated=updated,
        duplicates=duplicates,
        errors=errors,
        results=results,
    )


# ── OLX → Platform Listing conversion ──────────────────────────────


async def convert_olx_to_listing(
    olx: OLXListing,
    seller: Seller,
    db: AsyncSession,
) -> Listing:
    """Convert an OLXListing into a platform Listing owned by the seller.

    Creates ListingImage rows from the JSONB images array,
    bumps the seller's listings_count, and links the OLX record
    via converted_listing_id.

    The caller must hold a SELECT FOR UPDATE lock on `olx` and
    handle commit/rollback.
    """
    listing_type = _LISTING_TYPE_MAP.get(olx.listing_type, ListingType.SELL)
    property_type = _PROPERTY_TYPE_MAP.get(olx.property_type, PropertyType.APARTMENT)
    currency = _CURRENCY_MAP.get(olx.currency, Currency.USD)

    listing = Listing(
        seller_id=seller.id,
        type=listing_type,
        property_type=property_type,
        rooms=olx.rooms,
        area=olx.area_sqm,
        floor=olx.floor,
        total_floors=olx.total_floors,
        region=olx.region or infer_region(olx.district),
        district=olx.district,
        address=olx.address,
        price=int(olx.price),
        currency=currency,
        title=olx.description[:200] if olx.description else None,
        description=olx.description,
        phone=olx.contact_phone,
        source_type=SourceType.CLAIMED,
        # Block D D4 — claimed imports never auto-post to a channel unless
        # the seller later opts in.
        publish_to_channel=False,
        source_url=olx.url,
        status=ListingStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
        original_language=olx.original_language or "ru",
        title_ru=olx.description_ru[:200] if olx.description_ru else None,
        title_uz=olx.description_uz[:200] if olx.description_uz else None,
        description_ru=olx.description_ru,
        description_uz=olx.description_uz,
        address_ru=olx.address_ru,
        address_uz=olx.address_uz,
        translation_status=olx.translation_status or "pending",
        translated_at=olx.translated_at,
        # A1 V2.0: preserve the realtor's raw source text as metadata —
        # surfaced in cabinet via the "Show source" block, used by F1 as
        # context. Never shown in B2C.
        raw_text=olx.raw_text,
    )
    db.add(listing)
    await db.flush()  # get listing.id

    # Convert JSONB images → ListingImage rows
    if olx.images and isinstance(olx.images, list):
        for idx, img_url in enumerate(olx.images[:12]):
            if not isinstance(img_url, str):
                continue
            db.add(
                ListingImage(
                    listing_id=listing.id,
                    original_url=img_url,
                    medium_url=img_url,
                    large_url=img_url,
                    position=idx,
                    is_primary=(idx == 0),
                    upload_status="completed",
                )
            )

    # Link back
    olx.converted_listing_id = listing.id

    # Bump seller count
    seller.listings_count = (seller.listings_count or 0) + 1

    return listing


async def convert_telegram_to_listing(
    tg: TelegramListing,
    seller: Seller,
    db: AsyncSession,
) -> Listing:
    """Convert a TelegramListing into a platform Listing owned by the seller.

    Mirrors convert_olx_to_listing. The caller must hold a SELECT FOR UPDATE
    lock on `tg` and handle commit/rollback.
    """
    listing_type = _LISTING_TYPE_MAP.get(tg.listing_type, ListingType.SELL)
    property_type = _PROPERTY_TYPE_MAP.get(tg.property_type, PropertyType.APARTMENT)
    currency = _CURRENCY_MAP.get(tg.currency, Currency.USD)

    source_url = (
        f"https://t.me/{tg.source_channel}/{tg.message_id}"
        if tg.source_channel and tg.message_id
        else None
    )

    listing = Listing(
        seller_id=seller.id,
        type=listing_type,
        property_type=property_type,
        rooms=tg.rooms,
        area=tg.area_sqm,
        floor=tg.floor,
        total_floors=tg.total_floors,
        region=tg.region or infer_region(tg.district),
        district=tg.district,
        address=tg.address,
        price=int(tg.price),
        currency=currency,
        title=tg.description[:200] if tg.description else None,
        description=tg.description,
        phone=tg.contact_phone,
        source_type=SourceType.CLAIMED,
        # Block D D4 — claimed imports never auto-post to a channel unless
        # the seller later opts in.
        publish_to_channel=False,
        source_url=source_url,
        status=ListingStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
        original_language=tg.original_language or "ru",
        title_ru=tg.description_ru[:200] if tg.description_ru else None,
        title_uz=tg.description_uz[:200] if tg.description_uz else None,
        description_ru=tg.description_ru,
        description_uz=tg.description_uz,
        address_ru=tg.address_ru,
        address_uz=tg.address_uz,
        translation_status=tg.translation_status or "pending",
        translated_at=tg.translated_at,
        # A1 V2.0: see convert_olx_to_listing for rationale.
        raw_text=tg.raw_text,
    )
    db.add(listing)
    await db.flush()

    if tg.images and isinstance(tg.images, list):
        for idx, img_url in enumerate(tg.images[:12]):
            if not isinstance(img_url, str):
                continue
            db.add(
                ListingImage(
                    listing_id=listing.id,
                    original_url=img_url,
                    medium_url=img_url,
                    large_url=img_url,
                    position=idx,
                    is_primary=(idx == 0),
                    upload_status="completed",
                )
            )

    tg.converted_listing_id = listing.id
    seller.listings_count = (seller.listings_count or 0) + 1

    return listing
