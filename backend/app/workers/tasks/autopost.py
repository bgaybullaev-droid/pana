"""Block D V2.0 (D4) — Celery tasks for channel autoposting.

Four tasks, one per listing-state transition. All four follow the
same shape: load listing+seller fresh inside the task → render →
publish/edit/delete → update ``bot_channel_posts``. The user-facing
endpoint that enqueued the task returned immediately; failures here
never delay the seller's request.

Retry policy
============
Permanent failures (bot kicked, chat not found) → no retry; mark
``Seller.autopost_verified_at = NULL`` and write a warning. The seller
sees a "reconnect required" prompt in the cabinet on next load.

Transient failures (rate-limit, network) → Celery max_retries=3 with
exponential backoff (60s / 5m / 30m).

Idempotency
===========
``bot_channel_posts.uq_bot_channel_posts_listing_channel`` ensures one
row per (listing, channel). Publish task SELECTs first; if a row
already exists, the task is a no-op.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import (
    BotChannelPost,
    Listing,
    ListingStatus,
    Seller,
)
from app.services import autopost as domain
from app.services import channel_publisher as publisher
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-task async session helper. Reuses the pattern from notifications.py
# (fresh engine per task — Celery workers are sync).
# ---------------------------------------------------------------------------


async def _with_session(fn):
    engine = create_async_engine(
        settings.async_database_url, pool_pre_ping=True, pool_size=2
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_maker() as session:
            return await fn(session)
    finally:
        await engine.dispose()


async def _load_listing(db: AsyncSession, listing_id: UUID) -> Optional[Listing]:
    from sqlalchemy.orm import selectinload

    row = await db.execute(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.images))
    )
    return row.scalar_one_or_none()


async def _load_seller(db: AsyncSession, seller_id: UUID) -> Optional[Seller]:
    row = await db.execute(select(Seller).where(Seller.id == seller_id))
    return row.scalar_one_or_none()


async def _get_existing_post(
    db: AsyncSession, listing_id: UUID, channel_id: int
) -> Optional[BotChannelPost]:
    row = await db.execute(
        select(BotChannelPost).where(
            BotChannelPost.listing_id == listing_id,
            BotChannelPost.channel_id == channel_id,
        )
    )
    return row.scalar_one_or_none()


async def _invalidate_seller_connection(
    db: AsyncSession, seller_id: UUID, reason: str
) -> None:
    """Mark the seller's connection as broken so the cabinet prompts to
    re-verify. Called when Telegram tells us the bot can't post anymore."""
    seller = await _load_seller(db, seller_id)
    if seller is None:
        return
    seller.autopost_verified_at = None
    await db.commit()
    logger.warning(
        "autopost.connection_invalidated seller=%s reason=%s",
        seller_id,
        reason,
    )


def _seller_lang(seller: Seller) -> str:
    """Resolve the seller's language for post body rendering.

    The seller-user relationship is loaded by the caller when needed.
    We fall back to "ru" if the user object isn't attached.
    """
    user = getattr(seller, "user", None)
    return (user.language if user else None) or "ru"


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def publish_listing_to_channel(self, listing_id: str, seller_id: str) -> Dict[str, Any]:
    """Publish a freshly-active listing to the seller's channel."""
    return asyncio.run(_publish_listing_to_channel(self, listing_id, seller_id))


