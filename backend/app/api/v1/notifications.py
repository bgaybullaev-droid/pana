"""Notifications API endpoints."""

from datetime import time
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.db.models import Notification, NotificationPreferences, NotificationType, User
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.notification import (
    NotificationActorResponse,
    NotificationMarkReadRequest,
    NotificationResponse,
)

router = APIRouter()


class NotificationPreferencesResponse(BaseModel):
    """Notification preferences response."""

    enabled: bool
    time_start: str
    time_end: str
    timezone: str
    daily_limit: int
    disabled_types: List[str]
    districts: List[str]
    property_types: List[str]
    listing_types: List[str]
    price_min: Optional[int]
    price_max: Optional[int]
    rooms: List[int]


class NotificationPreferencesUpdate(BaseModel):
    """Notification preferences update request."""

    enabled: Optional[bool] = None
    time_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    time_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    timezone: Optional[str] = Field(None, max_length=50)
    daily_limit: Optional[int] = Field(None, ge=1, le=50)
    disabled_types: Optional[List[str]] = None
    districts: Optional[List[str]] = None
    property_types: Optional[List[str]] = None
    listing_types: Optional[List[str]] = None
    price_min: Optional[int] = Field(None, ge=0)
    price_max: Optional[int] = Field(None, le=100000000)
    rooms: Optional[List[int]] = None


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's notification preferences.
    """
    query = select(NotificationPreferences).where(
        NotificationPreferences.user_id == current_user.id
    )
    result = await db.execute(query)
    prefs = result.scalar_one_or_none()

    if not prefs:
        # Return defaults
        return NotificationPreferencesResponse(
            enabled=True,
            time_start="09:00",
            time_end="21:00",
            timezone="Asia/Tashkent",
            daily_limit=10,
            disabled_types=[],
            districts=[],
            property_types=[],
            listing_types=[],
            price_min=None,
            price_max=None,
            rooms=[],
        )

    return NotificationPreferencesResponse(
        enabled=prefs.enabled,
        time_start=prefs.time_start.strftime("%H:%M") if prefs.time_start else "09:00",
        time_end=prefs.time_end.strftime("%H:%M") if prefs.time_end else "21:00",
        timezone=prefs.timezone,
        daily_limit=prefs.daily_limit,
        disabled_types=prefs.disabled_types or [],
        districts=prefs.districts or [],
        property_types=prefs.property_types or [],
        listing_types=prefs.listing_types or [],
        price_min=prefs.price_min,
        price_max=prefs.price_max,
        rooms=prefs.rooms or [],
    )


@router.put("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    data: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user's notification preferences.
    """
    query = select(NotificationPreferences).where(
        NotificationPreferences.user_id == current_user.id
    )
    result = await db.execute(query)
    prefs = result.scalar_one_or_none()

    if not prefs:
        # Create new preferences
        prefs = NotificationPreferences(user_id=current_user.id)
        db.add(prefs)

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "time_start" and value:
            hour, minute = map(int, value.split(":"))
            setattr(prefs, field, time(hour, minute))
        elif field == "time_end" and value:
            hour, minute = map(int, value.split(":"))
            setattr(prefs, field, time(hour, minute))
        else:
            setattr(prefs, field, value)

    await db.commit()
    await db.refresh(prefs)

    return NotificationPreferencesResponse(
        enabled=prefs.enabled,
        time_start=prefs.time_start.strftime("%H:%M") if prefs.time_start else "09:00",
        time_end=prefs.time_end.strftime("%H:%M") if prefs.time_end else "21:00",
        timezone=prefs.timezone,
        daily_limit=prefs.daily_limit,
        disabled_types=prefs.disabled_types or [],
        districts=prefs.districts or [],
        property_types=prefs.property_types or [],
        listing_types=prefs.listing_types or [],
        price_min=prefs.price_min,
        price_max=prefs.price_max,
        rooms=prefs.rooms or [],
    )


# =============================================================================
# In-app Notifications
# =============================================================================


def build_notification_response(notification: Notification) -> NotificationResponse:
    """Build notification response from model."""
    actor = None
    if notification.actor:
        actor = NotificationActorResponse(
            id=notification.actor.id,
            first_name=notification.actor.first_name,
            last_name=notification.actor.last_name,
            username=notification.actor.username,
            avatar_url=notification.actor.avatar_url,
        )

    # Back-fill source for legacy rows (created before the column
    # existed) so the frontend can always switch on a non-null value.
    source = notification.source
    if source is None and notification.type == NotificationType.NEW_LISTING:
        title = notification.title or ""
        if "поиску" in title or "Qidiruv" in title:
            source = "saved_search"
        else:
            source = "preferences"

    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        type=notification.type.value,
        source=source,
        title=notification.title,
        message=notification.message,
        listing_id=notification.listing_id,
        comment_id=notification.comment_id,
        actor=actor,
        read=notification.read,
        created_at=notification.created_at,
    )


@router.get("", response_model=PaginatedResponse[NotificationResponse])
async def get_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's notifications.

    Returns paginated list of notifications for the current user.
    """
    # Base query for user's notifications
    base_query = select(Notification).where(Notification.user_id == current_user.id)

    if unread_only:
        base_query = base_query.where(Notification.read.is_(False))

    # Count total
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated notifications
    offset = (page - 1) * per_page
    query = (
        base_query.order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .options(selectinload(Notification.actor))
    )
    result = await db.execute(query)
    notifications = result.scalars().all()

    # Build response
    items = [build_notification_response(n) for n in notifications]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get count of unread notifications.
    """
    query = select(func.count()).where(
        Notification.user_id == current_user.id,
        Notification.read.is_(False),
    )
    result = await db.execute(query)
    count = result.scalar() or 0

    return {"unread_count": count}


@router.post("/mark-read", response_model=MessageResponse)
async def mark_notifications_read(
    data: NotificationMarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark notifications as read.

    If notification_ids is provided, marks only those notifications.
    If notification_ids is None/empty, marks all notifications as read.
    """
    if data.notification_ids:
        # Mark specific notifications as read
        query = (
            update(Notification)
            .where(
                Notification.user_id == current_user.id,
                Notification.id.in_(data.notification_ids),
            )
            .values(read=True)
        )
    else:
        # Mark all notifications as read
        query = (
            update(Notification)
            .where(Notification.user_id == current_user.id)
            .values(read=True)
        )

    await db.execute(query)
    await db.commit()

    return MessageResponse(message="Notifications marked as read", success=True)


@router.delete("/{notification_id}", response_model=MessageResponse)
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a notification.
    """
    query = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    )
    result = await db.execute(query)
    notification = result.scalar_one_or_none()

    if not notification:
        return MessageResponse(message="Notification not found", success=False)

    await db.delete(notification)
    await db.commit()

    return MessageResponse(message="Notification deleted", success=True)
