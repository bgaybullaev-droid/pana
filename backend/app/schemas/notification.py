"""Notification schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import UTCDateTime


class NotificationActorResponse(BaseModel):
    """Actor (user who triggered notification) response."""

    id: UUID
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    """Notification response schema."""

    id: UUID
    user_id: UUID
    type: str
    # Discriminator for new_listing notifications: "saved_search" |
    # "preferences". Null for legacy rows or types that don't split by
    # source. The frontend MUST key UI off this field, not the title.
    source: Optional[str] = None
    title: str
    message: str
    listing_id: Optional[UUID] = None
    comment_id: Optional[UUID] = None
    actor: Optional[NotificationActorResponse] = None
    read: bool
    created_at: UTCDateTime

    class Config:
        from_attributes = True


class NotificationMarkReadRequest(BaseModel):
    """Request to mark notifications as read."""

    notification_ids: Optional[list[UUID]] = None  # None means mark all as read