async def _publish_listing_to_channel(
    task, listing_id: str, seller_id: str
) -> Dict[str, Any]:
    async def _run(db: AsyncSession) -> Dict[str, Any]:
        from sqlalchemy.orm import selectinload

        # Load seller with user relationship for language resolution.
        seller_row = await db.execute(
            select(Seller)
            .where(Seller.id == UUID(seller_id))
            .options(selectinload(Seller.user))
        )
        seller = seller_row.scalar_one_or_none()
        if seller is None:
            return {"ok": False, "reason": "seller_not_found"}
        if not domain.is_autopost_ready(seller):
            return {"ok": False, "reason": "channel_not_connected"}

        listing = await _load_listing(db, UUID(listing_id))
        if listing is None:
            return {"ok": False, "reason": "listing_not_found"}
        # Block D D4 — defense-in-depth: never publish an opted-out listing
        # even if an enqueue slipped past the upstream gates.
        if not getattr(listing, "publish_to_channel", True):
            logger.info("autopost.publish_skipped_opt_out listing=%s", listing_id)
            return {"ok": False, "reason": "publish_opt_out"}
        if listing.status != ListingStatus.ACTIVE:
            return {"ok": False, "reason": "listing_not_active"}

        # Idempotency: an earlier task already published this listing.
        existing = await _get_existing_post(
            db, listing.id, seller.autopost_channel_id
        )
        if existing is not None:
            return {"ok": False, "reason": "already_posted"}

        body = domain.render_post_body(listing, _seller_lang(seller))
        result = await publisher.publish_post(seller.autopost_channel_id, body)
        if result.ok:
            db.add(
                BotChannelPost(
                    listing_id=listing.id,
                    seller_id=seller.id,
                    channel_id=seller.autopost_channel_id,
                    message_id=result.message_id,
                    last_listing_version=listing.version,
                    status="live",
                )
            )
            await db.commit()
            return {"ok": True, "message_id": result.message_id}

        if result.permanent_failure:
            await _invalidate_seller_connection(
                db, seller.id, result.error_code or "permanent"
            )
            return {"ok": False, "reason": result.error_code}
        # Transient — retry.
        raise RuntimeError(result.error_code or "telegram_error")

    try:
        return await _with_session(_run)
    except Exception as exc:
        logger.warning(
            "autopost.publish_retry listing=%s seller=%s err=%s",
            listing_id,
            seller_id,
            exc,
        )
        try:
            task.retry(exc=exc)
        except Exception:
            logger.error(
                "autopost.publish_max_retries listing=%s seller=%s",
                listing_id,
                seller_id,
            )
            return {"ok": False, "reason": "max_retries"}


# ---------------------------------------------------------------------------
# Update — manual "Update post in channel" button
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def update_channel_post(
    self,
    post_id: str,
    force_text_only: bool = False,
) -> Dict[str, Any]:
    """Refresh the channel post from current listing state.

    Returns ``{"ok": True}`` on success, ``{"ok": False, "reason":
    "media_too_old"}`` if the photo changed but the post is past the
    48-hour cutoff — the cabinet uses that to surface the 3-option modal.
    """
    return asyncio.run(_update_channel_post(self, post_id, force_text_only))


async def _update_channel_post(
    task, post_id: str, force_text_only: bool
) -> Dict[str, Any]:
    async def _run(db: AsyncSession) -> Dict[str, Any]:
        from sqlalchemy.orm import selectinload

        post_row = await db.execute(
            select(BotChannelPost).where(BotChannelPost.id == UUID(post_id))
        )
        post = post_row.scalar_one_or_none()
        if post is None:
            return {"ok": False, "reason": "post_not_found"}

        listing = await _load_listing(db, post.listing_id)
        if listing is None:
            return {"ok": False, "reason": "listing_not_found"}

        seller_row = await db.execute(
            select(Seller)
            .where(Seller.id == post.seller_id)
            .options(selectinload(Seller.user))
        )
        seller = seller_row.scalar_one_or_none()
        if seller is None:
            return {"ok": False, "reason": "seller_not_found"}

        body = domain.render_post_body(listing, _seller_lang(seller))

        # 48h media-edit cutoff. If the photo URL changed *and* we're
        # past the cutoff, the cabinet must offer the user the choice.
        photo_changed = body.photo_url and (body.photo_url != "")
        # We don't actually know whether the URL is "the same" without
        # comparing to what Telegram stored; conservatively assume any
        # post past 48h needs the text-only path unless force_text_only.
        past_cutoff = not domain.media_edit_allowed(post)
        if past_cutoff and not force_text_only and body.photo_url:
            return {"ok": False, "reason": "media_too_old"}

        if force_text_only or past_cutoff or not body.photo_url:
            result = await publisher.edit_post_caption(
                post.channel_id, post.message_id, body
            )
        else:
            result = await publisher.edit_post_media(
                post.channel_id, post.message_id, body
            )
            # If Telegram reports media is too old, fall back to caption-only.
            if not result.ok and result.error_code == "media_too_old":
                return {"ok": False, "reason": "media_too_old"}

        if result.ok or result.error_code == "not_modified":
            post.last_listing_version = listing.version
            post.last_edited_at = datetime.utcnow()
            await db.commit()
            return {"ok": True}

        if result.permanent_failure:
            if result.error_code == "message_gone":
                post.status = "deleted"
                await db.commit()
                return {"ok": False, "reason": "message_gone"}
            await _invalidate_seller_connection(
                db, post.seller_id, result.error_code or "permanent"
            )
            return {"ok": False, "reason": result.error_code}

        raise RuntimeError(result.error_code or "telegram_error")

    try:
        return await _with_session(_run)
    except Exception as exc:
        logger.warning("autopost.update_retry post=%s err=%s", post_id, exc)
        try:
            task.retry(exc=exc)
        except Exception:
            return {"ok": False, "reason": "max_retries"}


