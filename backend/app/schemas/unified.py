"""Unified listing schemas — normalized view across all listing sources."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import UTCDateTime


class UnifiedListingImage(BaseModel):
    """Normalized image with a single url field."""

    url: str
    thumbnail: Optional[str] = None


class UnifiedListingResponse(BaseModel):
    """Single listing resolved from any source (main, telegram, olx)."""

    source: str  # "main" | "telegram" | "olx"
    id: UUID
    type: str  # "sell" | "rent"
    property_type: str
    price: float
    currency: str
    rooms: Optional[int] = None
    area: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    region: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = None
    raw_text: Optional[str] = None
    images: List[UnifiedListingImage] = []
    contact_phone: Optional[str] = None
    created_at: UTCDateTime

    # Main-listing-only fields
    title: Optional[str] = None
    views_count: int = 0
    favorites_count: int = 0
    comments_count: int = 0
    is_favorited: bool = False
    is_boosted: bool = False
    is_highlighted: bool = False
    seller_id: Optional[UUID] = None
    seller_name: Optional[str] = None
    seller_avatar_url: Optional[str] = None
    seller_verified: bool = False
    seller_type: Optional[str] = None  # owner / realtor / developer
    seller_telegram: Optional[str] = None

    # Property attributes
    building_type: Optional[str] = None  # new / secondary
    condition: Optional[str] = None  # euro / cosmetic / needs_repair / rough
    land_purpose: Optional[str] = None
    market_type: Optional[str] = None  # new / secondary
    wall_material: Optional[str] = None
    listing_subtype: Optional[str] = None
    balcony: Optional[str] = None
    house_type: Optional[str] = None
    house_condition: Optional[List[str]] = None
    location_type: Optional[List[str]] = None

    # Extended area fields
    living_area: Optional[float] = None
    kitchen_area: Optional[float] = None
    land_area: Optional[float] = None

    # Finish & furniture
    furniture: Optional[str] = None
    is_furnished: Optional[bool] = None

    # Extra property features
    garage: Optional[bool] = None
    basement: Optional[bool] = None
    buildings_exist: Optional[bool] = None
    fence: Optional[bool] = None
    land_shape: Optional[str] = None
    ceiling_height: Optional[float] = None

    # Utilities (house / land)
    water_supply: Optional[List[str]] = None
    electricity: Optional[str] = None
    heating: Optional[List[str]] = None
    gas_supply: Optional[str] = None
    sewage: Optional[str] = None

    # Commercial attributes
    commercial_type: Optional[str] = None
    price_per_sqm: Optional[int] = None
    entrance: Optional[str] = None
    parking_comm: Optional[bool] = None
    building_class: Optional[str] = None

    # Deal conditions
    is_negotiable: bool = False
    deed_type: Optional[str] = None
    urgent_flag: bool = False

    # Rent-specific (rent listings only)
    rent_period: Optional[str] = None  # long_term / daily
    deposit: Optional[int] = None
    utilities_incl: Optional[bool] = None
    min_rent_months: Optional[int] = None
    allowed_students: Optional[bool] = None
    allowed_pets: Optional[bool] = None
    rent_payment: Optional[List[str]] = None

    # Sale-finance flags (main listings only; crawled sources default False)
    mortgage_ok: bool = False
    installment_ok: bool = False
    halol_ok: bool = False

    # Location extras
    city: Optional[str] = None
    microdistrict: Optional[str] = None
    jk_name: Optional[str] = None
    landmark: Optional[str] = None
    metro_station: Optional[str] = None

    # Crawler-specific fields
    amenities: Optional[List[str]] = None
    nearby_amenities: Optional[List[str]] = None
    confidence: Optional[float] = None
    source_url: Optional[str] = None  # OLX url or telegram source_channel

    # Multilingual metadata
    original_language: Optional[str] = None
    is_translated: bool = False


class UnifiedListingListItem(BaseModel):
    """Lightweight item for the mixed feed."""

    id: UUID
    source: str
    type: str
    property_type: str
    price: float
    currency: str
    # Ready-to-display human title from the shared normalization layer
    # (services/listing_normalize). Crawled rows have no DB title, so it is
    # generated ("rooms + property type + district") identically everywhere.
    title: Optional[str] = None
    rooms: Optional[int] = None
    area: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    region: Optional[str] = None
    district: Optional[str] = None
    building_type: Optional[str] = None
    condition: Optional[str] = None
    land_purpose: Optional[str] = None
    primary_image_url: Optional[str] = None
    created_at: UTCDateTime
