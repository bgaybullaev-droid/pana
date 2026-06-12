"""Admin API endpoints."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_admin
from app.bot.notifications import (
    get_bot_instance,
    send_approval_notification,
    send_rejection_notification,
)
from app.core.exceptions import BadRequestException, NotFoundException
from app.db.database import get_db
from app.db.models import (
    AuditLog,
    Listing,
    ModerationStatus,
    Notification,
    NotificationType,
    User,
    UserApprovalStatus,
    UserRole,
)
from app.schemas.admin import (
    AdminDashboardStats,
    AdminListingListResponse,
    AdminListingResponse,
    AdminUserListResponse,
    AdminUserResponse,
    ListingModerationRequest,
    UserApprovalRequest,
)
from app.schemas.common import PaginatedResponse, UTCDateTime
from app.schemas.listing import ListingImageResponse, ListingUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_admin_user_response(user: User) -> AdminUserResponse:
    """Build AdminUserResponse from a User model."""
    return AdminUserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        avatar_url=user.avatar_url,
        language=user.language,
        role=user.role.value,
        approval_status=user.approval_status.value,
        approval_notes=user.approval_notes,
        approved_by=user.approved_by,
        approved_at=user.approved_at,
        onboarding_completed=user.onboarding_completed,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _build_admin_listing_response(listing: Listing) -> AdminListingResponse:
    """Build AdminListingResponse from a Listing model with loaded relations."""
    images = [
        ListingImageResponse(
            id=img.id,
            original_url=img.original_url,
            thumbnail_url=img.thumbnail_url,
            medium_url=img.medium_url,
            large_url=img.large_url,
            position=img.position,
            is_primary=img.is_primary,
        )
        for img in listing.images
    ]

    return AdminListingResponse(
        id=listing.id,
        seller_id=listing.seller_id,
        seller_name=listing.seller.company_name if listing.seller else None,
        seller_phone=listing.seller.phone if listing.seller else None,
        type=listing.type.value,
        property_type=listing.property_type.value,
        rooms=listing.rooms,
        area=listing.area,
        floor=listing.floor,
        total_floors=listing.total_floors,
        region=listing.region,
        district=listing.district,
        address=listing.address,
        latitude=listing.latitude,
        longitude=listing.longitude,
        price=listing.price,
        currency=listing.currency.value,
        title=listing.title,
        description=listing.description,
        phone=listing.phone,
        source_type=listing.source_type.value,
        source_url=listing.source_url,
        raw_text=listing.raw_text,
        status=listing.status.value,
        moderation_status=listing.moderation_status.value,
        moderation_notes=listing.moderation_notes,
        moderated_by=listing.moderated_by,
        moderated_at=listing.moderated_at,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
        images=images,
    )


# ============== DASHBOARD ==============


@router.get("/dashboard", response_model=AdminDashboardStats)
async def get_dashboard_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get admin dashboard statistics."""
    # Count users by approval status
    pending_users_query = select(func.count()).where(
        User.approval_status == UserApprovalStatus.PENDING,
        User.deleted_at.is_(None),
    )
    pending_users = (await db.execute(pending_users_query)).scalar() or 0

    approved_users_query = select(func.count()).where(
        User.approval_status == UserApprovalStatus.APPROVED,
        User.deleted_at.is_(None),
    )
    approved_users = (await db.execute(approved_users_query)).scalar() or 0

    rejected_users_query = select(func.count()).where(
        User.approval_status == UserApprovalStatus.REJECTED,
        User.deleted_at.is_(None),
    )
    rejected_users = (await db.execute(rejected_users_query)).scalar() or 0

    total_users_query = select(func.count()).where(User.deleted_at.is_(None))
    total_users = (await db.execute(total_users_query)).scalar() or 0

    # Count listings by moderation status
    pending_listings_query = select(func.count()).where(
        Listing.moderation_status == ModerationStatus.PENDING,
        Listing.deleted_at.is_(None),
    )
    pending_listings = (await db.execute(pending_listings_query)).scalar() or 0

    approved_listings_query = select(func.count()).where(
        Listing.moderation_status == ModerationStatus.APPROVED,
        Listing.deleted_at.is_(None),
    )
    approved_listings = (await db.execute(approved_listings_query)).scalar() or 0

    rejected_listings_query = select(func.count()).where(
        Listing.moderation_status == ModerationStatus.REJECTED,
        Listing.deleted_at.is_(None),
    )
    rejected_listings = (await db.execute(rejected_listings_query)).scalar() or 0

    total_listings_query = select(func.count()).where(Listing.deleted_at.is_(None))
    total_listings = (await db.execute(total_listings_query)).scalar() or 0

    return AdminDashboardStats(
        pending_users=pending_users,
        total_users=total_users,
        pending_listings=pending_listings,
        total_listings=total_listings,
        approved_users=approved_users,
        rejected_users=rejected_users,
        approved_listings=approved_listings,
        rejected_listings=rejected_listings,
    )