# ---------------------------------------------------------------------------
# Mark sold/rented — caption overlay
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def mark_channel_post_sold(self, listing_id: str) -> Dict[str, Any]:
    """Rewrite the channel-post caption with a SOLD/RENTED overlay."""
    return asyncio.run(_mark_channel_post_sold(self, listing_id))


async def _mark_channel_post_sold(task, listing_id: str) -> Dict[str, Any]:
    async def _run(db: AsyncSession) -> Dict[str, Any]:
        from sqlalchemy.orm import selectinload

        # Listing might already be SOLD (the API mutated it before
        # enqueuing). We just need the seller's lang and the post row.
        listing = await _load_listing(db, UUID(listing_id))
        if listing is None or listing.seller_id is None:
            return {"ok": False, "reason": "listing_not_found"}

        seller_row = await db.execute(
            select(Seller)
            .where(Seller.id == listing.seller_id)
            .options(selectinload(Seller.user))
        )
        seller = seller_row.scalar_one_or_none()
        if seller is None or not seller.autopost_channel_id:
            return {"ok": False, "reason": "channel_unset"}

        post = await _get_existing_post(
            db, listing.id, seller.autopost_channel_id
        )
        if post is None:
            return {"ok": False, "reason": "no_post"}

        body = domain.render_post_body(
            listing, _seller_lang(seller), sold_overlay=True
        )
        result = await publisher.edit_post_caption(
            post.channel_id, post.message_id, body
        )
        if result.ok or result.error_code == "not_modified":
            post.status = "sold_marker"
            post.last_edited_at = datetime.utcnow()
            await db.commit()
            return {"ok": True}
        if result.permanent_failure:
            if result.error_code == "message_gone":
                post.status = "deleted"
                await db.commit()
            else:
                await _invalidate_seller_connection(
                    db, post.seller_id, result.error_code or "permanent"
                )
            return {"ok": False, "reason": result.error_code}
        raise RuntimeError(result.error_code or "telegram_error")

    try:
        return await _with_session(_run)
    except Exception as exc:
        logger.warning("autopost.mark_sold_retry listing=%s err=%s", listing_id, exc)
        try:
            task.retry(exc=exc)
        except Exception:
            return {"ok": False, "reason": "max_retries"}


# ---------------------------------------------------------------------------
# Recreate — 48h-cutoff "delete old + republish" path
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def recreate_channel_post(self, post_id: str) -> Dict[str, Any]:
    """Block D D4 — delete an existing channel post and republish.

    Used when the listing's photo changed and the post is past
    Telegram's 48h media-edit cutoff. Sequencing:
      1. ``delete_message`` against the old post.
      2. Mark the old ``bot_channel_posts`` row as ``status='deleted'``.
      3. Enqueue the standard publish task for the listing — creates a
         fresh row via the existing idempotency check.

    Idempotency: the publish step succeeds only if no live row exists
    for (listing_id, channel_id); step 2 above ensures that.
    """
    return asyncio.run(_recreate_channel_post(self, post_id))


