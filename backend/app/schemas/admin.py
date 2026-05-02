"""Admin panel schemas."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import UTCDateTime
from app.schemas.listing import ListingImageResponse


class AdminUserListResponse(BaseModel):
    """Admin user list item response."""

    id: UUID
    telegram_id: Optional[int] = None
    phone: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    role: str
    approval_status: str
    created_at: UTCDateTime

    model_config = {"from_attributes": True}


class AdminUserResponse(BaseModel):
    """Admin user detail response."""

    id: UUID
    telegram_id: Optional[int] = None
    phone: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    language: str
    role: str
    approval_status: str
    approval_notes: Optional[str] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[UTCDateTime] = None
    onboarding_completed: bool
    created_at: UTCDateTime
    updated_at: UTCDateTime

    model_config = {"from_attributes": True}


class UserApprovalRequest(BaseModel):
    """User approval/rejection request."""

    notes: Optional[str] = Field(None, max_length=1000)


class AdminListingListResponse(BaseModel):
    """Admin listing list item response."""

    id: UUID
    seller_id: Optional[UUID] = None
    seller_name: Optional[str] = None
    type: str
    property_type: str
    title: Optional[str] = None
    price: int
    currency: str
    region: Optional[str] = None
    district: Optional[str] = None
    source_type: str
    moderation_status: str
    moderation_notes: Optional[str] = None
    created_at: UTCDateTime
    primary_image_url: Optional[str] = None

    model_config = {"from_attributes": True}


class AdminListingResponse(BaseModel):
    """Admin listing detail response."""

    id: UUID
    seller_id: Optional[UUID] = None
    seller_name: Optional[str] = None
    seller_phone: Optional[str] = None
    type: str
    property_type: str
    rooms: Optional[int] = None
    area: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    region: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price: int
    currency: str
    title: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    source_type: str
    source_url: Optional[str] = None
    raw_text: Optional[str] = None
    status: str
    moderation_status: str
    moderation_notes: Optional[str] = None
    moderated_by: Optional[UUID] = None
    moderated_at: Optional[UTCDateTime] = None
    created_at: UTCDateTime
    updated_at: UTCDateTime
    images: List[ListingImageResponse] = []

    model_config = {"from_attributes": True}


class ListingModerationRequest(BaseModel):
    """Listing moderation request."""

    notes: Optional[str] = Field(None, max_length=1000)


class AdminDashboardStats(BaseModel):
    """Admin dashboard statistics."""

    pending_users: int
    total_users: int
    pending_listings: int
    total_listings: int
    approved_users: int
    rejected_users: int
    approved_listings: int
    rejected_listings: int
