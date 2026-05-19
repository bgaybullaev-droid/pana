"""Buyer API endpoints for TikTok-style UI."""

from typing import List, Optional
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
    SavedSearch,
    Seller,
    User,
)
from app.schemas.buyer import (
    BuyerListing,
    BuyerListingImage,
    BuyerListingsResponse,
    LikeToggleResponse,
)
from app.schemas.common import PaginatedResponse
from app.schemas.listing import ListingListResponse
from app.services.recommendations import get_recommended_listings

router = APIRouter()


def _build_list_response(
    listing: Listing,
    *,
    lang: str,
    user_favorites: set,
) -> ListingListResponse:
    """Build a ListingListResponse matching the shape used by /listings/feed.

    Localizes title against the caller's content language, joins the
    seller for the ``is_verified`` badge, and picks the primary image
    (or the first image when no primary is flagged) for the card
    thumbnail.
    """
    primary_image = next(
        (img for img in listing.images if img.is_primary),
        listing.images[0] if listing.images else None,
    )
    localized_title = (
        getattr(listing, f"title_{lang}", None) or listing.title
    )
    return ListingListResponse(
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
        title=localized_title,
        views_count=listing.views_count,
        favorites_count=listing.favorites_count,
        comments_count=listing.comments_count,
        is_boosted=listing.is_boosted,
        is_highlighted=listing.is_highlighted,
        created_at=listing.created_at,
        primary_image_url=primary_image.medium_url if primary_image else None,
        is_favorited=listing.id in user_favorites,
        rent_period=listing.rent_period,
        land_area=listing.land_area,
        mortgage_ok=listing.mortgage_ok,
        installment_ok=listing.installment_ok,
        halol_ok=listing.halol_ok,
        urgent_flag=None,
        is_verified=(listing.seller.is_verified if listing.seller else None),
    )


def _get_content_language(request: Request) -> str:
    """Two-letter content language (ru/uz), defaulting to ru."""
    header = request.headers.get("accept-language", "ru")
    lang = header[:2].lower()
    return lang if lang in ("ru", "uz") else "ru"


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


# =============================================================================
# F048 — Subscriptions tab on the buyer home feed
# =============================================================================
@router.get(
    "/feed/subscriptions",
    response_model=PaginatedResponse[ListingListResponse],
)
async def get_subscriptions_feed(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Active listings matching ANY of the caller's saved searches.

    Each ``SavedSearch.filters`` dict is converted into a SQL predicate;
    the resulting per-search predicates are OR-ed together. Listings are
    returned newest-first. If the user has no saved searches we return
    an empty page so the frontend can render a friendly empty state.
    """
    # Pull the user's saved searches.
    saved_q = select(SavedSearch).where(SavedSearch.user_id == current_user.id)
    saved_res = await db.execute(saved_q)
    saved_searches: List[SavedSearch] = list(saved_res.scalars().all())

    if not saved_searches:
        return PaginatedResponse.create(
            items=[], total=0, page=page, per_page=per_page
        )

    # Build the listing base query (same eligibility as /listings/feed).
    base_query = select(Listing).where(
        Listing.status == ListingStatus.ACTIVE,
        Listing.moderation_status == ModerationStatus.APPROVED,
        Listing.deleted_at.is_(None),
        Listing.master_record_id.is_(None),
    )

    # Build per-search predicate, then OR them together.
    # The saved-search filter dict is the same shape the frontend posts to
    # /saved-searches; we support the fields the buyer home filter UI
    # writes: deal_type, property_type, rooms, price_min, price_max,
    # district, region, plus the free-text query.
    per_search_clauses = []
    for s in saved_searches:
        f = s.filters or {}
        clauses = []
        deal_type = f.get("deal_type") or f.get("type")
        if deal_type:
            clauses.append(Listing.type == deal_type)
        prop_type = f.get("property_type")
        if prop_type:
            clauses.append(Listing.property_type == prop_type)
        rooms = f.get("rooms")
        if rooms:
            clauses.append(Listing.rooms.in_(rooms))
        price_min = f.get("price_min")
        if price_min is not None:
            clauses.append(Listing.price >= price_min)
        price_max = f.get("price_max")
        if price_max is not None:
            clauses.append(Listing.price <= price_max)
        region = f.get("region")
        if region:
            if isinstance(region, list):
                clauses.append(Listing.region.in_(region))
            else:
                clauses.append(Listing.region == region)
        district = f.get("district")
        if district:
            if isinstance(district, list):
                clauses.append(Listing.district.in_(district))
            else:
                clauses.append(Listing.district == district)
        q_text = s.query
        if q_text:
            search_term = f"%{q_text}%"
            clauses.append(
                or_(
                    Listing.title.ilike(search_term),
                    Listing.description.ilike(search_term),
                    Listing.district.ilike(search_term),
                    Listing.address.ilike(search_term),
                )
            )

        if clauses:
            # A saved search with N clauses requires ALL of them to match
            # (within-search AND). Across saved searches we OR.
            from sqlalchemy import and_ as _and

            per_search_clauses.append(_and(*clauses))
        else:
            # A truly empty saved search (no filters, no query) matches
            # every active listing — preserve that.
            per_search_clauses.append(Listing.id.is_not(None))

    query = base_query.where(or_(*per_search_clauses))

    # Total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Page
    offset = (page - 1) * per_page
    query = (
        query.order_by(Listing.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .options(selectinload(Listing.images), selectinload(Listing.seller))
    )
    listings = list((await db.execute(query)).scalars().all())

    # Favorites for the badge.
    fav_res = await db.execute(
        select(Favorite.listing_id).where(Favorite.user_id == current_user.id)
    )
    user_favorites = set(fav_res.scalars().all())

    lang = _get_content_language(request)
    items = [
        _build_list_response(listing, lang=lang, user_favorites=user_favorites)
        for listing in listings
    ]

    return PaginatedResponse.create(
        items=items, total=total, page=page, per_page=per_page
    )


# =============================================================================
# F077 Phase 2 — Recommended tab on the buyer home feed
# =============================================================================
@router.get(
    "/feed/recommended",
    response_model=PaginatedResponse[ListingListResponse],
)
async def get_recommended_feed(
    request: Request,
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Personalised listing feed for the buyer Recommended tab.

    Delegates scoring to ``services.recommendations`` — see that
    module's docstring for the algorithm. Users with no view history
    get a graceful fallback (newest-first feed slice) so the tab is
    never empty.
    """
    listings = await get_recommended_listings(
        db=db, user_id=current_user.id, limit=limit
    )

    # Favorites for the badge.
    fav_res = await db.execute(
        select(Favorite.listing_id).where(Favorite.user_id == current_user.id)
    )
    user_favorites = set(fav_res.scalars().all())

    lang = _get_content_language(request)
    items = [
        _build_list_response(listing, lang=lang, user_favorites=user_favorites)
        for listing in listings
    ]

    # The recommended endpoint is not paginated — the algorithm scores
    # a top-N slice in memory — but we keep the response shape compatible
    # with `/listings/feed` (PaginatedResponse). `page=1` + `total = len(items)`
    # makes the UI's "load more" guard happy without misrepresenting the
    # result set.
    return PaginatedResponse.create(
        items=items, total=len(items), page=1, per_page=max(limit, len(items) or 1)
    )
