"""User preferences API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.db.models import NotificationPreferences, User, UserPreferences

router = APIRouter()


class UserPreferencesResponse(BaseModel):
    regions: List[str]
    districts: List[str]
    property_types: List[str]
    listing_types: List[str]
    price_min: Optional[int]
    price_max: Optional[int]
    rooms: List[int]


class UserPreferencesUpdate(BaseModel):
    regions: Optional[List[str]] = None
    districts: Optional[List[str]] = None
    property_types: Optional[List[str]] = None
    listing_types: Optional[List[str]] = None
    price_min: Optional[int] = Field(None, ge=0)
    price_max: Optional[int] = Field(None, le=100000000)
    rooms: Optional[List[int]] = None


def _to_response(prefs: Optional[UserPreferences]) -> UserPreferencesResponse:
    if not prefs:
        return UserPreferencesResponse(
            regions=[],
            districts=[],
            property_types=[],
            listing_types=[],
            price_min=None,
            price_max=None,
            rooms=[],
        )
    return UserPreferencesResponse(
        regions=prefs.regions or [],
        districts=prefs.districts or [],
        property_types=prefs.property_types or [],
        listing_types=prefs.listing_types or [],
        price_min=prefs.price_min,
        price_max=prefs.price_max,
        rooms=prefs.rooms or [],
    )


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's feed preferences."""
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    return _to_response(result.scalar_one_or_none())


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    data: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's feed preferences (upsert). Also marks onboarding as complete."""
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    prefs = result.scalar_one_or_none()

    if not prefs:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(prefs, field, value)

    # Mark onboarding as complete
    current_user.onboarding_completed = True

    # Sync filter fields to NotificationPreferences so the notification
    # matching system uses the same criteria the user selected.
    notif_result = await db.execute(
        select(NotificationPreferences).where(
            NotificationPreferences.user_id == current_user.id
        )
    )
    notif_prefs = notif_result.scalar_one_or_none()
    if not notif_prefs:
        notif_prefs = NotificationPreferences(user_id=current_user.id)
        db.add(notif_prefs)

    # Sync shared filter fields (regions is not in NotificationPreferences)
    sync_fields = [
        "districts",
        "property_types",
        "listing_types",
        "price_min",
        "price_max",
        "rooms",
    ]
    for field in sync_fields:
        if field in update_fields:
            setattr(notif_prefs, field, update_fields[field])

    await db.commit()
    await db.refresh(prefs)

    return _to_response(prefs)
