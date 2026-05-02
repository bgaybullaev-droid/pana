"""Crawler import and response schemas."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import UTCDateTime

# =============================================================================
# Telegram Crawler Schemas
# =============================================================================


class TelegramListingImport(BaseModel):
    """Schema for importing a single Telegram crawler listing."""

    property_type: str = Field(..., max_length=50)
    listing_type: str = Field(..., max_length=50)
    price: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=10)
    rooms: Optional[int] = Field(None, ge=0, le=20)
    area_sqm: Optional[float] = Field(None, gt=0, le=1000000)
    floor: Optional[int] = Field(None, ge=-5, le=100)
    total_floors: Optional[int] = Field(None, ge=1, le=100)
    building_type: Optional[str] = Field(None, max_length=50)
    condition: Optional[str] = Field(None, max_length=50)
    land_purpose: Optional[str] = Field(None, max_length=50)
    district: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    images: Optional[list] = None
    raw_text: Optional[str] = None
    source_channel: Optional[str] = Field(None, max_length=200)
    message_id: Optional[int] = None
    original_language: Optional[str] = Field(None, max_length=5)


class TelegramBulkImport(BaseModel):
    """Bulk import request for Telegram listings."""

    listings: List[TelegramListingImport] = Field(..., min_length=1, max_length=100)


class TelegramListingResponse(BaseModel):
    """Response schema for a Telegram listing."""

    id: UUID
    property_type: str
    listing_type: str
    price: float
    currency: str
    rooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    district: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    contact_phone: Optional[str] = None
    confidence: Optional[float] = None
    images: Optional[list] = None
    raw_text: Optional[str] = None
    source_channel: Optional[str] = None
    message_id: Optional[int] = None
    signature_hash: Optional[str] = None
    created_at: UTCDateTime
    updated_at: UTCDateTime

    model_config = {"from_attributes": True}


# =============================================================================
# OLX Crawler Schemas
# =============================================================================


class OLXListingImport(BaseModel):
    """Schema for importing a single OLX crawler listing."""

    # OLX required fields
    olx_id: str = Field(..., max_length=50)
    url: str = Field(..., max_length=500)
    crawled_at: UTCDateTime

    # Core listing fields
    property_type: str = Field(..., max_length=50)
    listing_type: str = Field(..., max_length=50)
    price: float = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=10)
    rooms: Optional[int] = Field(None, ge=0, le=20)
    area_sqm: Optional[float] = Field(None, gt=0, le=1000000)
    floor: Optional[int] = Field(None, ge=-5, le=100)
    total_floors: Optional[int] = Field(None, ge=1, le=100)
    district: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    contact_phone: Optional[str] = Field(None, max_length=20)
    confidence: Optional[float] = Field(None, ge=0, le=1)
    images: Optional[list] = None

    # OLX source info
    source: str = Field(default="olx_uz", max_length=50)

    # OLX-specific fields
    seller_type: Optional[str] = Field(None, max_length=20)
    seller_name: Optional[str] = Field(None, max_length=200)
    views_count: Optional[int] = Field(None, ge=0)
    posted_date: Optional[str] = Field(None, max_length=100)
    building_type: Optional[str] = Field(None, max_length=100)
    condition: Optional[str] = Field(None, max_length=100)
    land_purpose: Optional[str] = Field(None, max_length=50)
    furnishing: Optional[str] = Field(None, max_length=100)
    ceiling_height: Optional[float] = Field(None, gt=0, le=10)
    bathroom: Optional[str] = Field(None, max_length=100)
    raw_text: Optional[str] = None
    original_language: Optional[str] = Field(None, max_length=5)


class OLXBulkImport(BaseModel):
    """Bulk import request for OLX listings."""

    listings: List[OLXListingImport] = Field(..., min_length=1, max_length=100)


class OLXListingResponse(BaseModel):
    """Response schema for an OLX listing."""

    id: UUID
    olx_id: str
    url: str
    property_type: str
    listing_type: str
    price: float
    currency: str
    rooms: Optional[int] = None
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    district: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    amenities: Optional[List[str]] = None
    contact_phone: Optional[str] = None
    confidence: Optional[float] = None
    images: Optional[list] = None
    source: str
    crawled_at: UTCDateTime
    seller_type: Optional[str] = None
    seller_name: Optional[str] = None
    views_count: Optional[int] = None
    posted_date: Optional[str] = None
    building_type: Optional[str] = None
    condition: Optional[str] = None
    furnishing: Optional[str] = None
    ceiling_height: Optional[float] = None
    bathroom: Optional[str] = None
    raw_text: Optional[str] = None
    signature_hash: Optional[str] = None
    created_at: UTCDateTime
    updated_at: UTCDateTime

    model_config = {"from_attributes": True}


# =============================================================================
# Shared Schemas
# =============================================================================


class CrawlerImportItemResult(BaseModel):
    """Result for a single listing import."""

    index: int
    success: bool
    listing_id: Optional[str] = None
    error: Optional[str] = None
    is_duplicate: bool = False
    is_updated: bool = False


class CrawlerImportResult(BaseModel):
    """Response for bulk import."""

    total: int
    created: int
    updated: int = 0
    duplicates: int
    errors: int
    results: List[CrawlerImportItemResult]