# ============== USER MANAGEMENT ==============


@router.get("/users", response_model=PaginatedResponse[AdminUserListResponse])
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    approval_status: Optional[str] = Query(
        None, pattern="^(pending|approved|rejected)$"
    ),
    role: Optional[str] = Query(None, pattern="^(user|seller|admin)$"),
    q: Optional[str] = Query(None, max_length=100),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with filters (admin only)."""
    query = select(User).where(User.deleted_at.is_(None))

    if approval_status:
        status_enum = UserApprovalStatus(approval_status.lower())
        query = query.where(User.approval_status == status_enum)
    if role:
        role_enum = UserRole(role.lower())
        query = query.where(User.role == role_enum)
    if q:
        search_term = f"%{q}%"
        query = query.where(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.username.ilike(search_term),
                User.phone.ilike(search_term),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(User.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    users = result.scalars().all()

    items = [
        AdminUserListResponse(
            id=u.id,
            telegram_id=u.telegram_id,
            phone=u.phone,
            first_name=u.first_name,
            last_name=u.last_name,
            username=u.username,
            role=u.role.value,
            approval_status=u.approval_status.value,
            created_at=u.created_at,
        )
        for u in users
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get user details (admin only)."""
    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundException("User", str(user_id))

    return _build_admin_user_response(user)


