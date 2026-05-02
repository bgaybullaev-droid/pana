"""Favorites API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_user
from app.api.v1.helpers import find_listing_any_source
from app.core.exceptions import NotFoundException
from app.db.database import get_db
from app.db.models import (
    Favorite,
    Listing,
    Notification,
    NotificationType,
    OLXListing,
    TelegramListing,
    User,
    UserPreferences,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.listing import ListingListResponse

router = APIRouter()


def _crawler_to_list_response(
    listing, source: str, is_favorited: bool = True
) -> ListingListResponse:
    """Build a ListingListResponse from a TelegramListing or OLXListing."""
    images = getattr(listing, "images", None) or []
    primary_image_url = None
    if images:
        if isinstance(images, list) and len(images) > 0:
            first = images[0]
            if isinstance(first, str):
                primary_image_url = first
            elif isinstance(first, dict):
                primary_image_url = first.get("url") or first.get("thumbnail")

    return ListingListResponse(
        id=listing.id,
        type=getattr(listing, "type", "sell") or "sell",
        property_type=getattr(listing, "property_type", "apartment") or "apartment",
        rooms=getattr(listing, "rooms", None),
        area=getattr(listing, "area", None),
        floor=getattr(listing, "floor", None),
        total_floors=getattr(listing, "total_floors", None),
        district=getattr(listing, "district", None),
        price=getattr(listing, "price", 0) or 0,
        currency=getattr(listing, "currency", "USD") or "USD",
        title=getattr(listing, "description", None),
        views_count=0,
        favorites_count=0,
        comments_count=0,
        is_boosted=False,
        is_highlighted=False,
        created_at=listing.created_at,
        primary_image_url=primary_image_url,
        is_favorited=is_favorited,
    )


@router.get("/ids")
async def get_favorite_ids(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all favorited listing IDs for the current user.

    Returns a lightweight list of UUIDs (no pagination, no listing data).
    """
    query = (
        select(Favorite.listing_id)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
    )
    result = await db.execute(query)
    ids = [str(row[0]) for row in result.all()]
    return {"ids": ids}


