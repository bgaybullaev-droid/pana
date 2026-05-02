"""Sellers API endpoints."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_seller, get_current_user
from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.db.database import get_db
from app.db.models import (
    Listing,
    ListingStatus,
    ModerationStatus,
    Seller,
    User,
    UserApprovalStatus,
    UserRole,
)
from app.schemas.common import PaginatedResponse
from app.schemas.crawler import OLXListingResponse, TelegramListingResponse
from app.schemas.listing import ListingListResponse, SellerListingListResponse
from app.schemas.seller import (
    SellerCrawledStatsResponse,
    SellerPhoneUpdateRequest,
    SellerPublicResponse,
    SellerRegistrationRequest,
    SellerResponse,
    SellerUpdate,
)
from app.services.seller_crawled_listings import (
    get_crawled_stats,
    get_crawled_stats_by_channel,
    get_olx_listings,
    get_telegram_listings,
    get_telegram_listings_by_channel,
)
from app.utils.phone import normalize_phone

router = APIRouter()


class _SellerMatchContext:
    """How to match crawled listings for a seller."""

    def __init__(
        self, phone_suffix: str | None = None, channel_name: str | None = None
    ):
        self.phone_suffix = phone_suffix
        self.channel_name = channel_name


async def _get_seller_match_context(
    user: User, db: AsyncSession
) -> _SellerMatchContext:
    """Determine how to match crawled listings based on seller type."""
    query = select(Seller).where(Seller.user_id == user.id)
    result = await db.execute(query)
    seller = result.scalar_one_or_none()

    phone_suffix = None
    channel_name = None

    # Check for channel-based matching
    if seller and seller.source_channel:
        channel_name = seller.source_channel

    # Check for phone-based matching
    phone = (seller.phone if seller else None) or user.phone
    if phone:
        suffix = normalize_phone(phone)
        if suffix and len(suffix) == 9:
            phone_suffix = suffix

    if not phone_suffix and not channel_name:
        raise BadRequestException(
            "No phone or channel linked for crawled listing matching"
        )

    return _SellerMatchContext(phone_suffix=phone_suffix, channel_name=channel_name)


@router.post("/register", response_model=SellerResponse, status_code=201)
async def register_seller(
    data: SellerRegistrationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register as a seller.

    Creates seller profile for authenticated user.
    """
    # Check if already a seller
    existing_query = select(Seller).where(Seller.user_id == current_user.id)
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise ConflictException("User is already registered as seller")

    # Check if phone is already used by another seller
    phone_query = select(Seller).where(Seller.phone == data.phone)
    phone_result = await db.execute(phone_query)
    if phone_result.scalar_one_or_none():
        raise ConflictException("Phone number already registered to another seller")

    # Create seller
    seller = Seller(
        user_id=current_user.id,
        phone=data.phone,
        company_name=data.company_name,
    )
    db.add(seller)

    # Update user role and status
    current_user.role = UserRole.SELLER
    current_user.phone = data.phone
    current_user.onboarding_completed = True
    if settings.auto_approve_users:
        current_user.approval_status = UserApprovalStatus.APPROVED
        current_user.approved_at = datetime.utcnow()

    await db.commit()
    await db.refresh(seller)

    return SellerResponse(
        id=seller.id,
        user_id=seller.user_id,
        company_name=seller.company_name,
        description=seller.description,
        logo_url=seller.logo_url,
        phone=seller.phone,
        email=seller.email,
        phone_public=seller.phone_public,
        telegram_username=seller.telegram_username,
        instagram_url=seller.instagram_url,
        website_url=seller.website_url,
        is_verified=seller.is_verified,
        verified_at=seller.verified_at,
        listings_count=seller.listings_count,
        total_views=seller.total_views,
        total_contacts=seller.total_contacts,
        created_at=seller.created_at,
        updated_at=seller.updated_at,
    )


@router.get("/me", response_model=SellerResponse)
async def get_current_seller_profile(
    seller: Seller = Depends(get_current_seller),
):
    """
    Get current seller's profile.
    """
    return SellerResponse(
        id=seller.id,
        user_id=seller.user_id,
        company_name=seller.company_name,
        description=seller.description,
        logo_url=seller.logo_url,
        phone=seller.phone,
        email=seller.email,
        phone_public=seller.phone_public,
        telegram_username=seller.telegram_username,
        instagram_url=seller.instagram_url,
        website_url=seller.website_url,
        is_verified=seller.is_verified,
        verified_at=seller.verified_at,
        listings_count=seller.listings_count,
        total_views=seller.total_views,
        total_contacts=seller.total_contacts,
        created_at=seller.created_at,
        updated_at=seller.updated_at,
    )


