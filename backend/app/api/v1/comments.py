"""Comments API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_user, get_current_user_optional
from app.api.v1.helpers import find_listing_any_source
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.db.database import get_db
from app.db.models import (
    Comment,
    CommentLike,
    Listing,
    Notification,
    NotificationType,
    User,
)
from app.schemas.comment import CommentAuthorResponse, CommentCreate, CommentResponse
from app.schemas.common import MessageResponse, PaginatedResponse

router = APIRouter()


def build_comment_response(
    comment: Comment,
    is_liked: bool = False,
) -> CommentResponse:
    """Build comment response from model."""
    return CommentResponse(
        id=comment.id,
        listing_id=comment.listing_id,
        user_id=comment.user_id,
        text=comment.text,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author=CommentAuthorResponse(
            id=comment.user.id,
            first_name=comment.user.first_name,
            last_name=comment.user.last_name,
            username=comment.user.username,
            avatar_url=comment.user.avatar_url,
        ),
        replies_count=comment.replies_count,
        likes_count=comment.likes_count,
        is_liked=is_liked,
    )


@router.get(
    "/listings/{listing_id}/comments",
    response_model=PaginatedResponse[CommentResponse],
)
async def get_comments(
    listing_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comments for a listing.

    Returns paginated list of comments with author information.
    """
    # Check if listing exists in any source
    listing = await find_listing_any_source(db, listing_id)
    if not listing:
        raise NotFoundException("Listing", str(listing_id))

    # Count total comments (top-level only)
    count_query = select(func.count()).where(
        Comment.listing_id == listing_id,
        Comment.parent_id.is_(None),
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get comments
    offset = (page - 1) * per_page
    query = (
        select(Comment)
        .where(
            Comment.listing_id == listing_id,
            Comment.parent_id.is_(None),
        )
        .order_by(Comment.created_at.desc())
        .offset(offset)
        .limit(per_page)
        .options(selectinload(Comment.user))
    )
    result = await db.execute(query)
    comments = result.scalars().all()

    # Get user's likes if authenticated
    liked_comment_ids = set()
    if current_user:
        likes_query = select(CommentLike.comment_id).where(
            CommentLike.user_id == current_user.id,
            CommentLike.comment_id.in_([c.id for c in comments]),
        )
        likes_result = await db.execute(likes_query)
        liked_comment_ids = set(likes_result.scalars().all())

    # Build response
    items = [
        build_comment_response(
            comment,
            is_liked=comment.id in liked_comment_ids,
        )
        for comment in comments
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/listings/{listing_id}/comments/{comment_id}/replies",
    response_model=PaginatedResponse[CommentResponse],
)
async def get_comment_replies(
    listing_id: UUID,
    comment_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Get replies for a specific comment.

    Returns paginated list of replies with author information.
    """
    # Check if parent comment exists
    parent_query = select(Comment).where(
        Comment.id == comment_id,
        Comment.listing_id == listing_id,
    )
    parent_result = await db.execute(parent_query)
    parent = parent_result.scalar_one_or_none()

    if not parent:
        raise NotFoundException("Comment", str(comment_id))

    # Count total replies
    count_query = select(func.count()).where(
        Comment.parent_id == comment_id,
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get replies
    offset = (page - 1) * per_page
    query = (
        select(Comment)
        .where(Comment.parent_id == comment_id)
        .order_by(Comment.created_at.asc())  # Oldest first for replies
        .offset(offset)
        .limit(per_page)
        .options(selectinload(Comment.user))
    )
    result = await db.execute(query)
    replies = result.scalars().all()

    # Get user's likes if authenticated
    liked_comment_ids = set()
    if current_user and replies:
        likes_query = select(CommentLike.comment_id).where(
            CommentLike.user_id == current_user.id,
            CommentLike.comment_id.in_([r.id for r in replies]),
        )
        likes_result = await db.execute(likes_query)
        liked_comment_ids = set(likes_result.scalars().all())

    # Build response
    items = [
        build_comment_response(
            reply,
            is_liked=reply.id in liked_comment_ids,
        )
        for reply in replies
    ]

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/listings/{listing_id}/comments",
    response_model=CommentResponse,
    status_code=201,
)
async def create_comment(
    listing_id: UUID,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new comment on a listing.
    """
    # Check if listing exists in any source
    listing = await find_listing_any_source(db, listing_id)
    if not listing:
        raise NotFoundException("Listing", str(listing_id))
    is_main_listing = isinstance(listing, Listing)

    # Check parent comment if provided
    if data.parent_id:
        parent_query = select(Comment).where(
            Comment.id == data.parent_id,
            Comment.listing_id == listing_id,
        )
        parent_result = await db.execute(parent_query)
        parent = parent_result.scalar_one_or_none()

        if not parent:
            raise NotFoundException("Parent comment", str(data.parent_id))

    # Create comment
    comment = Comment(
        listing_id=listing_id,
        user_id=current_user.id,
        parent_id=data.parent_id,
        text=data.text,
    )
    db.add(comment)

    # Update counts (only main listings track comments_count)
    if is_main_listing:
        listing.comments_count += 1
    if data.parent_id:
        parent.replies_count += 1

        # Create notification for the parent comment author (only if not replying to self)
        if parent.user_id != current_user.id:
            # Load parent author to determine their language
            parent_author_query = select(User).where(User.id == parent.user_id)
            parent_author_result = await db.execute(parent_author_query)
            parent_author = parent_author_result.scalar_one()

            from app.workers.tasks.notifications import (
                _COMMENT_REPLY_MESSAGE,
                _COMMENT_REPLY_TITLE,
            )

            lang = (
                parent_author.language
                if parent_author.language in ("ru", "uz")
                else "ru"
            )

            notification = Notification(
                user_id=parent.user_id,
                type=NotificationType.COMMENT_REPLY,
                title=_COMMENT_REPLY_TITLE[lang],
                message=_COMMENT_REPLY_MESSAGE[lang].format(
                    name=current_user.first_name
                ),
                listing_id=listing_id,
                comment_id=comment.id,
                actor_id=current_user.id,
            )
            db.add(notification)

    else:
        # Top-level comment: notify listing owner (if main listing with a seller)
        if is_main_listing and listing.seller_id:
            from app.db.models import Seller

            seller_query = select(Seller).where(Seller.id == listing.seller_id)
            seller_result = await db.execute(seller_query)
            seller = seller_result.scalar_one_or_none()

            if seller and seller.user_id != current_user.id:
                seller_user_query = select(User).where(User.id == seller.user_id)
                seller_user_result = await db.execute(seller_user_query)
                seller_user = seller_user_result.scalar_one_or_none()

                from app.workers.tasks.notifications import (
                    _NEW_COMMENT_MESSAGE,
                    _NEW_COMMENT_TITLE,
                )

                lang = (
                    seller_user.language
                    if seller_user and seller_user.language in ("ru", "uz")
                    else "ru"
                )

                notification = Notification(
                    user_id=seller.user_id,
                    type=NotificationType.NEW_COMMENT,
                    title=_NEW_COMMENT_TITLE[lang],
                    message=_NEW_COMMENT_MESSAGE[lang].format(
                        name=current_user.first_name
                    ),
                    listing_id=listing_id,
                    comment_id=comment.id,
                    actor_id=current_user.id,
                )
                db.add(notification)

    await db.commit()
    await db.refresh(comment)

    # Load user for response
    user_query = select(User).where(User.id == current_user.id)
    user_result = await db.execute(user_query)
    comment.user = user_result.scalar_one()

    return build_comment_response(comment, is_liked=False)


@router.delete(
    "/listings/{listing_id}/comments/{comment_id}",
    response_model=MessageResponse,
)
async def delete_comment(
    listing_id: UUID,
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete own comment.
    """
    # Find comment
    query = select(Comment).where(
        Comment.id == comment_id,
        Comment.listing_id == listing_id,
    )
    result = await db.execute(query)
    comment = result.scalar_one_or_none()

    if not comment:
        raise NotFoundException("Comment", str(comment_id))

    # Check ownership
    if comment.user_id != current_user.id:
        raise ForbiddenException("You can only delete your own comments")

    # Update listing comments count
    listing_query = select(Listing).where(Listing.id == listing_id)
    listing_result = await db.execute(listing_query)
    listing = listing_result.scalar_one_or_none()
    if listing:
        listing.comments_count = max(0, listing.comments_count - 1)

    # Update parent replies count if this is a reply
    if comment.parent_id:
        parent_query = select(Comment).where(Comment.id == comment.parent_id)
        parent_result = await db.execute(parent_query)
        parent = parent_result.scalar_one_or_none()
        if parent:
            parent.replies_count = max(0, parent.replies_count - 1)

    await db.delete(comment)
    await db.commit()

    return MessageResponse(message="Comment deleted")


@router.post(
    "/listings/{listing_id}/comments/{comment_id}/like",
    response_model=MessageResponse,
    status_code=201,
)
async def like_comment(
    listing_id: UUID,
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Like a comment.
    """
    # Find comment
    query = select(Comment).where(
        Comment.id == comment_id,
        Comment.listing_id == listing_id,
    )
    result = await db.execute(query)
    comment = result.scalar_one_or_none()

    if not comment:
        raise NotFoundException("Comment", str(comment_id))

    # Check if already liked
    existing_query = select(CommentLike).where(
        CommentLike.comment_id == comment_id,
        CommentLike.user_id == current_user.id,
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise ConflictException("Already liked this comment")

    # Create like
    like = CommentLike(
        comment_id=comment_id,
        user_id=current_user.id,
    )
    db.add(like)

    # Update comment likes count
    comment.likes_count += 1

    await db.commit()

    return MessageResponse(message="Comment liked")


@router.delete(
    "/listings/{listing_id}/comments/{comment_id}/like",
    response_model=MessageResponse,
)
async def unlike_comment(
    listing_id: UUID,
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Unlike a comment.
    """
    # Find like
    query = select(CommentLike).where(
        CommentLike.comment_id == comment_id,
        CommentLike.user_id == current_user.id,
    )
    result = await db.execute(query)
    like = result.scalar_one_or_none()

    if not like:
        raise NotFoundException("Like")

    # Update comment likes count
    comment_query = select(Comment).where(Comment.id == comment_id)
    comment_result = await db.execute(comment_query)
    comment = comment_result.scalar_one_or_none()
    if comment:
        comment.likes_count = max(0, comment.likes_count - 1)

    await db.delete(like)
    await db.commit()

    return MessageResponse(message="Comment unliked")
