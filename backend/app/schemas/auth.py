"""Authentication schemas."""

from typing import Optional

from pydantic import BaseModel, Field

# =============================================================================
# Telegram Auth
# =============================================================================


class TelegramAuthRequest(BaseModel):
    """Telegram WebApp authentication request."""

    init_data: str = Field(..., description="Telegram initData string")


class TelegramUserData(BaseModel):
    """Parsed Telegram user data."""

    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: bool = False
    photo_url: Optional[str] = None
    auth_date: int


# =============================================================================
# Token Management
# =============================================================================


class TokenResponse(BaseModel):
    """Token response after successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiry in seconds")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


# =============================================================================
# Auth Response
# =============================================================================


class UserMeResponse(BaseModel):
    """Current user profile response (no tokens)."""

    user_id: str
    telegram_id: Optional[int] = None
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    is_seller: bool
    onboarding_completed: bool
    approval_status: str  # pending, approved, rejected
    auth_source: Optional[str] = None
    phone: Optional[str] = None
    # Block D D1: canonical value ("ru" | "uz" | "uz_cyrl"). Frontend
    # i18n maps "uz_cyrl" → "uz-cyrl" at its boundary.
    language: str = "ru"
    scope: Optional[str] = None  # "admin" | "buyer" | "seller"
    seller_type: Optional[str] = None
    seller_telegram: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response with user info."""

    user_id: str
    telegram_id: Optional[int] = None
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    is_seller: bool
    onboarding_completed: bool
    approval_status: str  # pending, approved, rejected
    auth_source: Optional[str] = None
    phone: Optional[str] = None
    language: str = "ru"
    scope: str  # "admin" | "buyer" | "seller"
    seller_type: Optional[str] = None
    seller_telegram: Optional[str] = None
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# =============================================================================
# Seller Auth (OLX Phone / Telegram Channel)
# =============================================================================


class OLXPhoneLoginRequest(BaseModel):
    """Login as OLX seller by phone number."""

    phone: str = Field(..., pattern=r"^\+998\d{9}$")


class TelegramChannelLoginRequest(BaseModel):
    """Login as Telegram channel seller."""

    channel_name: str = Field(..., min_length=2, max_length=200)


class BuyerPhoneLoginRequest(BaseModel):
    """Login as buyer by phone number."""

    phone: str = Field(..., pattern=r"^\+998\d{9}$")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)


# =============================================================================
# Seller OTP Auth
# =============================================================================


class SellerOTPRequest(BaseModel):
    """Request OTP for seller phone login."""

    phone: str = Field(..., pattern=r"^\+998\d{9}$")
    init_data: Optional[str] = Field(
        None, description="Telegram initData for auto-linking telegram_id"
    )


class SellerOTPVerifyRequest(BaseModel):
    """Verify OTP and login as seller."""

    phone: str = Field(..., pattern=r"^\+998\d{9}$")
    otp_code: str = Field(..., min_length=6, max_length=6)


# =============================================================================
# Admin Auth
# =============================================================================


class AdminLoginRequest(BaseModel):
    """Admin login with username and password."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=100)