@router.patch("/me", response_model=SellerResponse)
async def update_current_seller_profile(
    data: SellerUpdate,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current seller's profile.
    """
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(seller, field, value)

    seller.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(seller)

    return SellerResponse(
        id=seller.id,
        user_id=seller.user_id,
        company_name=seller.company_name,
        description=seller.description,
        logo_url=seller.logo_url,
        phone=seller.phone,
        email=seller.email,
        phone_public=seller.phone_public,
        telegram_username=seller.telegram_username,
        instagram_url=seller.instagram_url,
        website_url=seller.website_url,
        is_verified=seller.is_verified,
        verified_at=seller.verified_at,
        listings_count=seller.listings_count,
        total_views=seller.total_views,
        total_contacts=seller.total_contacts,
        created_at=seller.created_at,
        updated_at=seller.updated_at,
    )


@router.get("/me/listings", response_model=PaginatedResponse[SellerListingListResponse])
async def get_seller_listings(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str = Query(None, pattern="^(active|paused|sold|expired)$"),
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current seller's listings.
    """
    # Base query
    query = select(Listing).where(
        Listing.seller_id == seller.id,
        Listing.deleted_at.is_(None),
    )

    if status:
        query = query.where(Listing.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = (
        query.order_by(Listing.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .options(selectinload(Listing.images))
    )

    result = await db.execute(query)
    listings = result.scalars().all()

    items = []
    for listing in listings:
        primary_image = next(
            (img for img in listing.images if img.is_primary),
            listing.images[0] if listing.images else None,
        )
        items.append(
            SellerListingListResponse(
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
                primary_image_url=primary_image.medium_url if primary_image else None,
                status=listing.status.value,
                contacts_count=listing.contacts_count,
                source_type=listing.source_type.value if listing.source_type else None,
            )
        )

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.put("/me/phone", response_model=SellerCrawledStatsResponse)
async def update_seller_phone(
    data: SellerPhoneUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the current user's phone number and return crawled listing stats.
    Also updates seller profile phone if seller exists.
    """
    current_user.phone = data.phone

    # Also update seller phone if registered
    query = select(Seller).where(Seller.user_id == current_user.id)
    result = await db.execute(query)
    seller = result.scalar_one_or_none()
    if seller:
        seller.phone = data.phone

    await db.commit()

    phone_suffix = normalize_phone(data.phone)
    stats = await get_crawled_stats(db, phone_suffix)
    return SellerCrawledStatsResponse(**stats)


@router.get("/me/crawled/stats", response_model=SellerCrawledStatsResponse)
async def get_seller_crawled_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get counts of crawled listings matching the current seller's phone/channel."""
    ctx = await _get_seller_match_context(current_user, db)

    olx_count = 0
    tg_count = 0

    if ctx.phone_suffix:
        stats = await get_crawled_stats(db, ctx.phone_suffix)
        olx_count += stats["olx_count"]
        tg_count += stats["telegram_count"]

    if ctx.channel_name:
        channel_stats = await get_crawled_stats_by_channel(db, ctx.channel_name)
        tg_count += channel_stats["telegram_count"]

    return SellerCrawledStatsResponse(
        olx_count=olx_count,
        telegram_count=tg_count,
        total_count=olx_count + tg_count,
    )


@router.get("/me/crawled/olx", response_model=PaginatedResponse[OLXListingResponse])
async def get_seller_crawled_olx(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    listing_type: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated OLX crawled listings matching the current seller's phone."""
    ctx = await _get_seller_match_context(current_user, db)

    if not ctx.phone_suffix:
        return PaginatedResponse.create(items=[], total=0, page=page, per_page=per_page)

    items, total = await get_olx_listings(
        db, ctx.phone_suffix, page, per_page, listing_type
    )

    return PaginatedResponse.create(
        items=[OLXListingResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/me/crawled/telegram", response_model=PaginatedResponse[TelegramListingResponse]
)
async def get_seller_crawled_telegram(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    listing_type: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated Telegram crawled listings matching the current seller's phone/channel."""
    ctx = await _get_seller_match_context(current_user, db)

    all_items = []
    total = 0

    if ctx.phone_suffix:
        items_phone, total_phone = await get_telegram_listings(
            db, ctx.phone_suffix, page, per_page, listing_type
        )
        all_items.extend(items_phone)
        total += total_phone

    if ctx.channel_name:
        items_channel, total_channel = await get_telegram_listings_by_channel(
            db, ctx.channel_name, page, per_page, listing_type
        )
        all_items.extend(items_channel)
        total += total_channel

    # Deduplicate by ID
    seen_ids = set()
    unique_items = []
    for item in all_items:
        if item.id not in seen_ids:
            seen_ids.add(item.id)
            unique_items.append(item)

    return PaginatedResponse.create(
        items=[
            TelegramListingResponse.model_validate(item)
            for item in unique_items[:per_page]
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{seller_id}", response_model=SellerPublicResponse)
async def get_seller_public_profile(
    seller_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get public seller profile.

    Phone is only included if phone_public is True.
    """
    query = select(Seller).where(Seller.id == seller_id)
    result = await db.execute(query)
    seller = result.scalar_one_or_none()

    if not seller:
        raise NotFoundException("Seller", str(seller_id))

    return SellerPublicResponse(
        id=seller.id,
        company_name=seller.company_name,
        description=seller.description,
        logo_url=seller.logo_url,
        phone=seller.phone if seller.phone_public else None,
        telegram_username=seller.telegram_username,
        instagram_url=seller.instagram_url,
        website_url=seller.website_url,
        is_verified=seller.is_verified,
        listings_count=seller.listings_count,
        created_at=seller.created_at,
    )


@router.get(
    "/{seller_id}/listings", response_model=PaginatedResponse[ListingListResponse]
)
async def get_seller_public_listings(
    seller_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get public listings of a seller.
    """
    # Verify seller exists
    seller_query = select(Seller).where(Seller.id == seller_id)
    seller_result = await db.execute(seller_query)
    if not seller_result.scalar_one_or_none():
        raise NotFoundException("Seller", str(seller_id))

    # Get listings
    query = select(Listing).where(
        Listing.seller_id == seller_id,
        Listing.status == ListingStatus.ACTIVE,
        Listing.moderation_status == ModerationStatus.APPROVED,
        Listing.deleted_at.is_(None),
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = (
        query.order_by(Listing.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .options(selectinload(Listing.images))
    )

    result = await db.execute(query)
    listings = result.scalars().all()

    items = []
    for listing in listings:
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
                primary_image_url=primary_image.medium_url if primary_image else None,
            )
        )

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )
