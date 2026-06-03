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

    # Property attributes
    building_type: Optional[str] = None  # new / secondary
    condition: Optional[str] = None  # euro / cosmetic / needs_repair / rough
    land_purpose: Optional[str] = None  # private / industrial

    # Sale-finance flags (main listings only; crawled sources default False)
    mortgage_ok: bool = False
    installment_ok: bool = False
    halol_ok: bool = False

    # Crawler-specific fields
    amenities: Optional[List[str]] = None
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
