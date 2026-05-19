"""Authentication API endpoints."""

from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_current_user_optional
from app.bot.i18n import language_from_telegram_code
from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    PhoneRequiredException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_otp,
    verify_telegram_init_data,
    verify_token,
)
from app.db.database import get_db
from app.db.models import (
    OLXListing,
    Seller,
    TelegramListing,
    User,
    UserApprovalStatus,
    UserRole,
)
from app.db.redis import CacheKeys, get_redis
from app.schemas.auth import (
    AdminLoginRequest,
    AuthResponse,
    BuyerPhoneLoginRequest,
    OLXPhoneLoginRequest,
    RefreshTokenRequest,
    SellerOTPRequest,
    SellerOTPVerifyRequest,
    TelegramAuthRequest,
    TelegramChannelLoginRequest,
    UserMeResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserUpdate
from app.services.account_linking import (
    get_account_linking_service,
    reserve_phone_for_user,
)
from app.utils.phone import normalize_phone, normalize_phone_e164

router = APIRouter()


logger = __import__("logging").getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


async def _apply_pending_referral_if_any(
    db, user: "User", telegram_id: int | None
) -> None:
    """Block D D3 — consume a pending ``ref_<id>`` referral if one was
    stashed for this telegram_id and persist the attribution.

    Guards:
      - Only writes if ``user.referred_by_user_id`` is currently NULL.
      - Self-referral rejected (referrer != new_user_id).
      - All failures are swallowed; attribution is observational and
        must never block the auth flow.
    """
    if telegram_id is None or user is None or user.id is None:
        return
    if getattr(user, "referred_by_user_id", None) is not None:
        return
    try:
        from app.services.deeplink import consume_pending_referral

        pending = await consume_pending_referral(telegram_id)
        if pending is None:
            return
        referrer_id_str, source = pending
        try:
            referrer_id = UUID(referrer_id_str)
        except (TypeError, ValueError):
            return
        if referrer_id == user.id:
            logger.info(
                "ref.self_referral_rejected user=%s tg=%s", user.id, telegram_id
            )
            return
        user.referred_by_user_id = referrer_id
        if source:
            user.referral_source = source[:64]
        await db.flush()
        logger.info(
            "ref.applied user=%s referrer=%s source=%s",
            user.id,
            referrer_id,
            source,
        )
    except Exception:
        logger.warning(
            "ref.apply_failed user=%s tg=%s", user.id, telegram_id, exc_info=True
        )


def _build_auth_response(
    user: User,
    access_token: str,
    refresh_token: str,
    scope: str = "buyer",
) -> AuthResponse:
    """Build AuthResponse from user model."""
    is_seller = user.role in [UserRole.SELLER, UserRole.ADMIN]
    return AuthResponse(
        user_id=str(user.id),
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        avatar_url=user.avatar_url,
        role=user.role.value,
        is_seller=is_seller,
        onboarding_completed=user.onboarding_completed,
        approval_status=user.approval_status.value,
        auth_source=user.auth_source,
        phone=user.phone,
        language=user.language or "ru",
        scope=scope,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """Set authentication cookies on response."""
    is_secure = settings.app_env == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )


async def _generate_and_store_tokens(
    user: User, scope: str = "buyer"
) -> tuple[str, str]:
    """Generate access and refresh tokens, store refresh token in Redis."""
    token_data = {"sub": str(user.id), "scope": scope}
    if user.telegram_id:
        token_data["telegram_id"] = user.telegram_id

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Store refresh token in Redis
    redis = await get_redis()
    token_key = CacheKeys.refresh_token(str(user.id), str(uuid4()))
    await redis.setex(
        token_key,
        settings.refresh_token_expire_days * 86400,
        refresh_token,
    )

    return access_token, refresh_token


# =============================================================================
# Session Check
# =============================================================================


def _verify_telegram_identity_header(
    request: Request,
    user: User,
) -> None:
    """
    Account-switch defense. When the Mini App frontend attaches
    X-Telegram-Init-Data, ONLY block if we can verify it AND it disagrees
    with the cookie session's user.

    LENIENT on verification failures (stale auth_date, unparseable, signature
    mismatch from clock skew, etc.) — those drop through to cookie-only auth
    so a long-idle but otherwise valid session still works. STRICT on positive
    mismatches — proven different telegram_id → 401 → PhoneGate.

    Header is OPTIONAL — dev-web and non-Telegram callers just skip the check.
    """
    init_data = request.headers.get("X-Telegram-Init-Data")
    if not init_data:
        return

    user_data = verify_telegram_init_data(
        init_data, settings.telegram_bot_token
    )
    if not user_data:
        # Couldn't verify (expired auth_date, signature mismatch, malformed).
        # We don't know if there's a real mismatch — fall through and let the
        # cookie-based JWT be authoritative. The whole point of this guard is
        # to catch ACTIVE account switches; without verifiable initData we
        # have no positive evidence of a switch.
        return

    header_telegram_id = user_data.get("telegram_id")
    if header_telegram_id is None:
        return  # Malformed header; fall through to cookie-only identity.

    if user.telegram_id is not None and user.telegram_id != header_telegram_id:
        raise UnauthorizedException(
            "Session does not match active Telegram account"
        )


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Get current authenticated user from session cookie or Authorization header.

    Verifies the access_token and returns user profile data.
    Does NOT check approval status — this is a session check only.
    """
    # Try Authorization header first, then cookie
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix

    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise UnauthorizedException("Missing authentication token")

    payload = verify_token(token, "access")
    if not payload:
        raise UnauthorizedException("Invalid or expired token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token payload")

    result = await db.execute(
        select(User).where(User.id == UUID(user_id), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedException("User not found")

    _verify_telegram_identity_header(request, user)

    is_seller = user.role in [UserRole.SELLER, UserRole.ADMIN]
    token_scope = payload.get("scope")
    return UserMeResponse(
        user_id=str(user.id),
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        avatar_url=user.avatar_url,
        role=user.role.value,
        is_seller=is_seller,
        onboarding_completed=user.onboarding_completed,
        approval_status=user.approval_status.value,
        auth_source=user.auth_source,
        phone=user.phone,
        language=user.language or "ru",
        scope=token_scope,
    )


# =============================================================================
# Profile Update
# =============================================================================


@router.patch("/me", response_model=UserMeResponse)
async def update_profile(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's profile fields.

    Accepts partial updates — only provided fields are changed.
    """
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise BadRequestException("No fields to update")

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    is_seller = user.role in [UserRole.SELLER, UserRole.ADMIN]
    return UserMeResponse(
        user_id=str(user.id),
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        avatar_url=user.avatar_url,
        role=user.role.value,
        is_seller=is_seller,
        onboarding_completed=user.onboarding_completed,
        approval_status=user.approval_status.value,
        auth_source=user.auth_source,
        phone=user.phone,
        language=user.language or "ru",
    )


# =============================================================================
# Telegram Auth
# =============================================================================


@router.post("/telegram", response_model=AuthResponse)
async def authenticate_telegram(
    request: TelegramAuthRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Phone-gated seller auth via Telegram WebApp initData.

    Production entry point. initData alone is NOT sufficient to authenticate —
    every user must have a verified phone number, obtained through Telegram's
    own WebApp.requestContact() consent flow. The bot caches the shared phone
    in Redis; this endpoint consumes it.

    Decision tree:
      - initData invalid                 → 401 UNAUTHORIZED
      - user exists with phone on file   → issue tokens (returning user)
      - phone shared recently (Redis)    → link it, issue tokens
      - otherwise                        → 400 PHONE_REQUIRED (frontend shows
                                           the PhoneGate and drives
                                           requestContact())
    """
    user_data = verify_telegram_init_data(
        request.init_data,
        settings.telegram_bot_token,
    )
    if not user_data:
        raise UnauthorizedException("Invalid Telegram authentication data")

    telegram_id = user_data["telegram_id"]
    first_name = user_data.get("first_name") or f"Seller {telegram_id}"
    linking_service = get_account_linking_service()

    user = await linking_service.find_user_by_identifiers(db, telegram_id=telegram_id)

    # Decide whether we already have an authenticated-worthy phone.
    redis = await get_redis()
    shared_phone_raw = await redis.get(f"contact_share:{telegram_id}")
    shared_phone = shared_phone_raw if shared_phone_raw else None

    has_existing_phone = bool(user and user.phone)
    if not has_existing_phone and not shared_phone:
        # Neither: block and let the Mini App run requestContact().
        raise PhoneRequiredException()

    # Phone uniqueness guard — only when we're about to attach a NEW phone
    # (shared_phone is set AND either the user is new or the shared phone
    # differs from what's on file). Bot-supplied phone is already E.164.
    incoming_phone = shared_phone if shared_phone else None
    if incoming_phone and (not user or user.phone != incoming_phone):
        try:
            await reserve_phone_for_user(
                db,
                incoming_phone=incoming_phone,
                target_user_id=user.id if user else None,
            )
        except BadRequestException:
            # Clear the one-shot key so stale collisions don't loop forever.
            await redis.delete(f"contact_share:{telegram_id}")
            raise

    if user:
        user.first_name = first_name
        user.last_name = user_data.get("last_name")
        user.username = user_data.get("username")
        if user_data.get("photo_url"):
            user.avatar_url = user_data["photo_url"]
        if incoming_phone:
            user.phone = incoming_phone
        linking_service.update_login_info(user)

        # Promote legacy buyers (created by the old /auth/telegram) to sellers.
        if user.role == UserRole.USER:
            user.role = UserRole.SELLER
            user.approval_status = UserApprovalStatus.APPROVED
        await db.flush()
    else:
        # A soft-deleted row can still hold this telegram_id under the unique
        # constraint; clear it before inserting to avoid an IntegrityError.
        collision_result = await db.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        collision = collision_result.scalar_one_or_none()
        if collision:
            collision.telegram_id = None
            await db.flush()

        # Block D D1-Q2: map Telegram language_code → canonical
        # backend identifier. Telegram "uz" maps to "uz_cyrl" (the
        # default Uzbek script). Anything else falls back to "ru".
        user = User(
            id=uuid4(),
            telegram_id=telegram_id,
            phone=incoming_phone,
            first_name=first_name,
            last_name=user_data.get("last_name"),
            username=user_data.get("username"),
            avatar_url=user_data.get("photo_url"),
            language=language_from_telegram_code(user_data.get("language_code")),
            role=UserRole.SELLER,
            approval_status=UserApprovalStatus.APPROVED,
            auth_source="telegram_webapp",
            onboarding_completed=True,
            last_login_at=datetime.utcnow(),
        )
        db.add(user)
        await db.flush()

        # Block D D3 — apply pending referral attribution if the user
        # arrived via /start ref_<id>. Self-referral guarded; existing
        # attribution never overwritten.
        await _apply_pending_referral_if_any(db, user, telegram_id)

    if user.role in (UserRole.SELLER, UserRole.ADMIN):
        seller_result = await db.execute(
            select(Seller).where(Seller.user_id == user.id)
        )
        seller = seller_result.scalar_one_or_none()
        if not seller:
            fallback_company = user.first_name or (
                f"@{user.username}" if user.username else f"Seller {telegram_id}"
            )
            seller = Seller(
                user_id=user.id,
                company_name=fallback_company,
                telegram_username=user.username,
                phone=user.phone,
            )
            db.add(seller)
        elif incoming_phone and not seller.phone:
            # Keep Seller.phone in sync with the newly linked User.phone so
            # listing contact info is populated for existing seller rows too.
            seller.phone = incoming_phone

    await db.commit()
    await db.refresh(user)

    # Consume the one-shot Redis key so a stale share can't re-link later.
    if shared_phone:
        await redis.delete(f"contact_share:{telegram_id}")

    scope = "seller" if user.role in (UserRole.SELLER, UserRole.ADMIN) else "buyer"
    access_token, refresh_token = await _generate_and_store_tokens(user, scope=scope)
    _set_auth_cookies(response, access_token, refresh_token)

    return _build_auth_response(user, access_token, refresh_token, scope=scope)


# =============================================================================
# Token Management
# =============================================================================


@router.post("/refresh", response_model=AuthResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    body: RefreshTokenRequest = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Accepts refresh_token from request body or httpOnly cookie.
    The old refresh token is invalidated and a new pair is issued.
    """
    # Get refresh token from body or cookie
    token = None
    if body and body.refresh_token:
        token = body.refresh_token
    if not token:
        token = request.cookies.get("refresh_token")
    if not token:
        raise UnauthorizedException("Missing refresh token")

    # Verify refresh token
    payload = verify_token(token, "refresh")
    if not payload:
        raise UnauthorizedException("Invalid or expired refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token payload")

    # Get user
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("User not found")

    # Account-switch defense: refuse to mint new tokens for user A if the
    # active Telegram account is B.
    _verify_telegram_identity_header(request, user)

    # Preserve scope from the original token
    scope = payload.get("scope", "buyer")

    # Generate new tokens
    access_token, refresh_token = await _generate_and_store_tokens(user, scope=scope)
    _set_auth_cookies(response, access_token, refresh_token)

    return _build_auth_response(user, access_token, refresh_token, scope=scope)


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """
    Logout and clear authentication cookies.

    Deletion attributes mirror the ones used in _set_auth_cookies so mobile
    Telegram WebApp clients (which are stricter about cookie attribute matching
    than desktop browsers) actually overwrite the existing cookies instead of
    silently ignoring the Set-Cookie header.
    """
    is_secure = settings.app_env == "production"
    response.delete_cookie(
        "access_token",
        path="/",
        secure=is_secure,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        "refresh_token",
        path="/",
        secure=is_secure,
        httponly=True,
        samesite="lax",
    )

    return MessageResponse(message="Successfully logged out")


# =============================================================================
# Development Endpoints
# =============================================================================


@router.post("/dev-login", response_model=AuthResponse)
async def dev_login(
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Development-only login endpoint.
    Creates or retrieves a test user and returns auth tokens.

    WARNING: This endpoint is only available in development mode.
    """
    if settings.app_env == "production":
        raise BadRequestException("This endpoint is not available in production")

    # Use a fixed dev telegram_id
    dev_telegram_id = 790863031

    # Get or create dev user
    result = await db.execute(select(User).where(User.telegram_id == dev_telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        # Create dev user
        user = User(
            id=uuid4(),
            telegram_id=dev_telegram_id,
            first_name="Dev",
            last_name="User",
            username="devuser",
            language="en",
            role=UserRole.USER,
            onboarding_completed=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Generate tokens
    token_data = {"sub": str(user.id), "telegram_id": user.telegram_id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Dev mode, no HTTPS
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # Dev mode, no HTTPS
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )

    return _build_auth_response(user, access_token, refresh_token)


# =============================================================================
# Seller Auth (OLX Phone / Telegram Channel)
# =============================================================================


@router.post("/olx-phone", response_model=AuthResponse)
async def login_olx_phone(
    request: OLXPhoneLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Login as an OLX seller by phone number.

    Checks if crawled OLX listings exist for this phone.
    If yes, creates or retrieves User + Seller and issues JWT.
    """
    phone = normalize_phone_e164(request.phone)
    phone_suffix = normalize_phone(request.phone)

    if not phone or not phone_suffix or len(phone_suffix) != 9:
        raise BadRequestException("Invalid phone number format")

    # Check OLX listings exist for this phone
    count_q = (
        select(func.count())
        .select_from(OLXListing)
        .where(func.right(OLXListing.contact_phone, 9) == phone_suffix)
    )
    result = await db.execute(count_q)
    olx_count = result.scalar() or 0

    if olx_count == 0:
        raise BadRequestException("No OLX listings found for this phone number")

    # Find existing user by canonical phone
    user_q = select(User).where(User.phone == phone, User.deleted_at.is_(None))
    user_result = await db.execute(user_q)
    user = user_result.scalar_one_or_none()

    # Reserve the phone — frees stale rows + hard-stops on active clash.
    await reserve_phone_for_user(
        db, incoming_phone=phone, target_user_id=user.id if user else None
    )

    if user:
        user.last_login_at = datetime.utcnow()
        user.auth_source = "olx_phone"
    else:
        user = User(
            id=uuid4(),
            first_name="OLX Seller",
            phone=phone,
            role=UserRole.SELLER,
            auth_source="olx_phone",
            approval_status=UserApprovalStatus.APPROVED,
            onboarding_completed=True,
            last_login_at=datetime.utcnow(),
        )
        db.add(user)
        await db.flush()

    # Ensure seller profile exists
    seller_q = select(Seller).where(Seller.user_id == user.id)
    seller_result = await db.execute(seller_q)
    seller = seller_result.scalar_one_or_none()

    if not seller:
        seller = Seller(
            user_id=user.id,
            phone=phone,
            company_name=f"OLX Seller ({phone_suffix[-4:]})",
        )
        db.add(seller)
    else:
        seller.phone = phone

    await db.commit()
    await db.refresh(user)

    access_token, refresh_token = await _generate_and_store_tokens(user, scope="seller")
    _set_auth_cookies(response, access_token, refresh_token)

    return _build_auth_response(user, access_token, refresh_token, scope="seller")


@router.post("/telegram-channel", response_model=AuthResponse)
async def login_telegram_channel(
    request: TelegramChannelLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Login as a Telegram channel seller by channel name.

    Checks if crawled Telegram listings exist for this channel.
    If yes, creates or retrieves User + Seller and issues JWT.
    """
    channel_name = request.channel_name.strip().lstrip("@").lower()

    if not channel_name:
        raise BadRequestException("Invalid channel name")

    # Check Telegram listings exist for this channel
    count_q = (
        select(func.count())
        .select_from(TelegramListing)
        .where(
            func.lower(func.replace(TelegramListing.source_channel, "@", ""))
            == channel_name
        )
    )
    result = await db.execute(count_q)
    tg_count = result.scalar() or 0

    if tg_count == 0:
        raise BadRequestException("No Telegram listings found for this channel")

    # Find existing user by username + auth_source
    user_q = select(User).where(
        User.username == channel_name,
        User.auth_source == "tg_channel",
        User.deleted_at.is_(None),
    )
    user_result = await db.execute(user_q)
    user = user_result.scalar_one_or_none()

    if user:
        user.last_login_at = datetime.utcnow()
    else:
        user = User(
            id=uuid4(),
            first_name=f"@{channel_name}",
            username=channel_name,
            role=UserRole.SELLER,
            auth_source="tg_channel",
            approval_status=UserApprovalStatus.APPROVED,
            onboarding_completed=True,
            last_login_at=datetime.utcnow(),
        )
        db.add(user)
        await db.flush()

    # Ensure seller profile exists
    seller_q = select(Seller).where(Seller.user_id == user.id)
    seller_result = await db.execute(seller_q)
    seller = seller_result.scalar_one_or_none()

    if not seller:
        seller = Seller(
            user_id=user.id,
            source_channel=channel_name,
            telegram_username=channel_name,
            company_name=f"@{channel_name}",
        )
        db.add(seller)
    else:
        seller.source_channel = channel_name
        seller.telegram_username = channel_name

    await db.commit()
    await db.refresh(user)

    access_token, refresh_token = await _generate_and_store_tokens(user, scope="seller")
    _set_auth_cookies(response, access_token, refresh_token)

    return _build_auth_response(user, access_token, refresh_token, scope="seller")


# =============================================================================
# Seller OTP Auth (Phone + Telegram OTP)
# =============================================================================

OTP_EXPIRY_SECONDS = 600  # 10 minutes
OTP_MAX_ATTEMPTS = 3
OTP_RATE_LIMIT_SECONDS = 600  # 10 min window
OTP_RATE_LIMIT_MAX = 3  # max 3 requests per window


@router.post("/seller-otp")
async def request_seller_otp(
    request: SellerOTPRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    Request OTP for seller phone login.

    Finds the bot-registered seller by phone number and sends a 6-digit
    OTP code to their Telegram account via the B2B bot.
    """
    phone = request.phone
    phone_suffix = normalize_phone(phone)

    if not phone_suffix or len(phone_suffix) != 9:
        raise BadRequestException("Неверный формат номера телефона")

    redis = await get_redis()

    # Rate limiting
    rate_key = CacheKeys.rate_limit(f"seller_otp:{phone_suffix}")
    rate_count = await redis.get(rate_key)
    if rate_count and int(rate_count) >= OTP_RATE_LIMIT_MAX:
        raise BadRequestException("Слишком много запросов. Попробуйте через 10 минут.")

    # Find existing user by phone (last 9 digits match)
    user_q = select(User).where(
        func.right(User.phone, 9) == phone_suffix,
        User.deleted_at.is_(None),
    )
    user_result = await db.execute(user_q)
    user = user_result.scalar_one_or_none()

    bot_username = settings.telegram_bot_username or "ucharmarket_bot"

    # Do NOT create user here — user creation happens only on OTP verify.
    # We only need a telegram_id to deliver the OTP message.

    if user and not settings.auto_approve_users:
        if user.approval_status == UserApprovalStatus.REJECTED:
            raise BadRequestException("Ваш аккаунт был отклонён.")

    # Resolve telegram_id for OTP delivery
    tg_id = user.telegram_id if user else None

    if not tg_id:
        # Try to get telegram_id from initData (Telegram Mini App context)
        if request.init_data:
            tg_user_data = verify_telegram_init_data(
                request.init_data, settings.telegram_bot_token
            )
            if tg_user_data:
                tg_id = tg_user_data["telegram_id"]

        # Or from the authenticated buyer session
        if not tg_id and current_user and current_user.telegram_id:
            tg_id = current_user.telegram_id

    if not tg_id and not settings.debug:
        # In production, telegram_id is required for OTP delivery
        link = f"https://t.me/{bot_username}?start=link_{phone_suffix}"
        raise BadRequestException(
            f"Telegram не привязан. Нажмите на ссылку, затем попробуйте снова: {link}"
        )

    # If we found a tg_id for an existing user that didn't have one, save it
    if user and tg_id and not user.telegram_id:
        # Remove telegram_id from any other user to avoid unique violation
        old_user_q = await db.execute(
            select(User).where(
                User.telegram_id == tg_id,
                User.id != user.id,
                User.deleted_at.is_(None),
            )
        )
        old_user = old_user_q.scalar_one_or_none()
        if old_user:
            old_user.telegram_id = None
            await db.flush()

        user.telegram_id = tg_id
        await db.commit()

    # Store the resolved telegram_id in Redis so verify can link it to new users
    if tg_id:
        await redis.setex(
            f"seller_otp_tg:{phone_suffix}",
            OTP_EXPIRY_SECONDS,
            str(tg_id),
        )

    # Generate and store OTP
    otp_code = generate_otp()
    await redis.setex(CacheKeys.seller_otp(phone_suffix), OTP_EXPIRY_SECONDS, otp_code)

    # Reset attempts counter
    await redis.delete(CacheKeys.seller_otp_attempts(phone_suffix))

    # Increment rate limit
    if rate_count:
        await redis.incr(rate_key)
    else:
        await redis.setex(rate_key, OTP_RATE_LIMIT_SECONDS, 1)

    # Send OTP via Telegram bot
    dev_otp = None
    if tg_id:
        from app.bot.notifications import get_bot_instance

        bot = get_bot_instance()
        if bot:
            try:
                await bot.send_message(
                    chat_id=tg_id,
                    text=(
                        f"🔐 <b>Код для входа в кабинет продавца:</b>\n\n"
                        f"<code>{otp_code}</code>\n\n"
                        f"Код действителен 10 минут. Никому не сообщайте его."
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                if not settings.debug:
                    raise BadRequestException(
                        "Не удалось отправить код. Убедитесь, что бот не заблокирован."
                    )
                else:
                    dev_otp = otp_code
    elif settings.debug:
        # Dev mode: no telegram_id, return OTP in response
        dev_otp = otp_code

    masked_phone = f"+998 {phone_suffix[:2]} *** ** {phone_suffix[-2:]}"
    result: dict = {
        "message": f"Код отправлен в Telegram ({masked_phone})",
        "expires_in": OTP_EXPIRY_SECONDS,
    }
    if dev_otp:
        result["_dev_otp"] = dev_otp
    return result


@router.post("/seller-otp/verify", response_model=AuthResponse)
async def verify_seller_otp(
    request: SellerOTPVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify OTP and login as seller.

    Validates the OTP code sent to the seller's Telegram, then issues JWT tokens.
    """
    phone = request.phone
    phone_suffix = normalize_phone(phone)

    if not phone_suffix or len(phone_suffix) != 9:
        raise BadRequestException("Неверный формат номера телефона")

    redis = await get_redis()

    # Check attempts
    attempts_key = CacheKeys.seller_otp_attempts(phone_suffix)
    attempts = await redis.get(attempts_key)
    if attempts and int(attempts) >= OTP_MAX_ATTEMPTS:
        # Clear OTP on max attempts
        await redis.delete(CacheKeys.seller_otp(phone_suffix))
        raise BadRequestException("Превышено количество попыток. Запросите новый код.")

    # Get stored OTP
    stored_otp = await redis.get(CacheKeys.seller_otp(phone_suffix))
    if not stored_otp:
        raise BadRequestException("Код истёк. Запросите новый код.")

    # Increment attempts
    if attempts:
        await redis.incr(attempts_key)
    else:
        await redis.setex(attempts_key, OTP_EXPIRY_SECONDS, 1)

    # Verify OTP
    if stored_otp != request.otp_code:
        current_attempts = int(attempts or 0) + 1
        remaining = OTP_MAX_ATTEMPTS - current_attempts
        raise BadRequestException(f"Неверный код. Осталось попыток: {remaining}")

    # OTP verified - clean up
    await redis.delete(CacheKeys.seller_otp(phone_suffix))
    await redis.delete(attempts_key)

    # Find user by phone
    user_q = select(User).where(
        func.right(User.phone, 9) == phone_suffix,
        User.deleted_at.is_(None),
    )
    user_result = await db.execute(user_q)
    user = user_result.scalar_one_or_none()

    canonical_phone = f"+998{phone_suffix}"

    if not user:
        # User doesn't exist yet — create on successful OTP verification.
        # Recover telegram_id stored during OTP request.
        stored_tg_id = await redis.get(f"seller_otp_tg:{phone_suffix}")
        tg_id = int(stored_tg_id) if stored_tg_id else None

        # If we have a tg_id, clear it from any other user first.
        if tg_id:
            old_user_q = await db.execute(
                select(User).where(
                    User.telegram_id == tg_id,
                    User.deleted_at.is_(None),
                )
            )
            old_user = old_user_q.scalar_one_or_none()
            if old_user:
                old_user.telegram_id = None
                await db.flush()

        # Free any stale users.phone / sellers.phone before insert so the
        # unique index doesn't trip.
        await reserve_phone_for_user(
            db, incoming_phone=canonical_phone, target_user_id=None
        )

        # Hotfix (Block C decision-pass G3): two concurrent verify requests
        # for the same OTP can both reach this branch (Redis GET is
        # non-destructive). The second INSERT then violates the
        # users.phone UNIQUE index. Catch IntegrityError, roll back the
        # nested savepoint, and re-fetch the row that won.
        try:
            user = User(
                phone=canonical_phone,
                first_name=f"Seller {phone_suffix[-4:]}",
                telegram_id=tg_id,
                role=UserRole.SELLER,
                approval_status=(
                    UserApprovalStatus.APPROVED
                    if settings.auto_approve_users
                    else UserApprovalStatus.PENDING
                ),
                auth_source="seller_otp",
                last_login_at=datetime.utcnow(),
            )
            db.add(user)
            await db.flush()
        except IntegrityError:
            await db.rollback()
            user_result = await db.execute(
                select(User).where(
                    func.right(User.phone, 9) == phone_suffix,
                    User.deleted_at.is_(None),
                )
            )
            user = user_result.scalar_one_or_none()
            if user is None:
                # Should never happen — UNIQUE violation but no row found?
                raise BadRequestException(
                    "Не удалось создать аккаунт. Попробуйте ещё раз."
                )
            user.last_login_at = datetime.utcnow()
            await db.flush()

        # Clean up stored telegram_id
        await redis.delete(f"seller_otp_tg:{phone_suffix}")
    else:
        # Existing user — update login info
        user.last_login_at = datetime.utcnow()
        if not user.auth_source or user.auth_source == "bot":
            user.auth_source = "seller_otp"

    # Ensure seller role
    if user.role not in (UserRole.SELLER, UserRole.ADMIN):
        user.role = UserRole.SELLER

    # Ensure seller profile exists
    seller_result = await db.execute(select(Seller).where(Seller.user_id == user.id))
    seller = seller_result.scalar_one_or_none()
    if not seller:
        seller = Seller(
            user_id=user.id,
            phone=user.phone,
            company_name=user.first_name or f"Продавец ({phone_suffix[-4:]})",
        )
        db.add(seller)

    await db.commit()
    await db.refresh(user)

    # Generate tokens
    access_token, refresh_token = await _generate_and_store_tokens(user, scope="seller")
    _set_auth_cookies(response, access_token, refresh_token)

    return _build_auth_response(user, access_token, refresh_token, scope="seller")


@router.get("/seller-bot-info")
async def get_seller_bot_info():
    """
    Get bot username for registration link.
    Public endpoint — no authentication required.
    """
    return {
        "bot_username": settings.telegram_bot_username,
    }


# =============================================================================
# Buyer Auth (Phone)
# =============================================================================


@router.post("/buyer-phone", response_model=AuthResponse)
async def login_buyer_phone(
    request: BuyerPhoneLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Login as a buyer by phone number.

    Creates or retrieves a user by phone and issues JWT.
    No crawled-data check — any valid phone can log in.
    """
    phone = normalize_phone_e164(request.phone)
    if not phone:
        raise BadRequestException("Invalid phone number format")

    # Find existing user by canonical phone
    user_q = select(User).where(User.phone == phone, User.deleted_at.is_(None))
    user_result = await db.execute(user_q)
    user = user_result.scalar_one_or_none()

    # Reserve the phone — frees stale rows + hard-stops on active clash.
    await reserve_phone_for_user(
        db, incoming_phone=phone, target_user_id=user.id if user else None
    )

    now = datetime.utcnow()

    if user:
        user.last_login_at = now
        user.first_name = request.first_name
        if request.last_name is not None:
            user.last_name = request.last_name
        if not user.auth_source:
            user.auth_source = "buyer_phone"
    else:
        user = User(
            id=uuid4(),
            first_name=request.first_name,
            last_name=request.last_name,
            phone=phone,
            role=UserRole.USER,
            auth_source="buyer_phone",
            approval_status=UserApprovalStatus.APPROVED,
            onboarding_completed=True,
            last_login_at=now,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    access_token, refresh_token = await _generate_and_store_tokens(user, scope="buyer")
    _set_auth_cookies(response, access_token, refresh_token)

    return _build_auth_response(user, access_token, refresh_token, scope="buyer")


# =============================================================================
# Admin Auth (Username/Password)
# =============================================================================


@router.post("/admin-login", response_model=AuthResponse)
async def admin_login(
    request: AdminLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Admin login with username and password.

    Validates credentials against config and returns JWT tokens.
    Creates or retrieves admin user account.
    """
    # Verify credentials
    if (
        request.username != settings.admin_username
        or request.password != settings.admin_password
    ):
        raise UnauthorizedException("Invalid admin credentials")

    # Find or create admin user
    admin_username = f"admin_{request.username.lower().replace(' ', '_')}"
    user_q = select(User).where(
        User.username == admin_username,
        User.role == UserRole.ADMIN,
        User.deleted_at.is_(None),
    )
    user_result = await db.execute(user_q)
    user = user_result.scalar_one_or_none()

    now = datetime.utcnow()

    if user:
        user.last_login_at = now
    else:
        user = User(
            id=uuid4(),
            first_name="Admin",
            last_name=request.username,
            username=admin_username,
            role=UserRole.ADMIN,
            auth_source="admin_login",
            approval_status=UserApprovalStatus.APPROVED,
            onboarding_completed=True,
            last_login_at=now,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    access_token, refresh_token = await _generate_and_store_tokens(user, scope="admin")
    _set_auth_cookies(response, access_token, refresh_token)

    return _build_auth_response(user, access_token, refresh_token, scope="admin")
