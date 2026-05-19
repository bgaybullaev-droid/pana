"""C4 PR2 — Multi-phone management endpoints.

Per decision-pass / OTP_STRATEGY.md §5: add-phone is auth-required and
NEVER creates a User; operations attach to the current authenticated
seller.

Endpoints:
- ``POST /sellers/me/phones/request-otp`` — send OTP via Telegram bot
- ``POST /sellers/me/phones/verify-otp`` — confirm and attach
- ``GET  /sellers/me/phones`` — list attached phones with listing counts
- ``DELETE /sellers/me/phones/{phone_id}`` — remove (with 3-option flow)

Per PHONE_IDENTITY_MODEL §11: backfill ensures every legacy user has
a primary row in ``user_phones`` already, so this endpoint operates
strictly on additional phones.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.core.security import generate_otp
from app.db.database import get_db
from app.db.models import (
    Listing,
    ListingStatus,
    PhoneVerifyAttempt,
    User,
    UserPhone,
)
from app.db.redis import CacheKeys, get_redis
from app.utils.phone import normalize_phone_e164

logger = logging.getLogger(__name__)
router = APIRouter()

# Mirror the login-OTP constants (auth.py:761-762).
OTP_EXPIRY_SECONDS = 600  # 10 min
OTP_MAX_ATTEMPTS = 3
OTP_RATE_LIMIT_REQUESTS = 3
OTP_RATE_LIMIT_WINDOW = 600  # 10 min


# ── helpers ───────────────────────────────────────────────────────────


def _last9(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    return digits[-9:] if len(digits) >= 9 else digits


def _validate_e164(phone: str) -> str:
    canonical = normalize_phone_e164(phone)
    if not canonical:
        raise BadRequestException(
            "Phone must be in international format, e.g. +998XXXXXXXXX"
        )
    return canonical


# ── schemas ───────────────────────────────────────────────────────────


class RequestOtpIn(BaseModel):
    phone: str = Field(..., min_length=4, max_length=20)


class VerifyOtpIn(BaseModel):
    phone: str = Field(..., min_length=4, max_length=20)
    code: str = Field(..., min_length=4, max_length=6)


class PhoneOut(BaseModel):
    id: str
    phone: str
    is_primary: bool
    verification_method: str
    verified_at: datetime
    listings_count: int


class DeletePhoneIn(BaseModel):
    """3-option flow per PHONE_IDENTITY_MODEL §5."""

    action: Literal[
        "transfer_to_primary",
        "transfer_to_other",
        "archive_listings",
    ]
    target_phone_id: Optional[str] = None  # required when action='transfer_to_other'


# ── endpoints ─────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=List[PhoneOut],
    summary="List attached phones with per-phone listing counts",
)
async def list_phones(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(UserPhone)
            .where(UserPhone.user_id == user.id)
            .order_by(UserPhone.is_primary.desc(), UserPhone.created_at.asc())
        )
    ).scalars().all()

    out: List[PhoneOut] = []
    for r in rows:
        # Count listings whose contact phone matches this row's phone.
        count = (
            await db.execute(
                select(func.count(Listing.id)).where(
                    Listing.seller_id == user.id,
                    Listing.phone == r.phone,
                    Listing.deleted_at.is_(None),
                )
            )
        ).scalar_one()
        out.append(
            PhoneOut(
                id=str(r.id),
                phone=r.phone,
                is_primary=r.is_primary,
                verification_method=r.verification_method,
                verified_at=r.verified_at,
                listings_count=int(count or 0),
            )
        )
    return out


@router.post(
    "/request-otp",
    status_code=200,
    summary="Send OTP code to attach an additional phone (Telegram bot)",
)
async def request_phone_otp(
    body: RequestOtpIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per OTP_STRATEGY §5 — auth-required; never creates a User."""
    if not settings.multi_phone_enabled:
        raise ForbiddenException("Multi-phone management is disabled")

    phone = _validate_e164(body.phone)
    suffix = _last9(phone)

    # Pre-check: does the user already own this phone?
    existing = (
        await db.execute(
            select(UserPhone).where(UserPhone.phone == phone)
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.user_id == user.id:
            raise BadRequestException(
                {"code": "phone_already_yours", "message": "This phone is already attached to your account"}
            )
        # Don't disclose owner.
        raise BadRequestException(
            {"code": "phone_in_use", "message": "This phone is already attached to another account"}
        )

    # Quota check: max additional phones
    additional_count = (
        await db.execute(
            select(func.count(UserPhone.id)).where(
                UserPhone.user_id == user.id,
                UserPhone.is_primary.is_(False),
            )
        )
    ).scalar_one()
    if int(additional_count or 0) >= settings.multi_phone_max_additional:
        raise BadRequestException(
            {
                "code": "quota_exceeded",
                "message": f"Maximum additional phones reached ({settings.multi_phone_max_additional})",
            }
        )

    redis = await get_redis()
    rate_key = CacheKeys.add_phone_rate_limit(str(user.id), suffix)
    rate = await redis.get(rate_key)
    if rate and int(rate) >= OTP_RATE_LIMIT_REQUESTS:
        raise BadRequestException(
            "Too many OTP requests. Try again in 10 minutes."
        )

    code = generate_otp()
    otp_key = CacheKeys.add_phone_otp(str(user.id), suffix)
    attempts_key = CacheKeys.add_phone_otp_attempts(str(user.id), suffix)
    await redis.setex(otp_key, OTP_EXPIRY_SECONDS, code)
    await redis.delete(attempts_key)
    if rate:
        await redis.incr(rate_key)
    else:
        await redis.setex(rate_key, OTP_RATE_LIMIT_WINDOW, 1)

    # Log the attempt for C5 detection (forward-compat).
    db.add(
        PhoneVerifyAttempt(
            user_id=user.id, phone=phone, succeeded=False
        )
    )
    await db.commit()

    # Deliver via Telegram bot (per OTP_STRATEGY §1 + decision #1).
    if user.telegram_id:
        try:
            from app.bot.notifications import get_bot_instance

            bot = get_bot_instance()
            if bot is not None:
                lang = (user.language or "ru").lower()
                if "cyr" in lang:
                    body_text = f"🔐 Рақамни тасдиқлаш коди: <code>{code}</code>\nАмал қилиш муддати: 10 дақиқа."
                elif lang.startswith("uz"):
                    body_text = f"🔐 Raqamni tasdiqlash kodi: <code>{code}</code>\nAmal qilish muddati: 10 daqiqa."
                else:
                    body_text = f"🔐 Код для подтверждения номера: <code>{code}</code>\nСрок действия: 10 минут."
                await bot.send_message(
                    chat_id=user.telegram_id, text=body_text, parse_mode="HTML"
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to deliver add-phone OTP via bot: %s", exc)

    response = {"expires_in": OTP_EXPIRY_SECONDS}
    if settings.debug:
        response["_dev_otp"] = code
    return response


@router.post(
    "/verify-otp",
    response_model=PhoneOut,
    summary="Verify OTP and attach phone to current user",
)
async def verify_phone_otp(
    body: VerifyOtpIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per OTP_STRATEGY §5 — auth-required; ATTACH never CREATE."""
    if not settings.multi_phone_enabled:
        raise ForbiddenException("Multi-phone management is disabled")

    phone = _validate_e164(body.phone)
    suffix = _last9(phone)
    redis = await get_redis()

    attempts_key = CacheKeys.add_phone_otp_attempts(str(user.id), suffix)
    attempts = await redis.get(attempts_key)
    if attempts and int(attempts) >= OTP_MAX_ATTEMPTS:
        await redis.delete(CacheKeys.add_phone_otp(str(user.id), suffix))
        raise BadRequestException("Maximum attempts exceeded. Request a new code.")

    stored = await redis.get(CacheKeys.add_phone_otp(str(user.id), suffix))
    if not stored:
        raise BadRequestException("Code expired. Request a new one.")

    if attempts:
        await redis.incr(attempts_key)
    else:
        await redis.setex(attempts_key, OTP_EXPIRY_SECONDS, 1)

    if stored != body.code:
        remaining = OTP_MAX_ATTEMPTS - (int(attempts or 0) + 1)
        raise BadRequestException(
            f"Invalid code. Attempts remaining: {max(0, remaining)}"
        )

    # Verified — clean up.
    await redis.delete(CacheKeys.add_phone_otp(str(user.id), suffix))
    await redis.delete(attempts_key)

    # Attach phone. Idempotent: if a row already exists for this user
    # (race condition), surface a clear error.
    new_phone = UserPhone(
        user_id=user.id,
        phone=phone,
        is_primary=False,
        verification_method="tg_otp",
        verified_at=datetime.utcnow(),
    )
    db.add(new_phone)
    db.add(
        PhoneVerifyAttempt(
            user_id=user.id, phone=phone, succeeded=True
        )
    )
    try:
        await db.commit()
        await db.refresh(new_phone)
    except IntegrityError:
        await db.rollback()
        raise BadRequestException(
            {
                "code": "phone_in_use",
                "message": "This phone became attached to another account; please retry.",
            }
        )

    # Per spec: synchronous re-search after verify, return matched count.
    matched = (
        await db.execute(
            select(func.count(Listing.id)).where(
                Listing.seller_id != user.id,
                Listing.phone == phone,
                Listing.deleted_at.is_(None),
            )
        )
    ).scalar_one()

    return PhoneOut(
        id=str(new_phone.id),
        phone=new_phone.phone,
        is_primary=new_phone.is_primary,
        verification_method=new_phone.verification_method,
        verified_at=new_phone.verified_at,
        listings_count=int(matched or 0),
    )


@router.delete(
    "/{phone_id}",
    status_code=200,
    summary="Remove an additional phone (3-option flow)",
)
async def delete_phone(
    phone_id: UUID,
    body: DeletePhoneIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per PHONE_IDENTITY_MODEL §5 — primary cannot be deleted via UI;
    listings on the to-be-deleted phone must transfer or archive first.
    """
    target = (
        await db.execute(
            select(UserPhone).where(
                UserPhone.id == phone_id, UserPhone.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if target is None:
        raise NotFoundException("UserPhone", str(phone_id))
    if target.is_primary:
        raise BadRequestException(
            {
                "code": "primary_phone_protected",
                "message": "Primary phone cannot be deleted via UI; contact support.",
            }
        )

    # Find affected listings.
    affected = (
        await db.execute(
            select(Listing).where(
                Listing.seller_id == user.id,
                Listing.phone == target.phone,
                Listing.deleted_at.is_(None),
            )
        )
    ).scalars().all()

    if body.action == "transfer_to_primary":
        if not user.phone:
            raise BadRequestException("User has no primary phone to transfer to")
        new_phone_value = user.phone
    elif body.action == "transfer_to_other":
        if not body.target_phone_id:
            raise BadRequestException("target_phone_id is required for transfer_to_other")
        target_other = (
            await db.execute(
                select(UserPhone).where(
                    UserPhone.id == UUID(body.target_phone_id),
                    UserPhone.user_id == user.id,
                )
            )
        ).scalar_one_or_none()
        if target_other is None or target_other.id == target.id:
            raise BadRequestException("target_phone_id is not a valid alternate phone")
        new_phone_value = target_other.phone
    else:  # archive_listings
        new_phone_value = None  # signal archive path

    if new_phone_value is not None:
        for listing in affected:
            listing.phone = new_phone_value
    else:
        for listing in affected:
            listing.status = ListingStatus.DELETED
            listing.deleted_at = datetime.utcnow()

    await db.delete(target)
    await db.commit()

    return {
        "status": "ok",
        "affected_listings_count": len(affected),
        "action": body.action,
    }
