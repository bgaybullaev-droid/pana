"""Sellers API endpoints."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
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
    BotChannelPost,
    Favorite,
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
    """How to match crawled listings for a seller.

    Block C V2.0 (C4): ``phone_suffix`` is now a List[str] containing every
    verified phone of the user (primary + additional from user_phones).
    Backward compat — service functions accept either str or list.
    """

    def __init__(
        self,
        phone_suffix: list[str] | None = None,
        channel_name: str | None = None,
    ):
        self.phone_suffix = phone_suffix or []
        self.channel_name = channel_name


async def _get_seller_match_context(
    user: User, db: AsyncSession
) -> _SellerMatchContext:
    """Determine how to match crawled listings based on seller type."""
    from app.services.seller_crawled_listings import (
        get_phone_suffixes_for_user,
    )

    query = select(Seller).where(Seller.user_id == user.id)
    result = await db.execute(query)
    seller = result.scalar_one_or_none()

    channel_name = None

    # Check for channel-based matching
    if seller and seller.source_channel:
        channel_name = seller.source_channel

    # Block C V2.0 (C4) — resolve all verified phones for this user.
    # Falls back to single-phone behaviour if user_phones is empty
    # (backfill ensures every legacy user has their primary in there;
    # this fallback covers freshly-created users in transition windows).
    phone_suffixes = await get_phone_suffixes_for_user(db, user.id)
    if not phone_suffixes:
        phone = (seller.phone if seller else None) or user.phone
        if phone:
            suffix = normalize_phone(phone)
            if suffix and len(suffix) == 9:
                phone_suffixes = [suffix]

    if not phone_suffixes and not channel_name:
        raise BadRequestException(
            "No phone or channel linked for crawled listing matching"
        )

    return _SellerMatchContext(phone_suffix=phone_suffixes, channel_name=channel_name)


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
    db: AsyncSession = Depends(get_db),
):
    """
    Get current seller's profile.

    total_views / total_contacts / total_favorites are computed LIVE from the
    seller's listings — the ``Seller.total_*`` cached columns are never
    updated (view/contact counts accrue on ``Listing``, favorites on the
    ``Favorite`` table), so reading them would always report 0. Mirrors the
    aggregation in ``get_seller_dashboard`` so the profile reflects real
    activity.
    """
    totals = await db.execute(
        select(
            func.coalesce(func.sum(Listing.views_count), 0).label("total_views"),
            func.coalesce(func.sum(Listing.contacts_count), 0).label(
                "total_contacts"
            ),
        ).where(
            Listing.seller_id == seller.id,
            Listing.deleted_at.is_(None),
        )
    )
    agg = totals.one()
    total_favorites = (
        await db.execute(
            select(func.count())
            .select_from(Favorite)
            .join(Listing, Favorite.listing_id == Listing.id)
            .where(Listing.seller_id == seller.id, Listing.deleted_at.is_(None))
        )
    ).scalar_one()

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
        total_views=int(agg.total_views or 0),
        total_contacts=int(agg.total_contacts or 0),
        total_favorites=int(total_favorites or 0),
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

    # Block D D4 — overlay autopost staleness per listing. A SEPARATE
    # grouped query, NOT a JOIN: the count subquery above reuses ``query``,
    # so joining there would corrupt its row count. Rides the
    # ``idx_bot_channel_posts_seller_status`` index.
    post_by_listing: dict[UUID, tuple[UUID, int]] = {}
    listing_ids = [listing.id for listing in listings]
    if listing_ids:
        posts_result = await db.execute(
            select(
                BotChannelPost.listing_id,
                BotChannelPost.id,
                BotChannelPost.last_listing_version,
            ).where(
                BotChannelPost.seller_id == seller.id,
                BotChannelPost.status == "live",
                BotChannelPost.listing_id.in_(listing_ids),
            )
        )
        for post_listing_id, post_id, last_version in posts_result.all():
            post_by_listing[post_listing_id] = (post_id, last_version)

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
                autopost_post_id=(
                    post_by_listing[listing.id][0]
                    if listing.id in post_by_listing
                    else None
                ),
                autopost_is_stale=(
                    listing.id in post_by_listing
                    and listing.version > post_by_listing[listing.id][1]
                ),
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


# =============================================================================
# Seller dashboard — see spec-kit/partial/EXECUTION_PLAN.md Step 7
# =============================================================================


@router.get("/me/dashboard")
async def get_seller_dashboard(
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate counters for the seller's portfolio.

    Reads from the cached counters on Listing (denormalised); they are
    populated atomically alongside the event log in
    ``listing_view_event``. Numbers in this response match the sum of
    the per-card chips on ``/me/listings``.
    """
    totals = await db.execute(
        select(
            func.coalesce(func.sum(Listing.views_count), 0).label("total_views"),
            func.coalesce(func.sum(Listing.contacts_count), 0).label(
                "total_contacts"
            ),
            func.coalesce(func.sum(Listing.favorites_count), 0).label(
                "total_favorites"
            ),
            func.count(Listing.id).label("total_listings"),
        ).where(
            Listing.seller_id == seller.id,
            Listing.deleted_at.is_(None),
        )
    )
    agg = totals.one()

    # C2 / seller-dashboard-counters — chips on the seller's listings
    # page need two extra aggregates restricted to *active* listings:
    #   * ``total_active_listings`` powers the "Active: N / ∞" chip.
    #   * ``favorites_total`` is the cached-counter sum across active
    #     listings only (per-card chips already render the per-listing
    #     value; this gives the portfolio total).
    active_totals = await db.execute(
        select(
            func.count(Listing.id).label("total_active_listings"),
            func.coalesce(func.sum(Listing.favorites_count), 0).label(
                "favorites_total"
            ),
        ).where(
            Listing.seller_id == seller.id,
            Listing.status == ListingStatus.ACTIVE,
            Listing.deleted_at.is_(None),
        )
    )
    active_agg = active_totals.one()

    # Cross-check favorites via the canonical Favorite table; falls back
    # to the cached counter if it ever drifts.
    fav_real = (
        await db.execute(
            select(func.count())
            .select_from(Favorite)
            .join(Listing, Favorite.listing_id == Listing.id)
            .where(Listing.seller_id == seller.id, Listing.deleted_at.is_(None))
        )
    ).scalar_one()

    top_rows = (
        await db.execute(
            select(Listing.id, Listing.title, Listing.views_count)
            .where(
                Listing.seller_id == seller.id,
                Listing.deleted_at.is_(None),
            )
            .order_by(Listing.views_count.desc().nullslast())
            .limit(3)
        )
    ).all()

    # A5 V2.0 — last-7-day rolling window from the event log. Counts both
    # auth (user_id) and anon (anon_id) rows that the dedup index admits.
    seven_d = await db.execute(
        text(
            """
            SELECT
              COALESCE(SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END), 0) AS views_7d,
              COALESCE(SUM(CASE WHEN e.event_type = 'contact' THEN 1 ELSE 0 END), 0) AS contacts_7d
            FROM listing_view_event e
            JOIN listings l ON l.id = e.listing_id
            WHERE l.seller_id = :sid
              AND l.deleted_at IS NULL
              AND e.viewed_at >= now() - interval '7 days'
            """
        ),
        {"sid": seller.id},
    )
    seven_row = seven_d.one()

    # Block C V2.0 (C2) — billable count is the live "ACTIVE +
    # GENERATION_FAILED" count per the buyer-feed gate. Distinct from
    # total_listings which counts everything not soft-deleted.
    from app.services.listing_quota import get_billable_listing_count
    total_billable_listings = await get_billable_listing_count(seller.id, db)

    return {
        "total_listings": int(agg.total_listings or 0),
        "total_active_listings": int(active_agg.total_active_listings or 0),
        "total_billable_listings": total_billable_listings,
        "free_listings_per_seller": settings.free_listings_per_seller,
        "test_period_active": settings.test_period_active,
        "total_views": int(agg.total_views or 0),
        "total_contacts": int(agg.total_contacts or 0),
        "total_favorites": int(fav_real or agg.total_favorites or 0),
        "favorites_total": int(active_agg.favorites_total or 0),
        "total_views_7d": int(seven_row.views_7d or 0),
        "total_contacts_7d": int(seven_row.contacts_7d or 0),
        "top_listings": [
            {
                "id": str(row.id),
                "title": row.title,
                "views_count": row.views_count or 0,
            }
            for row in top_rows
        ],
    }
