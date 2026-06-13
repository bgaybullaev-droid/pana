"""Block D V2.0 (D4) — thin aiogram adapter for channel publishing.

The only file that imports aiogram for D4. Domain logic (post body,
status transitions) lives in :mod:`app.services.autopost`; this layer
just hands the rendered bytes to Telegram.

Responsibilities:
- ``verify_channel_admin(channel)`` — pre-connect check.
- ``publish_post(channel_id, post)`` — send_photo, return message_id.
- ``edit_post_caption(channel_id, message_id, caption)`` — text-only edit.
- ``edit_post_media(channel_id, message_id, post)`` — photo+caption edit.
- ``delete_post(channel_id, message_id)``.

Rate limiting
=============
Per-channel serial: one outbound call/sec via Redis SETNX. When Redis
is unavailable the lock fails open — Telegram's own per-bot limits
provide a coarse ceiling.

Error semantics
===============
Every method returns a small :class:`PublishResult` rather than raising
on Telegram errors. Callers (Celery tasks) decide whether to retry,
record the failure, or escalate. ``permanent_failure=True`` flags
errors where retrying makes no sense (bot kicked, chat not found).
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
)
from aiogram.types import (
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    URLInputFile,
)

from app.core.config import settings
from app.db.redis import get_redis
from app.services.autopost import RenderedPost

logger = logging.getLogger(__name__)

# Pacing — 1 outbound call/sec/channel keeps us well under Telegram's
# channel-edit limits.
_PER_CHANNEL_LOCK_TTL_SECONDS = 1
_PER_CHANNEL_LOCK_WAIT_SECONDS = 5  # max time to sit and wait
_PER_CHANNEL_LOCK_POLL_SECONDS = 0.1


# =============================================================================
# Result types
# =============================================================================


@dataclass(frozen=True)
class PublishResult:
    """What the adapter hands back. Never raises."""

    ok: bool
    message_id: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    permanent_failure: bool = False  # bot kicked, chat not found, ...


@dataclass(frozen=True)
class VerifyResult:
    """Outcome of a pre-connect ``get_chat`` + ``get_chat_member`` check."""

    ok: bool
    channel_id: Optional[int] = None
    channel_username: Optional[str] = None  # canonical handle Telegram returned
    error_code: Optional[str] = None


# =============================================================================
# Adapter
# =============================================================================


def _build_keyboard(post: RenderedPost) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=post.button_label, url=post.button_url)]
        ]
    )


async def _acquire_channel_lock(channel_id: int) -> None:
    """Block until we can send to ``channel_id`` (per-channel serial).

    Bounded wait — after _PER_CHANNEL_LOCK_WAIT_SECONDS we proceed
    anyway and let Telegram throttle. Redis unavailable: also proceed.
    """
    try:
        client = await get_redis()
    except Exception:
        return
    key = f"autopost:channel:{channel_id}"
    deadline = asyncio.get_event_loop().time() + _PER_CHANNEL_LOCK_WAIT_SECONDS
    while True:
        try:
            acquired = await client.set(
                key, "1", ex=_PER_CHANNEL_LOCK_TTL_SECONDS, nx=True
            )
        except Exception:
            return
        if acquired:
            return
        if asyncio.get_event_loop().time() >= deadline:
            logger.debug(
                "autopost.lock_wait_exceeded channel=%s — proceeding anyway",
                channel_id,
            )
            return
        await asyncio.sleep(_PER_CHANNEL_LOCK_POLL_SECONDS)


def _classify_error(exc: Exception) -> tuple[str, bool]:
    """Map an aiogram exception to ``(error_code, permanent_failure)``.

    permanent_failure=True means "don't retry; surface to seller".
    """
    if isinstance(exc, TelegramForbiddenError):
        return "forbidden", True  # bot kicked, blocked, missing perms
    if isinstance(exc, TelegramNotFound):
        return "not_found", True  # chat gone, message gone
    if isinstance(exc, TelegramRetryAfter):
        return "retry_after", False  # transient — Celery retries
    if isinstance(exc, TelegramBadRequest):
        msg = (getattr(exc, "message", "") or str(exc)).lower()
        # Specific bad-request kinds we can't recover from.
        if "message to edit not found" in msg or "message to delete not found" in msg:
            return "message_gone", True
        if "message is not modified" in msg:
            return "not_modified", False
        if "media is too old" in msg or "caption is too long" in msg:
            return "media_too_old", True
        return "bad_request", False
    return "telegram_error", False


def _make_bot() -> Bot:
    return Bot(token=settings.telegram_bot_token)


# Marker identifying our own locally-stored uploads inside a photo URL.
_UPLOADS_MARKER = "/uploads/"


def _photo_input(photo_url: str):
    """Resolve a listing photo URL to the best aiogram input.

    Stopgap (single-VPS deploy): uploaded photos live on a disk volume shared
    with the worker and are served at ``/uploads/<key>``. Reading the file
    straight off disk avoids depending on the worker reaching the public URL
    over HTTP (no hairpin NAT to our own domain; ``/uploads`` may be
    browser-only). Falls back to downloading the URL for anything not on local
    disk (e.g. external / crawler-sourced images). The proper fix — object
    storage + CDN + sized renditions — is tracked in BACKLOG.md (#3).
    """
    marker_at = photo_url.find(_UPLOADS_MARKER)
    if marker_at != -1:
        key = photo_url[marker_at + len(_UPLOADS_MARKER):].split("?", 1)[0]
        try:
            local_path = Path(settings.upload_dir) / key
            if local_path.is_file():
                return FSInputFile(str(local_path), filename="listing.jpg")
        except OSError:
            pass
    return URLInputFile(photo_url, filename="listing.jpg")


_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")


def _normalize_channel_input(raw: str) -> str:
    """Reduce a pasted channel reference to a bare token.

    Strips a full/short ``t.me`` / ``telegram.me`` link, an optional query
    string or fragment, surrounding slashes, a leading ``@`` and whitespace —
    so a seller can paste ``https://t.me/foo`` and we resolve ``@foo``.
    Numeric ids survive untouched for the caller to cast.
    """
    s = (raw or "").strip()
    low = s.lower()
    for host in (
        "https://t.me/",
        "http://t.me/",
        "https://telegram.me/",
        "http://telegram.me/",
        "t.me/",
        "telegram.me/",
    ):
        if low.startswith(host):
            s = s[len(host) :]
            break
    s = s.split("?", 1)[0].split("#", 1)[0].strip()
    s = s.strip("/").lstrip("@").strip()
    return s


# ── Verify ────────────────────────────────────────────────────────────


async def verify_channel_admin(channel_username_or_id: str) -> VerifyResult:
    """Resolve a channel handle and confirm the bot is an admin there.

    Accepts ``@name``, a bare username, a pasted ``t.me/…`` link, or a
    numeric channel id (as a string). Invite links (``t.me/+…``,
    ``joinchat/…``) and other junk that can't be resolved by username
    return ``bad_request`` without a Telegram round-trip.
    """
    handle = _normalize_channel_input(channel_username_or_id)
    # Telegram's get_chat takes a numeric chat_id or a public @username.
    if handle.lstrip("-").isdigit():
        target: str | int = int(handle)
    elif _USERNAME_RE.match(handle):
        target = f"@{handle}"
    else:
        return VerifyResult(ok=False, error_code="bad_request")

    bot = _make_bot()
    try:
        try:
            chat = await bot.get_chat(target)
        except (TelegramForbiddenError, TelegramNotFound, TelegramBadRequest) as exc:
            code, _ = _classify_error(exc)
            return VerifyResult(ok=False, error_code=code)
        try:
            me = await bot.get_me()
            member = await bot.get_chat_member(chat.id, me.id)
        except (TelegramForbiddenError, TelegramNotFound, TelegramBadRequest) as exc:
            code, _ = _classify_error(exc)
            return VerifyResult(ok=False, channel_id=chat.id, error_code=code)
        status = getattr(member, "status", "") or ""
        if status != "administrator":
            return VerifyResult(
                ok=False, channel_id=chat.id, error_code="bot_not_admin"
            )
        can_post = getattr(member, "can_post_messages", None)
        if can_post is False:
            return VerifyResult(
                ok=False,
                channel_id=chat.id,
                error_code="bot_lacks_post_permission",
            )
        return VerifyResult(
            ok=True,
            channel_id=chat.id,
            channel_username=getattr(chat, "username", None),
        )
    finally:
        await bot.session.close()


# ── Publish / edit / delete ───────────────────────────────────────────


async def publish_post(channel_id: int, post: RenderedPost) -> PublishResult:
    """Send a fresh post; returns the new ``message_id`` on success."""
    await _acquire_channel_lock(channel_id)
    bot = _make_bot()
    try:
        kb = _build_keyboard(post)
        if post.photo_url:
            # Send the photo as an uploaded file (from disk when possible, else
            # downloaded from the URL) instead of handing Telegram a raw URL:
            # Telegram's send-by-URL path rejects photos >5 MB and needs the
            # host reachable from its servers. See ``_photo_input``.
            msg = await bot.send_photo(
                chat_id=channel_id,
                photo=_photo_input(post.photo_url),
                caption=post.caption,
                reply_markup=kb,
            )
        else:
            msg = await bot.send_message(
                chat_id=channel_id,
                text=post.caption,
                reply_markup=kb,
                disable_web_page_preview=True,
            )
        return PublishResult(ok=True, message_id=msg.message_id)
    except Exception as exc:
        code, permanent = _classify_error(exc)
        logger.warning(
            "autopost.publish_failed channel=%s code=%s err=%s",
            channel_id,
            code,
            exc,
        )
        return PublishResult(
            ok=False,
            error_code=code,
            error_message=str(exc),
            permanent_failure=permanent,
        )
    finally:
        await bot.session.close()


async def edit_post_caption(
    channel_id: int, message_id: int, post: RenderedPost
) -> PublishResult:
    """Edit caption only — works at any age."""
    await _acquire_channel_lock(channel_id)
    bot = _make_bot()
    try:
        kb = _build_keyboard(post)
        await bot.edit_message_caption(
            chat_id=channel_id,
            message_id=message_id,
            caption=post.caption,
            reply_markup=kb,
        )
        return PublishResult(ok=True, message_id=message_id)
    except Exception as exc:
        code, permanent = _classify_error(exc)
        # "not modified" is harmless — caller decides whether to log.
        log = logger.debug if code == "not_modified" else logger.warning
        log(
            "autopost.edit_caption_failed channel=%s msg=%s code=%s err=%s",
            channel_id,
            message_id,
            code,
            exc,
        )
        return PublishResult(
            ok=False,
            error_code=code,
            error_message=str(exc),
            permanent_failure=permanent,
        )
    finally:
        await bot.session.close()


async def edit_post_media(
    channel_id: int, message_id: int, post: RenderedPost
) -> PublishResult:
    """Edit photo + caption. Fails (``media_too_old``) past 48h."""
    if not post.photo_url:
        # Caller should branch on this. Defensive return.
        return PublishResult(
            ok=False,
            error_code="no_photo",
            error_message="post has no photo",
            permanent_failure=True,
        )
    await _acquire_channel_lock(channel_id)
    bot = _make_bot()
    try:
        kb = _build_keyboard(post)
        await bot.edit_message_media(
            chat_id=channel_id,
            message_id=message_id,
            # Upload the file (see ``_photo_input``) rather than a raw URL so
            # large / internally-hosted photos don't get rejected by Telegram.
            media=InputMediaPhoto(
                media=_photo_input(post.photo_url),
                caption=post.caption,
            ),
            reply_markup=kb,
        )
        return PublishResult(ok=True, message_id=message_id)
    except Exception as exc:
        code, permanent = _classify_error(exc)
        logger.warning(
            "autopost.edit_media_failed channel=%s msg=%s code=%s err=%s",
            channel_id,
            message_id,
            code,
            exc,
        )
        return PublishResult(
            ok=False,
            error_code=code,
            error_message=str(exc),
            permanent_failure=permanent,
        )
    finally:
        await bot.session.close()


async def delete_post(channel_id: int, message_id: int) -> PublishResult:
    """Delete a previously-published post. Works at any age."""
    await _acquire_channel_lock(channel_id)
    bot = _make_bot()
    try:
        await bot.delete_message(chat_id=channel_id, message_id=message_id)
        return PublishResult(ok=True, message_id=message_id)
    except Exception as exc:
        code, permanent = _classify_error(exc)
        logger.warning(
            "autopost.delete_failed channel=%s msg=%s code=%s err=%s",
            channel_id,
            message_id,
            code,
            exc,
        )
        return PublishResult(
            ok=False,
            error_code=code,
            error_message=str(exc),
            permanent_failure=permanent,
        )
    finally:
        await bot.session.close()