@router.post("/users/{user_id}/approve", response_model=AdminUserResponse)
async def approve_user(
    user_id: UUID,
    data: UserApprovalRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve a pending user (admin only)."""
    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundException("User", str(user_id))

    if user.approval_status != UserApprovalStatus.PENDING:
        raise BadRequestException(f"User is already {user.approval_status.value}")

    old_status = user.approval_status.value

    user.approval_status = UserApprovalStatus.APPROVED
    user.approval_notes = data.notes
    user.approved_by = admin.id
    user.approved_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        user_id=admin.id,
        entity_type="user",
        entity_id=user.id,
        action="approve",
        old_values={"approval_status": old_status},
        new_values={"approval_status": "approved", "notes": data.notes},
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(user)

    # Send Telegram notification to seller
    if user.telegram_id:
        bot = get_bot_instance()
        if bot:
            try:
                await send_approval_notification(bot, user.telegram_id, user.language)
            except Exception as e:
                logger.warning(
                    f"Failed to send approval notification to {user.telegram_id}: {e}"
                )

    return _build_admin_user_response(user)


@router.post("/users/{user_id}/reject", response_model=AdminUserResponse)
async def reject_user(
    user_id: UUID,
    data: UserApprovalRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reject a pending user (admin only)."""
    query = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundException("User", str(user_id))

    if user.approval_status == UserApprovalStatus.REJECTED:
        raise BadRequestException("User is already rejected")

    if not data.notes:
        raise BadRequestException("Rejection reason is required")

    old_status = user.approval_status.value

    user.approval_status = UserApprovalStatus.REJECTED
    user.approval_notes = data.notes
    user.approved_by = admin.id
    user.approved_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        user_id=admin.id,
        entity_type="user",
        entity_id=user.id,
        action="reject",
        old_values={"approval_status": old_status},
        new_values={"approval_status": "rejected", "notes": data.notes},
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(user)

    # Send Telegram notification to seller
    if user.telegram_id:
        bot = get_bot_instance()
        if bot:
            try:
                await send_rejection_notification(
                    bot, user.telegram_id, reason=data.notes, language=user.language
                )
            except Exception as e:
                logger.warning(
                    f"Failed to send rejection notification to {user.telegram_id}: {e}"
                )

    return _build_admin_user_response(user)


# ============== LISTING MODERATION ==============


@router.get("/listings", response_model=PaginatedResponse[AdminListingListResponse])
async def list_listings_for_moderation(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    moderation_status: Optional[str] = Query(
        None, pattern="^(pending|approved|rejected)$"
    ),
    source_type: Optional[str] = Query(None, pattern="^(manual|claimed|parsed)$"),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all listings for moderation (admin only)."""
    query = select(Listing).where(Listing.deleted_at.is_(None))

    if moderation_status:
        status_enum = ModerationStatus(moderation_status.lower())
        query = query.where(Listing.moderation_status == status_enum)
    if source_type:
        from app.db.models import SourceType

        source_enum = SourceType(source_type.lower())
        query = query.where(Listing.source_type == source_enum)

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
        .options(selectinload(Listing.images), selectinload(Listing.seller))
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
            AdminListingListResponse(
                id=listing.id,
                seller_id=listing.seller_id,
                seller_name=listing.seller.company_name if listing.seller else None,
                type=listing.type.value,
                property_type=listing.property_type.value,
                title=listing.title,
                price=listing.price,
                currency=listing.currency.value,
                region=listing.region,
                district=listing.district,
                source_type=listing.source_type.value,
                moderation_status=listing.moderation_status.value,
                moderation_notes=listing.moderation_notes,
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


@router.get("/listings/{listing_id}", response_model=AdminListingResponse)
async def get_listing_for_moderation(
    listing_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get listing details for moderation (admin only)."""
    query = (
        select(Listing)
        .where(Listing.id == listing_id, Listing.deleted_at.is_(None))
        .options(selectinload(Listing.images), selectinload(Listing.seller))
    )
    result = await db.execute(query)
    listing = result.scalar_one_or_none()

    if not listing:
        raise NotFoundException("Listing", str(listing_id))

    return _build_admin_listing_response(listing)


@router.post("/listings/{listing_id}/approve", response_model=AdminListingResponse)
async def approve_listing(
    listing_id: UUID,
    data: ListingModerationRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Approve a listing (admin only)."""
    query = (
        select(Listing)
        .where(Listing.id == listing_id, Listing.deleted_at.is_(None))
        .options(selectinload(Listing.images), selectinload(Listing.seller))
    )
    result = await db.execute(query)
    listing = result.scalar_one_or_none()

    if not listing:
        raise NotFoundException("Listing", str(listing_id))

    old_status = listing.moderation_status.value

    listing.moderation_status = ModerationStatus.APPROVED
    listing.moderation_notes = data.notes
    listing.moderated_by = admin.id
    listing.moderated_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        user_id=admin.id,
        entity_type="listing",
        entity_id=listing.id,
        action="approve",
        old_values={"moderation_status": old_status},
        new_values={"moderation_status": "approved", "notes": data.notes},
    )
    db.add(audit_log)

    # Notify the seller that their listing was approved
    if listing.seller and listing.seller.user_id:
        from app.workers.tasks.notifications import (
            _LISTING_APPROVED_MESSAGE,
            _LISTING_APPROVED_TITLE,
        )

        seller_user_query = select(User).where(User.id == listing.seller.user_id)
        seller_user_result = await db.execute(seller_user_query)
        seller_user = seller_user_result.scalar_one_or_none()
        lang = (
            seller_user.language
            if seller_user and seller_user.language in ("ru", "uz")
            else "ru"
        )

        approval_notification = Notification(
            user_id=listing.seller.user_id,
            type=NotificationType.LISTING_APPROVED,
            title=_LISTING_APPROVED_TITLE[lang],
            message=_LISTING_APPROVED_MESSAGE[lang],
            listing_id=listing.id,
        )
        db.add(approval_notification)

    await db.commit()
    await db.refresh(listing)

    # FIX 1 — approval is the moment the listing becomes visible to
    # buyers; the Meili index must mirror that. Safe-fallback: never
    # blocks the admin response.
    try:
        from app.services.search_index import index_listing as _mx_index

        _mx_index(listing)
    except Exception as exc:
        logger.warning("meili index (admin approve) failed: %s", exc)

    # Trigger matching-user notifications for the newly approved listing
    from app.workers.tasks.notifications import _send_new_listing_notifications

    await _send_new_listing_notifications(str(listing.id))

    return _build_admin_listing_response(listing)


@router.post("/listings/{listing_id}/reject", response_model=AdminListingResponse)
async def reject_listing(
    listing_id: UUID,
    data: ListingModerationRequest,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reject a listing (admin only)."""
    query = (
        select(Listing)
        .where(Listing.id == listing_id, Listing.deleted_at.is_(None))
        .options(selectinload(Listing.images), selectinload(Listing.seller))
    )
    result = await db.execute(query)
    listing = result.scalar_one_or_none()

    if not listing:
        raise NotFoundException("Listing", str(listing_id))

    if not data.notes:
        raise BadRequestException("Rejection reason is required")

    old_status = listing.moderation_status.value

    listing.moderation_status = ModerationStatus.REJECTED
    listing.moderation_notes = data.notes
    listing.moderated_by = admin.id
    listing.moderated_at = datetime.utcnow()

    # Create audit log
    audit_log = AuditLog(
        user_id=admin.id,
        entity_type="listing",
        entity_id=listing.id,
        action="reject",
        old_values={"moderation_status": old_status},
        new_values={"moderation_status": "rejected", "notes": data.notes},
    )
    db.add(audit_log)

    # Notify the seller that their listing was rejected
    if listing.seller and listing.seller.user_id:
        from app.workers.tasks.notifications import (
            _LISTING_REJECTED_MESSAGE,
            _LISTING_REJECTED_TITLE,
        )

        seller_user_query = select(User).where(User.id == listing.seller.user_id)
        seller_user_result = await db.execute(seller_user_query)
        seller_user = seller_user_result.scalar_one_or_none()
        lang = (
            seller_user.language
            if seller_user and seller_user.language in ("ru", "uz")
            else "ru"
        )

        rejection_notification = Notification(
            user_id=listing.seller.user_id,
            type=NotificationType.LISTING_REJECTED,
            title=_LISTING_REJECTED_TITLE[lang],
            message=_LISTING_REJECTED_MESSAGE[lang].format(reason=data.notes or ""),
            listing_id=listing.id,
        )
        db.add(rejection_notification)

    await db.commit()
    await db.refresh(listing)

    # FIX 1 — rejection MUST remove the document from Meili; otherwise a
    # rejected listing keeps appearing on the buyer feed when the flag
    # is flipped to meili. Safe-fallback: failures do not block the
    # admin response.
    try:
        from app.services.search_index import delete_listing as _mx_delete

        _mx_delete(listing.id)
    except Exception as exc:
        logger.warning("meili delete (admin reject) failed: %s", exc)

    return _build_admin_listing_response(listing)


# ─────────────────────────────────────────────────────────────────────
# PR-F.3 — Admin-scoped listing edit
# ─────────────────────────────────────────────────────────────────────
#
# Reuses the matrix/dual-read/validation pipeline from the seller's
# PATCH route, but bypasses the seller-ownership check. Every field
# change is recorded in audit_log with before/after snapshots.


def _diff_values(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """Return only the keys whose values changed (for audit old_values
    projection). Preserves null → value and value → null transitions."""
    out: Dict[str, Any] = {}
    for k, before_v in before.items():
        after_v = after.get(k)
        if before_v != after_v:
            out[k] = before_v
    return out


@router.patch("/listings/{listing_id}", response_model=AdminListingResponse)
async def admin_update_listing(
    listing_id: UUID,
    data: ListingUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin edit — full power over any listing, bypasses seller
    ownership. Applies the same matrix/clearing/validation rules as the
    seller PATCH so the row stays consistent, then records a full audit
    log entry of the diff.
    """
    # Inline imports for the engine helpers + enums so the admin module
    # doesn't pull the whole listings API surface at load time.
    from app.api.v1.listings import (
        _apply_dual_read_inputs,
        _clear_incompatible_fields,
        _populate_listing_lang_columns,
        _validate_required_fields,
    )
    from app.db.models import Currency as _Currency
    from app.db.models import ListingStatus as _ListingStatus
    from app.db.models import ListingType as _ListingType
    from app.db.models import PropertyType as _PropertyType

    query = (
        select(Listing)
        .where(Listing.id == listing_id, Listing.deleted_at.is_(None))
        .options(selectinload(Listing.images), selectinload(Listing.seller))
    )
    listing = (await db.execute(query)).scalar_one_or_none()
    if listing is None:
        raise NotFoundException("Listing", str(listing_id))

    # Capture "before" snapshot for audit — project the same fields the
    # PATCH body could have mutated.
    audited_fields = list(data.model_dump(exclude_unset=True).keys())
    before_snapshot = {
        k: _serialize_audit_value(getattr(listing, k, None)) for k in audited_fields
    }

    update_data = data.model_dump(exclude_unset=True)
    update_data = _apply_dual_read_inputs(update_data)

    _TRANSLATABLE_FIELDS = {"description", "title", "address"}
    content_changed = False

    # `images` is not in the admin PATCH contract for this phase — if the
    # body included it, ignore. Admins edit scalar fields here; full
    # photo management has its own flow.
    update_data.pop("images", None)

    for field, value in update_data.items():
        if field == "type" and value:
            setattr(listing, field, _ListingType(value))
        elif field == "property_type" and value:
            setattr(listing, field, _PropertyType(value))
        elif field == "currency" and value:
            setattr(listing, field, _Currency(value))
        elif field == "status" and value:
            setattr(listing, field, _ListingStatus(value))
        else:
            if field in _TRANSLATABLE_FIELDS and getattr(listing, field) != value:
                content_changed = True
            setattr(listing, field, value)

    _clear_incompatible_fields(listing)
    # is_create=False — admins can PATCH legacy rows without getting
    # 400'd by the S3 `city` / S4 `commercial_type` required rules.
    _validate_required_fields(listing, is_create=False)

    if content_changed:
        _populate_listing_lang_columns(listing)

    # Capture "after" snapshot post-clear/validate.
    after_snapshot = {
        k: _serialize_audit_value(getattr(listing, k, None)) for k in audited_fields
    }

    old_values = _diff_values(before_snapshot, after_snapshot)
    new_values = {k: after_snapshot[k] for k in old_values.keys()}

    if old_values:
        audit_log = AuditLog(
            user_id=admin.id,
            entity_type="listing",
            entity_id=listing.id,
            action="update",
            old_values=old_values,
            new_values=new_values,
        )
        db.add(audit_log)

    await db.commit()
    await db.refresh(listing)

    # Keep Meili in sync — safe-fallback, never blocks the response.
    try:
        from app.services.search_index import index_listing as _mx_index

        _mx_index(listing)
    except Exception as exc:
        logger.warning("meili index (admin update) failed: %s", exc)

    return _build_admin_listing_response(listing)


def _serialize_audit_value(value: Any) -> Any:
    """Coerce a model attribute to something JSON-safe for audit_log.
    Enums → .value, UUIDs/datetimes → str, everything else passthrough."""
    if value is None:
        return None
    if hasattr(value, "value"):  # SQLAlchemy Enum
        return value.value
    if isinstance(value, (UUID, datetime)):
        return str(value)
    # Lists/dicts — passthrough; JSONB handles them natively.
    return value


# ─────────────────────────────────────────────────────────────────────
# FIX 4 — Meili reindex + counters endpoint (admin-only)
# ─────────────────────────────────────────────────────────────────────


@router.post("/meili/reindex-all")
async def admin_reindex_all_meili(
    batch_size: int = 1000,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Force a full Postgres → Meilisearch reindex. Idempotent (upsert
    by primary key). Safe-fallback: on any Meili failure the endpoint
    returns zero counts rather than 5xx-ing.

    This is the ops-layer reconciliation hook — point a cron or Celery
    beat at it every 15 min, or call manually after a Meili outage.
    """
    from app.services.search_index import (
        backfill_all_listings,
        backfill_crawled_listings,
        get_backfill_counters,
        init_meilisearch_index,
    )

    # Best-effort ensure index + attributes exist before we push docs.
    init_meilisearch_index()

    native = await backfill_all_listings(db, batch_size=batch_size)
    crawled = await backfill_crawled_listings(db, batch_size=batch_size)
    return {
        "indexed_count": native["indexed_count"] + crawled["indexed_count"],
        "native_indexed": native["indexed_count"],
        "crawled_indexed": crawled["indexed_count"],
        "failed_count": native["failed_count"] + crawled["failed_count"],
        "counters": get_backfill_counters(),
    }


@router.get("/meili/counters")
async def admin_meili_counters(admin=Depends(get_current_admin)):
    """Read-only snapshot of the in-process Meili counters. Suitable for
    a lightweight Prometheus scraper or an ops dashboard poll."""
    from app.services.search_index import get_backfill_counters

    return get_backfill_counters()


# ─────────────────────────────────────────────────────────────────────
# PR-I — Audit log admin view
# ─────────────────────────────────────────────────────────────────────


class AuditLogEntryResponse(BaseModel):
    """Flat projection of an audit_log row — includes a joined
    `actor_name` so the UI doesn't need a second roundtrip to resolve
    user_id → display name."""

    id: UUID
    user_id: Optional[UUID]
    actor_name: Optional[str]
    entity_type: str
    entity_id: UUID
    action: str
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: UTCDateTime

    model_config = {"from_attributes": True}


def _format_actor_name(
    first_name: Optional[str],
    last_name: Optional[str],
    username: Optional[str],
) -> Optional[str]:
    """Compose a human-readable actor label from the three User columns
    we return in the audit join. Returns None for anonymous rows
    (user_id NULL → all three inputs None)."""
    if first_name or last_name:
        return " ".join(p for p in (first_name, last_name) if p)
    if username:
        return f"@{username}"
    return None


@router.get(
    "/audit-log",
    response_model=PaginatedResponse[AuditLogEntryResponse],
)
async def admin_audit_log(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    entity_type: Optional[str] = Query(None, max_length=50),
    action: Optional[str] = Query(None, max_length=50),
    user_id: Optional[UUID] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Paginated, filterable audit log for admin oversight.

    Filters compose with AND. Default ordering is newest-first; the UI
    relies on this for the reverse-chronological feed. Max 200 rows per
    page to bound DB load.
    """
    # WHERE clauses
    predicates = []
    if entity_type:
        predicates.append(AuditLog.entity_type == entity_type)
    if action:
        predicates.append(AuditLog.action == action)
    if user_id:
        predicates.append(AuditLog.user_id == user_id)
    if from_date:
        predicates.append(AuditLog.created_at >= from_date)
    if to_date:
        predicates.append(AuditLog.created_at <= to_date)

    where_clause = and_(*predicates) if predicates else None

    # Total — same filter, no ordering needed.
    count_q = select(func.count()).select_from(AuditLog)
    if where_clause is not None:
        count_q = count_q.where(where_clause)
    total = (await db.execute(count_q)).scalar() or 0

    # Page — LEFT JOIN to users so we can return the display name without
    # a second round-trip. Anonymous audit rows (user_id NULL) still
    # appear, just with `actor_name=None`.
    offset = (page - 1) * per_page
    page_q = (
        select(
            AuditLog.id,
            AuditLog.user_id,
            AuditLog.entity_type,
            AuditLog.entity_id,
            AuditLog.action,
            AuditLog.old_values,
            AuditLog.new_values,
            AuditLog.ip_address,
            AuditLog.user_agent,
            AuditLog.created_at,
            User.first_name,
            User.last_name,
            User.username,
        )
        .select_from(AuditLog)
        .outerjoin(User, AuditLog.user_id == User.id)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    if where_clause is not None:
        page_q = page_q.where(where_clause)

    rows = (await db.execute(page_q)).all()

    items: List[AuditLogEntryResponse] = []
    for r in rows:
        actor_name = _format_actor_name(r.first_name, r.last_name, r.username)
        items.append(
            AuditLogEntryResponse(
                id=r.id,
                user_id=r.user_id,
                actor_name=actor_name,
                entity_type=r.entity_type,
                entity_id=r.entity_id,
                action=r.action,
                old_values=r.old_values,
                new_values=r.new_values,
                ip_address=r.ip_address,
                user_agent=r.user_agent,
                created_at=r.created_at,
            )
        )

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return PaginatedResponse[AuditLogEntryResponse](
        items=items,
        page=page,
        per_page=per_page,
        total=int(total),
        total_pages=int(total_pages),
    )
