"""Buyer API endpoints for TikTok-style UI."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.api.v1.deps import get_current_user, get_current_user_optional
from app.core.exceptions import NotFoundException
from app.db.database import get_db
from app.db.models import (
    Favorite,
    Listing,
    ListingStatus,
    ModerationStatus,
    Seller,
    User,
)
from app.schemas.buyer import (
    BuyerListing,
    BuyerListingImage,
    BuyerListingsResponse,
    LikeToggleResponse,
)

router = APIRouter()


@router.get("/listings", response_model=BuyerListingsResponse)
async def get_buyer_listings(
    request: Request,
    PageSize: int = Query(10, ge=1, le=50, alias="PageSize"),
    PageNumber: int = Query(1, ge=1, alias="PageNumber"),
    SearchTerm: Optional[str] = Query(None, max_length=200, alias="SearchTerm"),
    CategoryId: Optional[str] = Query(None, alias="CategoryId"),
    SortingName: Optional[int] = Query(None, alias="SortingName"),
    MinPrice: Optional[int] = Query(None, ge=0, alias="MinPrice"),
    MaxPrice: Optional[int] = Query(None, le=100000000, alias="MaxPrice"),
    RegionLocation: Optional[str] = Query(None, alias="RegionLocation"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Get listings in TikTok-style format for buyer UI.

    Query parameters use PascalCase to match frontend expectations.
    """
    # Base query - only active, approved listings
    query = select(Listing).where(
        Listing.status == ListingStatus.ACTIVE,
        Listing.moderation_status == ModerationStatus.APPROVED,
        Listing.deleted_at.is_(None),
    )

    # Apply filters
    if SearchTerm:
        search_term = f"%{SearchTerm}%"
        query = query.where(
            or_(
                Listing.title.ilike(search_term),
                Listing.description.ilike(search_term),
                Listing.district.ilike(search_term),
                Listing.address.ilike(search_term),
            )
        )

    if MinPrice is not None:
        query = query.where(Listing.price >= MinPrice)

    if MaxPrice is not None:
        query = query.where(Listing.price <= MaxPrice)

    if RegionLocation:
        query = query.where(Listing.district.ilike(f"%{RegionLocation}%"))

    # Apply sorting based on SortingName
    # -1 or None = default (newest first)
    # 0 = Price low to high
    # 1 = Price high to low
    # 2 = Newest first
    if SortingName == 0:
        query = query.order_by(Listing.is_boosted.desc(), Listing.price.asc())
    elif SortingName == 1:
        query = query.order_by(Listing.is_boosted.desc(), Listing.price.desc())
    else:
        # Default: newest first
        query = query.order_by(Listing.is_boosted.desc(), Listing.created_at.desc())

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (PageNumber - 1) * PageSize
    query = query.offset(offset).limit(PageSize)

    # Load images and seller
    query = query.options(
        selectinload(Listing.images),
        joinedload(Listing.seller).joinedload(Seller.user),
    )

    # Execute query
    result = await db.execute(query)
    listings = result.unique().scalars().all()

    # Get user favorites if authenticated
    user_favorites = set()
    if current_user:
        fav_result = await db.execute(
            select(Favorite.listing_id).where(Favorite.user_id == current_user.id)
        )
        user_favorites = set(fav_result.scalars().all())

    # Build response
    lang = request.headers.get("accept-language", "ru")[:2].lower()
    if lang not in ("ru", "uz"):
        lang = "ru"
    buyer_listings = []
    for listing in listings:
        # Get seller info
        seller_name = "Unknown Seller"
        seller_image = ""
        if listing.seller:
            if listing.seller.company_name:
                seller_name = listing.seller.company_name
            elif listing.seller.user:
                seller_name = listing.seller.user.first_name
                if listing.seller.user.last_name:
                    seller_name += f" {listing.seller.user.last_name}"

            if listing.seller.logo_url:
                seller_image = listing.seller.logo_url
            elif listing.seller.user and listing.seller.user.avatar_url:
                seller_image = listing.seller.user.avatar_url

        # Build images list
        images = []
        if listing.images:
            # Sort by position and primary status
            sorted_images = sorted(
                listing.images, key=lambda x: (not x.is_primary, x.position)
            )
            for img in sorted_images:
                # Use the best available URL
                image_url = img.large_url or img.medium_url or img.original_url
                if image_url:
                    images.append(BuyerListingImage(imageUrl=image_url))

        # Resolve multilingual content
        title = getattr(listing, f"title_{lang}", None) or listing.title
        description = (
            getattr(listing, f"description_{lang}", None) or listing.description
        )

        # Build listing response
        buyer_listings.append(
            BuyerListing(
                id=str(listing.id),
                name=title
                or f"{listing.property_type.value.capitalize()} for {listing.type.value}",
                price=listing.price,
                description=description or "",
                images=images,
                sellerUserName=seller_name,
                sellerImage=seller_image,
                likes=listing.favorites_count,
                isLiked=listing.id in user_favorites,
            )
        )

    # Calculate pagination
    total_pages = (total + PageSize - 1) // PageSize
    has_more = PageNumber < total_pages

    return BuyerListingsResponse(
        listings=buyer_listings,
        listingsCount=total,
        currentPageNumber=PageNumber,
        nextPageNumber=PageNumber + 1 if has_more else None,
    )


@router.post("/listings/{listing_id}/like", response_model=LikeToggleResponse)
async def toggle_listing_like(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Toggle like (favorite) on a listing.

    If already liked, removes the like. If not liked, adds a like.
    Returns the new like state.
    """
    # Check if listing exists
    listing_query = select(Listing).where(
        Listing.id == listing_id,
        Listing.deleted_at.is_(None),
    )
    listing_result = await db.execute(listing_query)
    listing = listing_result.scalar_one_or_none()

    if not listing:
        raise NotFoundException("Listing", str(listing_id))

    # Check if already favorited
    existing_query = select(Favorite).where(
        Favorite.user_id == current_user.id,
        Favorite.listing_id == listing_id,
    )
    existing_result = await db.execute(existing_query)
    existing_favorite = existing_result.scalar_one_or_none()

    if existing_favorite:
        # Remove favorite (unlike)
        await db.delete(existing_favorite)
        listing.favorites_count = max(0, listing.favorites_count - 1)
        await db.commit()
        return LikeToggleResponse(liked=False)
    else:
        # Add favorite (like)
        favorite = Favorite(
            user_id=current_user.id,
            listing_id=listing_id,
        )
        db.add(favorite)
        listing.favorites_count += 1
        await db.commit()
        return LikeToggleResponse(liked=True)