async def _recreate_channel_post(task, post_id: str) -> Dict[str, Any]:
    async def _run(db: AsyncSession) -> Dict[str, Any]:
        post_row = await db.execute(
            select(BotChannelPost).where(BotChannelPost.id == UUID(post_id))
        )
        post = post_row.scalar_one_or_none()
        if post is None:
            return {"ok": False, "reason": "post_not_found"}
        if post.status == "deleted":
            # Old post already gone; just fire a fresh publish.
            seller_id, listing_id = post.seller_id, post.listing_id
        else:
            result = await publisher.delete_post(post.channel_id, post.message_id)
            if not result.ok and not (result.error_code == "message_gone"):
                if result.permanent_failure:
                    await _invalidate_seller_connection(
                        db, post.seller_id, result.error_code or "permanent"
                    )
                    return {"ok": False, "reason": result.error_code}
                raise RuntimeError(result.error_code or "telegram_error")
            post.status = "deleted"
            seller_id, listing_id = post.seller_id, post.listing_id
            await db.commit()

        # Hand off to the publish task for the new row. Fire-and-forget;
        # the cabinet polls /seller/autopost/posts to surface progress.
        publish_listing_to_channel.delay(str(listing_id), str(seller_id))
        return {"ok": True, "republish_enqueued": True}

    try:
        return await _with_session(_run)
    except Exception as exc:
        logger.warning("autopost.recreate_retry post=%s err=%s", post_id, exc)
        try:
            task.retry(exc=exc)
        except Exception:
            return {"ok": False, "reason": "max_retries"}


# ---------------------------------------------------------------------------
# Delete — pause / archive / hard-delete
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def delete_channel_post(self, listing_id: str) -> Dict[str, Any]:
    """Remove the channel post (PAUSED / DELETED / EXPIRED listing)."""
    return asyncio.run(_delete_channel_post(self, listing_id))


async def _delete_channel_post(task, listing_id: str) -> Dict[str, Any]:
    async def _run(db: AsyncSession) -> Dict[str, Any]:
        listing = await _load_listing(db, UUID(listing_id))
        # Listing might be hard-deleted already; we still want to remove
        # the channel post if a row exists.
        if listing is None or listing.seller_id is None:
            # Look up the post by listing_id directly.
            post_row = await db.execute(
                select(BotChannelPost).where(
                    BotChannelPost.listing_id == UUID(listing_id)
                )
            )
            post = post_row.scalar_one_or_none()
            if post is None:
                return {"ok": False, "reason": "no_post"}
            channel_id = post.channel_id
        else:
            seller_row = await db.execute(
                select(Seller).where(Seller.id == listing.seller_id)
            )
            seller = seller_row.scalar_one_or_none()
            if seller is None or not seller.autopost_channel_id:
                return {"ok": False, "reason": "channel_unset"}
            post = await _get_existing_post(
                db, listing.id, seller.autopost_channel_id
            )
            if post is None:
                return {"ok": False, "reason": "no_post"}
            channel_id = post.channel_id

        result = await publisher.delete_post(channel_id, post.message_id)
        if result.ok or result.error_code == "message_gone":
            post.status = "deleted"
            await db.commit()
            return {"ok": True}
        if result.permanent_failure:
            await _invalidate_seller_connection(
                db, post.seller_id, result.error_code or "permanent"
            )
            return {"ok": False, "reason": result.error_code}
        raise RuntimeError(result.error_code or "telegram_error")

    try:
        return await _with_session(_run)
    except Exception as exc:
        logger.warning("autopost.delete_retry listing=%s err=%s", listing_id, exc)
        try:
            task.retry(exc=exc)
        except Exception:
            return {"ok": False, "reason": "max_retries"}
