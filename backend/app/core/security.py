"""Security utilities: JWT tokens, password hashing, Telegram auth."""

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import parse_qsl

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.refresh_token_expire_days)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Verify a JWT token and return its payload."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None


def verify_telegram_init_data(
    init_data: str, bot_token: str
) -> Optional[Dict[str, Any]]:
    """
    Verify Telegram WebApp initData.

    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    Args:
        init_data: The initData string from Telegram WebApp
        bot_token: The bot token to verify against

    Returns:
        Parsed user data if valid, None otherwise
    """
    try:
        # Parse the init data
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))

        # Get the hash from the data
        received_hash = parsed_data.pop("hash", None)
        if not received_hash:
            return None

        # Check auth_date is within 24 hours
        auth_date = int(parsed_data.get("auth_date", 0))
        if time.time() - auth_date > 86400:  # 24 hours
            return None

        # Build the data check string
        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(parsed_data.items())
        )

        # Calculate the secret key
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256,
        ).digest()

        # Calculate the hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Verify the hash
        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        # Parse user data
        import json

        user_data = json.loads(parsed_data.get("user", "{}"))

        return {
            "telegram_id": user_data.get("id"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "username": user_data.get("username"),
            "language_code": user_data.get("language_code"),
            "is_premium": user_data.get("is_premium", False),
            "photo_url": user_data.get("photo_url"),
            "auth_date": auth_date,
        }
    except Exception:
        return None


def generate_otp() -> str:
    """Generate a 6-digit OTP code."""
    import secrets

    return str(secrets.randbelow(900000) + 100000)
