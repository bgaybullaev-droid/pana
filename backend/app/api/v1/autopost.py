"""Block D V2.0 (D4) — Cabinet endpoints for channel autoposting.

Endpoints:
- ``POST /seller/autopost/connect`` — bind a channel; verify bot is admin.
- ``POST /seller/autopost/disconnect`` — clear the binding (posts kept per D4-Q8).
- ``GET  /seller/autopost/posts`` — paginated history for the cabinet.
- ``POST /seller/autopost/posts/{post_id}/update`` — manual refresh.

User-facing path stays snappy: each endpoint returns immediately and
hands the actual Telegram work to Celery via the tasks in
``workers/tasks/autopost.py``. The cabinet polls or accepts eventual
consistency on the history list.

Subscription gate: ``check_active_subscription`` lives in
``services/subscriptions.py``; flipping from "open to all" to "real
check" is one config flag.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_user
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.db.database import get_db
from app.db.models import (
    BotChannelPost,
    Listing,
    Seller,
    SubscriptionType,
    User,
)
from app.services import autopost as domain
from app.services.channel_publisher import verify_channel_admin
from app.services.subscriptions import check_active_subscription

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ConnectChannelRequest(BaseModel):
    """``POST /seller/autopost/connect`` body."""

    channel: str = Field(..., min_length=2, max_length=128)


class ConnectChannelResponse(BaseModel):
    status: str  # "verified" | error code
    channel_id: Optional[int] = None
    channel_username: Optional[str] = None
    verified_at: Optional[str] = None  # ISO timestamp
    error: Optional[str] = None


class DisconnectResponse(BaseModel):
    status: str  # "disconnected"


class AutopostStatusResponse(BaseModel):
    """Combined "where do I stand" payload used by the cabinet UI."""

    connected: bool
    enabled: bool
    channel_username: Optional[str] = None
    channel_id: Optional[int] = None
    verified_at: Optional[str] = None
    stale_count: int = 0


class PostListItem(BaseModel):
    id: str
    listing_id: str
    listing_title: Optional[str] = None
    posted_at: str
    last_edited_at: Optional[str] = None
    is_stale: bool
    status: str


class PostListResponse(BaseModel):
    items: List[PostListItem]
    page: int
    page_size: int
    total: int


class UpdatePostRequest(BaseModel):
    force_text_only: bool = False


class UpdatePostResponse(BaseModel):
    result: str  # "queued" | "media_too_old" | error
    post_age_hours: Optional[int] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_my_seller(db: AsyncSession, user: User) -> Seller:
    row = await db.execute(select(Seller).where(Seller.user_id == user.id))
    seller = row.scalar_one_or_none()
    if seller is None:
        raise ForbiddenException("Seller profile required")
    return seller


def _post_to_item(post: BotChannelPost, listing: Optional[Listing]) -> PostListItem:
    return PostListItem(
        id=str(post.id),
        listing_id=str(post.listing_id),
        listing_title=listing.title if listing else None,
        posted_at=post.posted_at.isoformat(),
        last_edited_at=post.last_edited_at.isoformat()
        if post.last_edited_at
        else None,
        is_stale=(
            listing is not None and domain.is_post_stale(post, listing)
            and post.status == "live"
        ),
        status=post.status,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/status", response_model=AutopostStatusResponse)
async def get_autopost_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AutopostStatusResponse:
    """Read the current connection state + stale-post counter.

    Subscription gate enforced silently: if access is denied we still
    return a payload (``connected=False``) so the cabinet can render
    the upgrade prompt. The caller decides UI.
    """
    seller = await _get_my_seller(db, user)
    allowed = await check_active_subscription(
        db, user.id, SubscriptionType.CABINET
    )
    if not allowed:
        return AutopostStatusResponse(connected=False, enabled=False)

    stale_q = await db.execute(
        select(func.count())
        .select_from(BotChannelPost)
        .join(Listing, Listing.id == BotChannelPost.listing_id)
        .where(
            BotChannelPost.seller_id == seller.id,
            BotChannelPost.status == "live",
            Listing.version > BotChannelPost.last_listing_version,
        )
    )
    stale_count = int(stale_q.scalar_one() or 0)

    return AutopostStatusResponse(
        connected=domain.is_autopost_ready(seller),
        enabled=seller.autopost_enabled,
        channel_username=seller.autopost_channel_username,
        channel_id=seller.autopost_channel_id,
        verified_at=seller.autopost_verified_at.isoformat()
        if seller.autopost_verified_at
        else None,
        stale_count=stale_count,
    )


@router.post("/connect", response_model=ConnectChannelResponse)
async def connect_channel(
    data: ConnectChannelRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConnectChannelResponse:
    """Bind a channel after verifying the bot is an admin there."""
    seller = await _get_my_seller(db, user)
    allowed = await check_active_subscription(
        db, user.id, SubscriptionType.CABINET
    )
    if not allowed:
        raise ForbiddenException("Cabinet subscription required")

    result = await verify_channel_admin(data.channel)
    if not result.ok:
        return ConnectChannelResponse(
            status="error",
            channel_id=result.channel_id,
            error=result.error_code or "verify_failed",
        )

    # Persist on success. Store the canonical handle Telegram resolved
    # (None for id-only private channels) instead of the raw user input,
    # which may have been a pasted ``t.me/…`` link.
    from datetime import datetime

    seller.autopost_channel_username = result.channel_username
    seller.autopost_channel_id = result.channel_id
    seller.autopost_enabled = True
    seller.autopost_verified_at = datetime.utcnow()
    await db.commit()
    logger.info(
        "autopost.connected seller=%s channel_id=%s username=%s",
        seller.id,
        seller.autopost_channel_id,
        seller.autopost_channel_username,
    )
    return ConnectChannelResponse(
        status="verified",
        channel_id=seller.autopost_channel_id,
        channel_username=seller.autopost_channel_username,
        verified_at=seller.autopost_verified_at.isoformat(),
    )


@router.post("/disconnect", response_model=DisconnectResponse)
async def disconnect_channel(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DisconnectResponse:
    """Clear the channel binding. Existing posts stay in the channel
    (D4-Q8); only tracking stops."""
    seller = await _get_my_seller(db, user)
    seller.autopost_channel_username = None
    seller.autopost_channel_id = None
    seller.autopost_enabled = False
    seller.autopost_verified_at = None
    await db.commit()
    logger.info("autopost.disconnected seller=%s", seller.id)
    return DisconnectResponse(status="disconnected")


@router.get("/posts", response_model=PostListResponse)
async def list_posts(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PostListResponse:
    """Paginated channel-post history.

    Sorted newest-first. Joined to listings for the title + staleness
    check (one query, no N+1).
    """
    seller = await _get_my_seller(db, user)
    page = max(1, page)
    page_size = max(1, min(int(page_size), 50))
    offset = (page - 1) * page_size

    total_q = await db.execute(
        select(func.count())
        .select_from(BotChannelPost)
        .where(BotChannelPost.seller_id == seller.id)
    )
    total = int(total_q.scalar_one() or 0)

    rows = (
        await db.execute(
            select(BotChannelPost, Listing)
            .join(Listing, Listing.id == BotChannelPost.listing_id, isouter=True)
            .where(BotChannelPost.seller_id == seller.id)
            .order_by(BotChannelPost.posted_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).all()

    items = [_post_to_item(p, l) for p, l in rows]
    return PostListResponse(
        items=items, page=page, page_size=page_size, total=total
    )


@router.post("/posts/{post_id}/update", response_model=UpdatePostResponse)
async def trigger_update(
    post_id: UUID,
    data: UpdatePostRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UpdatePostResponse:
    """Queue a refresh for one post. Returns synchronously; the actual
    Telegram edit runs in Celery.

    When the post is past the 48h media-edit cutoff and the photo would
    need to change, returns ``media_too_old`` so the cabinet can show
    the 3-option modal.
    """
    seller = await _get_my_seller(db, user)
    row = await db.execute(
        select(BotChannelPost).where(
            BotChannelPost.id == post_id,
            BotChannelPost.seller_id == seller.id,
        )
    )
    post = row.scalar_one_or_none()
    if post is None:
        raise NotFoundException("Channel post")

    # If photo is about to change AND we're past 48h, the user must
    # explicitly choose (force_text_only or repost). Return early so
    # the cabinet renders the modal — don't enqueue yet.
    from app.services.autopost import media_edit_allowed

    if not data.force_text_only and not media_edit_allowed(post):
        listing_row = await db.execute(
            select(Listing).where(Listing.id == post.listing_id)
        )
        listing = listing_row.scalar_one_or_none()
        if listing is not None and listing.version > post.last_listing_version:
            from datetime import datetime

            age_hours = int(
                (datetime.utcnow() - post.posted_at).total_seconds() // 3600
            )
            return UpdatePostResponse(
                result="media_too_old", post_age_hours=age_hours
            )

    from app.workers.tasks.autopost import update_channel_post

    update_channel_post.delay(str(post.id), data.force_text_only)
    return UpdatePostResponse(result="queued")


class RecreatePostResponse(BaseModel):
    result: str  # "queued" | error


@router.post("/posts/{post_id}/recreate", response_model=RecreatePostResponse)
async def trigger_recreate(
    post_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecreatePostResponse:
    """Block D D4 — "delete old post + publish a new one" for the
    48h-cutoff modal choice. Loses accumulated views/reactions on the
    old post; seller is informed in the modal copy.

    Same shape as ``/update`` — returns immediately, Celery handles
    the actual Telegram dance.
    """
    seller = await _get_my_seller(db, user)
    row = await db.execute(
        select(BotChannelPost).where(
            BotChannelPost.id == post_id,
            BotChannelPost.seller_id == seller.id,
        )
    )
    post = row.scalar_one_or_none()
    if post is None:
        raise NotFoundException("Channel post")

    from app.workers.tasks.autopost import recreate_channel_post

    recreate_channel_post.delay(str(post.id))
    return RecreatePostResponse(result="queued")
