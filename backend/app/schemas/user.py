"""User schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import UTCDateTime

# Block D D1 — canonical backend identifiers. Frontend folder names
# use "uz-cyrl" (kebab); we accept either form on input and normalise
# to underscore form before persisting.
SUPPORTED_LANGUAGES = ("ru", "uz", "uz_cyrl")


def _normalize_language(value: str) -> str:
    """Map kebab → underscore form; reject unknown values."""
    canonical = value.lower().replace("-", "_")
    if canonical not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"language must be one of {SUPPORTED_LANGUAGES}, got {value!r}"
        )
    return canonical


class UserBase(BaseModel):
    """Base user schema."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    language: str = Field(default="ru", max_length=10)

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        return _normalize_language(value)


class UserCreate(UserBase):
    """Schema for creating a user."""

    telegram_id: int
    username: Optional[str] = None
    avatar_url: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user profile. Phone is not editable — it is a verified field."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=10)
    onboarding_completed: Optional[bool] = None
    seller_type: Optional[str] = Field(
        None,
        max_length=20,
        pattern=r"^(owner|realtor|developer)$",
    )
    seller_telegram: Optional[str] = Field(None, max_length=100)

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: Optional[str]) -> Optional[str]:
        return _normalize_language(value) if value is not None else None


class UserResponse(BaseModel):
    """User response schema."""

    id: UUID
    telegram_id: int
    phone: Optional[str]
    first_name: str
    last_name: Optional[str]
    username: Optional[str]
    avatar_url: Optional[str]
    language: str
    role: str
    onboarding_completed: bool
    seller_type: Optional[str] = None
    seller_telegram: Optional[str] = None
    created_at: UTCDateTime
    updated_at: UTCDateTime

    model_config = {"from_attributes": True}


class UserInDB(UserResponse):
    """User schema with database fields."""

    deleted_at: Optional[UTCDateTime]
    deletion_reason: Optional[str]


class UserStats(BaseModel):
    """User statistics for bottom nav badges."""

    favorites_count: int = 0
    unread_count: int = 0
    saved_searches_count: int = 0