@router.get("", response_model=PaginatedResponse[ListingListResponse])
async def get_favorites(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user's favorite listings.

    Returns paginated list of favorited listings from all sources.
    """
    # Count total favorites
    count_query = select(func.count()).where(Favorite.user_id == current_user.id)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get favorites
    offset = (page - 1) * per_page
    query = (
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    favorites = result.scalars().all()

    # Collect listing IDs
    listing_ids = [fav.listing_id for fav in favorites]
    if not listing_ids:
        return PaginatedResponse.create(
            items=[], total=total, page=page, per_page=per_page
        )

    # Batch-fetch main listings
    main_query = (
        select(Listing)
        .where(Listing.id.in_(listing_ids), Listing.deleted_at.is_(None))
        .options(selectinload(Listing.images))
    )
    main_result = await db.execute(main_query)
    main_map = {item.id: item for item in main_result.scalars().all()}

    # IDs not found in main
    remaining_ids = [lid for lid in listing_ids if lid not in main_map]

    tg_map = {}
    olx_map = {}

    if remaining_ids:
        tg_result = await db.execute(
            select(TelegramListing).where(TelegramListing.id.in_(remaining_ids))
        )
        tg_map = {item.id: item for item in tg_result.scalars().all()}

        still_remaining = [lid for lid in remaining_ids if lid not in tg_map]
        if still_remaining:
            olx_result = await db.execute(
                select(OLXListing).where(OLXListing.id.in_(still_remaining))
            )
            olx_map = {item.id: item for item in olx_result.scalars().all()}

    # Build response in original order
    items = []
    for fav in favorites:
        lid = fav.listing_id

        if lid in main_map:
            listing = main_map[lid]
            primary_image = next(
                (img for img in listing.images if img.is_primary),
                listing.images[0] if listing.images else None,
            )
            items.append(
                ListingListResponse(
                    id=listing.id,
                    type=listing.type.value,
                    property_type=listing.property_type.value,
                    rooms=listing.rooms,
                    area=listing.area,
                    floor=listing.floor,
                    total_floors=listing.total_floors,
                    region=listing.region,
                    district=listing.district,
                    price=listing.price,
                    currency=listing.currency.value,
                    title=listing.title,
                    views_count=listing.views_count,
                    favorites_count=listing.favorites_count,
                    is_boosted=listing.is_boosted,
                    is_highlighted=listing.is_highlighted,
                    created_at=listing.created_at,
                    primary_image_url=(
                        primary_image.medium_url if primary_image else None
                    ),
                    is_favorited=True,
                )
            )
        elif lid in tg_map:
            items.append(_crawler_to_list_response(tg_map[lid], "telegram"))
        elif lid in olx_map:
            items.append(_crawler_to_list_response(olx_map[lid], "olx"))
        # Skip if listing was deleted / not found in any table

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


async def _merge_listing_into_preferences(
    db: AsyncSession,
    user_id,
    listing,
) -> None:
    """Merge favorited listing's metadata into user preferences (set-union)."""
    # Extract metadata from any listing source
    if isinstance(listing, Listing):
        listing_type = listing.type.value  # enum → "sell"/"rent"
        property_type = listing.property_type.value  # enum → "apartment"/etc
    else:
        listing_type = getattr(listing, "listing_type", None) or getattr(
            listing, "type", None
        )
        property_type = getattr(listing, "property_type", None)

    region = getattr(listing, "region", None)
    district = getattr(listing, "district", None)

    # Nothing to merge if all fields are empty
    if not any([region, district, property_type, listing_type]):
        return

    # Load or create preferences
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = UserPreferences(user_id=user_id)
        db.add(prefs)

    # Set-union merge (add if not already present)
    if region and region not in (prefs.regions or []):
        prefs.regions = [*(prefs.regions or []), region]
    if district and district not in (prefs.districts or []):
        prefs.districts = [*(prefs.districts or []), district]
    if property_type and property_type not in (prefs.property_types or []):
        prefs.property_types = [*(prefs.property_types or []), property_type]
    if listing_type and listing_type not in (prefs.listing_types or []):
        prefs.listing_types = [*(prefs.listing_types or []), listing_type]


@router.post("/{listing_id}", response_model=MessageResponse, status_code=201)
async def add_favorite(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a listing to favorites (any source).
    """
    # Check if listing exists in any source
    listing = await find_listing_any_source(db, listing_id)
    if not listing:
        raise NotFoundException("Listing", str(listing_id))

    # Check if already favorited
    existing_query = select(Favorite).where(
        Favorite.user_id == current_user.id,
        Favorite.listing_id == listing_id,
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        return MessageResponse(message="Already in favorites")

    # Create favorite
    favorite = Favorite(
        user_id=current_user.id,
        listing_id=listing_id,
    )
    db.add(favorite)

    # Update listing favorites count (only main listings track this)
    if isinstance(listing, Listing):
        listing.favorites_count += 1

        # Create notification for the listing owner (if not self-favoriting)
        if listing.seller_id and listing.seller_id != current_user.id:
            # Look up the seller's user_id
            from app.db.models import Seller

            seller_query = select(Seller).where(Seller.id == listing.seller_id)
            seller_result = await db.execute(seller_query)
            seller = seller_result.scalar_one_or_none()
            if seller and seller.user_id != current_user.id:
                # Load seller's user to get language preference
                seller_user_query = select(User).where(User.id == seller.user_id)
                seller_user_result = await db.execute(seller_user_query)
                seller_user = seller_user_result.scalar_one_or_none()

                from app.workers.tasks.notifications import (
                    _FAVORITE_UPDATE_MESSAGE,
                    _FAVORITE_UPDATE_TITLE,
                )

                lang = (
                    seller_user.language
                    if seller_user and seller_user.language in ("ru", "uz")
                    else "ru"
                )

                notification = Notification(
                    user_id=seller.user_id,
                    type=NotificationType.FAVORITE_UPDATE,
                    title=_FAVORITE_UPDATE_TITLE[lang],
                    message=_FAVORITE_UPDATE_MESSAGE[lang].format(
                        name=current_user.first_name
                    ),
                    listing_id=listing_id,
                    actor_id=current_user.id,
                )
                db.add(notification)

    # Merge listing metadata into user preferences (set-union)
    await _merge_listing_into_preferences(db, current_user.id, listing)

    await db.commit()

    return MessageResponse(message="Added to favorites")


@router.delete("/{listing_id}", response_model=MessageResponse)
async def remove_favorite(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a listing from favorites.
    """
    # Find favorite
    query = select(Favorite).where(
        Favorite.user_id == current_user.id,
        Favorite.listing_id == listing_id,
    )
    result = await db.execute(query)
    favorite = result.scalar_one_or_none()

    if not favorite:
        raise NotFoundException("Favorite")

    # Update listing favorites count (only main listings)
    listing_query = select(Listing).where(Listing.id == listing_id)
    listing_result = await db.execute(listing_query)
    listing = listing_result.scalar_one_or_none()
    if listing:
        listing.favorites_count = max(0, listing.favorites_count - 1)

    await db.delete(favorite)
    await db.commit()

    return MessageResponse(message="Removed from favorites")
