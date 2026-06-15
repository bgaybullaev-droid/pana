"""Seller schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import UTCDateTime


class SellerBase(BaseModel):
    """Base seller schema."""

    company_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    phone: str = Field(..., pattern=r"^\+998\d{9}$")
    email: Optional[EmailStr] = None
    phone_public: bool = True
    telegram_username: Optional[str] = Field(None, max_length=100)
    instagram_url: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=500)


class SellerCreate(SellerBase):
    """Schema for creating a seller."""

    pass


class SellerUpdate(BaseModel):
    """Schema for updating a seller."""

    company_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    email: Optional[EmailStr] = None
    phone_public: Optional[bool] = None
    telegram_username: Optional[str] = Field(None, max_length=100)
    instagram_url: Optional[str] = Field(None, max_length=500)
    website_url: Optional[str] = Field(None, max_length=500)


class SellerResponse(SellerBase):
    """Full seller response schema."""

    # Mini App sellers are created before a phone is shared — the column is
    # nullable in DB, so the response schema must accept None. Overrides the
    # strict `phone: str` from SellerBase.
    phone: Optional[str] = None

    id: UUID
    user_id: UUID
    logo_url: Optional[str]
    is_verified: bool
    verified_at: Optional[UTCDateTime]
    listings_count: int
    total_views: int
    total_contacts: int
    # Live portfolio favorites total. Defaults to 0 so the lighter response
    # builders (register/patch) don't have to compute it; GET /me fills it in
    # from the canonical Favorite table.
    total_favorites: int = 0
    created_at: UTCDateTime
    updated_at: UTCDateTime

    model_config = {"from_attributes": True}


class SellerPublicResponse(BaseModel):
    """Public seller profile response."""

    id: UUID
    company_name: Optional[str]
    description: Optional[str]
    logo_url: Optional[str]
    phone: Optional[str]  # Only if phone_public is True
    telegram_username: Optional[str]
    instagram_url: Optional[str]
    website_url: Optional[str]
    is_verified: bool
    listings_count: int
    created_at: UTCDateTime

    model_config = {"from_attributes": True}


class SellerRegistrationRequest(BaseModel):
    """Seller registration request."""

    phone: str = Field(..., pattern=r"^\+998\d{9}$")
    company_name: Optional[str] = Field(None, max_length=200)


class SellerVerifyPhoneRequest(BaseModel):
    """Verify seller phone request."""

    otp_code: str = Field(..., min_length=6, max_length=6)


class SellerPhoneUpdateRequest(BaseModel):
    """Update user phone number for crawled listings matching."""

    phone: str = Field(..., pattern=r"^\+998\d{9}$")


class SellerCrawledStatsResponse(BaseModel):
    """Stats for a seller's crawled listings across platforms."""

    olx_count: int
    telegram_count: int
    total_count: int
