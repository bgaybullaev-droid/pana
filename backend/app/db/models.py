"""SQLAlchemy database models for Real Estate."""

import enum
from datetime import datetime, time
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.database import Base

# =============================================================================
# Enums
# =============================================================================


class UserRole(str, enum.Enum):
    """User role enum."""

    USER = "user"
    SELLER = "seller"
    ADMIN = "admin"


class UserApprovalStatus(str, enum.Enum):
    """User approval status enum."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ListingType(str, enum.Enum):
    """Listing type enum."""

    SELL = "sell"
    RENT = "rent"


class PropertyType(str, enum.Enum):
    """Property type enum."""

    APARTMENT = "apartment"
    HOUSE = "house"
    COMMERCIAL = "commercial"
    LAND = "land"


class ListingStatus(str, enum.Enum):
    """Listing status enum."""

    ACTIVE = "active"
    PAUSED = "paused"
    SOLD = "sold"
    DELETED = "deleted"
    EXPIRED = "expired"


class ModerationStatus(str, enum.Enum):
    """Moderation status enum."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SourceType(str, enum.Enum):
    """Listing source type enum."""

    MANUAL = "manual"
    CLAIMED = "claimed"
    PARSED = "parsed"


class Currency(str, enum.Enum):
    """Currency enum."""

    USD = "USD"
    UZS = "UZS"


class ClaimStatus(str, enum.Enum):
    """Claim status enum."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class NotificationType(str, enum.Enum):
    """Notification type enum."""

    COMMENT_REPLY = "comment_reply"
    PRICE_DROP = "price_drop"
    NEW_LISTING = "new_listing"
    FAVORITE_UPDATE = "favorite_update"
    LISTING_APPROVED = "listing_approved"
    LISTING_REJECTED = "listing_rejected"
    NEW_COMMENT = "new_comment"


class VerificationMethod(str, enum.Enum):
    """Verification method enum."""

    PHONE_MATCH = "phone_match"
    OTP = "otp"
    MANUAL = "manual"


# =============================================================================
# Models
# =============================================================================


class User(Base):
    """User model (Ф-7 to Ф-9)."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    # Primary identifier
    telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        unique=True,
        nullable=True,
        index=True,
    )

    # Timestamps
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Profile fields
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="ru")
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER,
    )
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Approval status (admin approval required)
    approval_status: Mapped[UserApprovalStatus] = mapped_column(
        Enum(UserApprovalStatus),
        default=UserApprovalStatus.PENDING,
        index=True,
    )
    approval_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Auth source (telegram, olx_phone, tg_channel, dev)
    auth_source: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deletion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    seller: Mapped[Optional["Seller"]] = relationship(
        "Seller",
        back_populates="user",
        uselist=False,
    )
    favorites: Mapped[List["Favorite"]] = relationship(
        "Favorite",
        back_populates="user",
    )
    saved_searches: Mapped[List["SavedSearch"]] = relationship(
        "SavedSearch",
        back_populates="user",
    )
    notification_preferences: Mapped[Optional["NotificationPreferences"]] = (
        relationship(
            "NotificationPreferences",
            back_populates="user",
            uselist=False,
        )
    )
    user_preferences: Mapped[Optional["UserPreferences"]] = relationship(
        "UserPreferences",
        back_populates="user",
        uselist=False,
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        foreign_keys="[Notification.user_id]",
    )


class Seller(Base):
    """Seller model (Ф-84 to Ф-97)."""

    __tablename__ = "sellers"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Profile (Ф-90 to Ф-97)
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Contact
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone_public: Mapped[bool] = mapped_column(Boolean, default=True)

    # Source channel (for Telegram channel sellers)
    source_channel: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # ── Sprint 7: developer / trust score (T-027, T-028) ──────────────
    is_developer_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    trust_score: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, server_default="0"
    )

    # Social
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    instagram_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verification_method: Mapped[Optional[VerificationMethod]] = mapped_column(
        Enum(VerificationMethod),
        nullable=True,
    )

    # Statistics
    listings_count: Mapped[int] = mapped_column(Integer, default=0)
    total_views: Mapped[int] = mapped_column(Integer, default=0)
    total_contacts: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="seller")
    listings: Mapped[List["Listing"]] = relationship(
        "Listing",
        back_populates="seller",
    )


class Listing(Base):
    """Listing model (Ф-98 to Ф-112)."""

    __tablename__ = "listings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    seller_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Type & Category
    type: Mapped[ListingType] = mapped_column(Enum(ListingType), nullable=False)
    property_type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType),
        nullable=False,
    )

    # Property Details
    rooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    area: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    floor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    building_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # new / secondary
    condition: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # euro / cosmetic / needs_repair / rough
    land_purpose: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # private / industrial
    living_area: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    kitchen_area: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    land_area: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    house_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    house_condition: Mapped[Optional[list]] = mapped_column(
        ARRAY(String), nullable=True
    )
    location_type: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    water_supply: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    electricity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    heating: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    gas_supply: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sewage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_furnished: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_negotiable: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    amenities: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    nearby_amenities: Mapped[Optional[list]] = mapped_column(
        ARRAY(String), nullable=True
    )

    # ── Sprint 2: Rent fields (T-002, T-003) — rent only per visibility matrix
    rent_period: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # long_term / daily
    deposit: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    utilities_incl: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    min_rent_months: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 1, 3, 6, 12 — only when rent_period='long_term'
    allowed_students: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    allowed_pets: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    rent_payment: Mapped[Optional[list]] = mapped_column(
        ARRAY(String(20)), nullable=True
    )  # elements: cash, payme, click, bank (validated at API layer)

    # ── Sprint 2: Sale finance flags (T-004) — sale only per visibility matrix
    mortgage_ok: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    installment_ok: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    halol_ok: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )

    # ── Sprint 2: Deed type (T-005) — sale only per visibility matrix
    deed_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # cadastre / order / other

    # ── Sprint 3: Cross-cutting location (T-001) ──────────────────────
    urgent_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    microdistrict: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    jk_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    landmark: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metro_station: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    seller_telegram: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Sprint 4: Commercial overhaul (T-009) ─────────────────────────
    commercial_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    price_per_sqm: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    ceiling_height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entrance: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    parking_comm: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    building_class: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # ── Sprint 5: Breaking renames — dual-read columns (T-006, T-008) ─
    market_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    wall_material: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    furniture: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Sprint 6: Property-type polish (T-011, T-014, T-015) ──────────
    garage: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    basement: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    buildings_exist: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    fence: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    land_shape: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    balcony: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    listing_subtype: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    floor_plan_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # ── Sprint 7: Optional FK to housing complexes (T-027) ────────────
    jk_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("housing_complexes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Sprint 8: SEO slug (T-023) ────────────────────────────────────
    slug: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=False
    )

    # Location
    region: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    district: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Price
    price: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency),
        default=Currency.USD,
    )

    # Content
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    seller_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # "owner" or "realtor"

    # Multilingual content
    original_language: Mapped[str] = mapped_column(
        String(5), default="ru", server_default="ru"
    )
    title_ru: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    title_uz: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_uz: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address_ru: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    address_uz: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    translation_status: Mapped[Optional[str]] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    translated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Source & Deduplication
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType),
        default=SourceType.PARSED,
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signature_hash: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )
    master_record_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status
    status: Mapped[ListingStatus] = mapped_column(
        Enum(ListingStatus),
        default=ListingStatus.ACTIVE,
        index=True,
    )
    moderation_status: Mapped[ModerationStatus] = mapped_column(
        Enum(ModerationStatus),
        default=ModerationStatus.PENDING,
    )
    moderation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moderated_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    moderated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Statistics
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    contacts_count: Mapped[int] = mapped_column(Integer, default=0)
    favorites_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)

    # Promotion (Phase 2)
    is_boosted: Mapped[bool] = mapped_column(Boolean, default=False)
    boost_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_highlighted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Optimistic locking
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    seller: Mapped[Optional["Seller"]] = relationship(
        "Seller",
        back_populates="listings",
    )
    images: Mapped[List["ListingImage"]] = relationship(
        "ListingImage",
        back_populates="listing",
        order_by="ListingImage.position",
    )
    master_record: Mapped[Optional["Listing"]] = relationship(
        "Listing",
        remote_side=[id],
        backref="duplicates",
    )

    # Indexes
    __table_args__ = (
        Index("idx_listings_type_status", "type", "status"),
        Index(
            "idx_listings_active",
            "status",
            postgresql_where=(status == ListingStatus.ACTIVE),
        ),
    )


class HousingComplex(Base):
    """Sprint 7 — Housing complexes (T-027). Coexists with the free-text
    `Listing.jk_name` from Sprint 3 (T-001); FK is optional."""

    __tablename__ = "housing_complexes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    developer_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True,
    )
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ListingImage(Base):
    """Listing image model (Ф-110)."""

    __tablename__ = "listing_images"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    listing_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Image URLs
    original_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    medium_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    large_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Position
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    # Upload status
    upload_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
    )  # pending, processing, completed, failed

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    # Relationships
    listing: Mapped["Listing"] = relationship("Listing", back_populates="images")


class ListingClaim(Base):
    """Listing claim model (Ф-106, Ф-107)."""

    __tablename__ = "listing_claims"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    listing_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Status
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus),
        default=ClaimStatus.PENDING,
    )
    verification_method: Mapped[Optional[VerificationMethod]] = mapped_column(
        Enum(VerificationMethod),
        nullable=True,
    )

    # OTP verification
    otp_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    otp_attempts: Mapped[int] = mapped_column(Integer, default=0)
    otp_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Review
    reviewed_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Favorite(Base):
    """User favorites model (Ф-67)."""

    __tablename__ = "favorites"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="uq_user_listing_favorite"),
    )


class Comment(Base):
    """Comment model for listing comments."""

    __tablename__ = "comments"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    listing_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # Statistics
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    replies_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    parent: Mapped[Optional["Comment"]] = relationship(
        "Comment",
        remote_side=[id],
        backref="replies",
    )

    __table_args__ = (
        Index("idx_comments_listing_created", "listing_id", "created_at"),
    )


class CommentLike(Base):
    """Comment like model."""

    __tablename__ = "comment_likes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    comment_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    # Relationships
    comment: Mapped["Comment"] = relationship("Comment")
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="uq_comment_user_like"),
    )


class SavedSearch(Base):
    """Saved search model (Ф-68)."""

    __tablename__ = "saved_searches"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # PR-B: name no longer NOT NULL — frontend allows empty / unnamed
    # searches (displayed as "Unnamed" in UI). Keep nullable=False to match
    # DB; default to empty string in schema builder so inserts don't fail.
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    # Optional free-text portion of the search (q=…).
    query: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Serialized sort order the UI picked (e.g. "relevance", "price_asc").
    sort: Mapped[str] = mapped_column(
        String(30), nullable=False, default="relevance", server_default="relevance"
    )
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    notify_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )
    # PR-B: renamed from `last_run_at` to match frontend-facing semantics
    # ("when did the user last see this saved search", which drives
    # `new_count` computation). Migration keeps the existing data.
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="saved_searches")


class UserFollowsSeller(Base):
    """User follows seller model (Ф-70)."""

    __tablename__ = "user_follows_seller"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "seller_id", name="uq_user_follows_seller"),
    )


class NotificationPreferences(Base):
    """Notification preferences model (Ф-77 to Ф-80)."""

    __tablename__ = "notification_preferences"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # General
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Time window (Ф-80)
    time_start: Mapped[Time] = mapped_column(Time, default=time(9, 0))
    time_end: Mapped[Time] = mapped_column(Time, default=time(21, 0))
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Tashkent")

    # Limits (Ф-79)
    daily_limit: Mapped[int] = mapped_column(Integer, default=10)

    # Per-type opt-out (empty = all enabled)
    disabled_types: Mapped[List[str]] = mapped_column(ARRAY(String), default=[])

    # Filters (Ф-77)
    districts: Mapped[List[str]] = mapped_column(ARRAY(String), default=[])
    property_types: Mapped[List[str]] = mapped_column(ARRAY(String), default=[])
    listing_types: Mapped[List[str]] = mapped_column(ARRAY(String), default=[])
    price_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rooms: Mapped[List[int]] = mapped_column(ARRAY(Integer), default=[])

    # PR-A — delivery-budget columns (backs /notification-settings).
    # Decoupled from the filter-preset above because the frontend's
    # NotificationSettings product is purely delivery-budget.
    time_windows: Mapped[List[str]] = mapped_column(
        ARRAY(String(20)),
        default=lambda: ["morning", "afternoon", "evening"],
        server_default="{morning,afternoon,evening}",
        nullable=False,
    )
    source_saved_searches: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    source_seller_follows: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    source_ai_recs: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    paused: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notification_preferences",
    )


class UserPreferences(Base):
    """User preferences for feed personalization."""

    __tablename__ = "user_preferences"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Preference filters
    regions: Mapped[List[str]] = mapped_column(ARRAY(String), default=[])
    districts: Mapped[List[str]] = mapped_column(ARRAY(String), default=[])
    property_types: Mapped[List[str]] = mapped_column(ARRAY(String), default=[])
    listing_types: Mapped[List[str]] = mapped_column(ARRAY(String), default=[])
    price_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rooms: Mapped[List[int]] = mapped_column(ARRAY(Integer), default=[])

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_preferences",
    )


class Notification(Base):
    """In-app notification model for user notifications."""

    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Notification type and content
    type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Related entities (optional, depends on notification type)
    # No FK — notifications can reference listings from any source (main, telegram, olx)
    listing_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    comment_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    actor_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status
    read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Source of the notification ("saved_search" | "preferences" | other).
    # NULL for legacy rows created before this column existed.
    source: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
        foreign_keys=[user_id],
    )
    actor: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[actor_id],
    )
    comment: Mapped[Optional["Comment"]] = relationship("Comment")

    __table_args__ = (
        Index(
            "idx_notifications_user_unread",
            "user_id",
            "read",
            postgresql_where=(read.is_(False)),
        ),
    )


class ParserSource(Base):
    """Parser source configuration model (Ф-10, Section 24)."""

    __tablename__ = "parser_sources"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Source identification
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # telegram_channel, website
    identifier: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        nullable=False,
    )  # @channel_name or URL
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Configuration
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[str] = mapped_column(
        String(20),
        default="medium",
    )  # high, medium, low
    parse_interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Statistics
    total_parsed: Mapped[int] = mapped_column(Integer, default=0)
    total_errors: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_errors: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    last_parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ParserError(Base):
    """Parser error log model."""

    __tablename__ = "parser_errors"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    source_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parser_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    error_type: Mapped[str] = mapped_column(String(100), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )


class AuditLog(Base):
    """Audit log for tracking changes."""

    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # create, update, delete
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )


# =============================================================================
# Crawler Models
# =============================================================================


class TelegramListing(Base):
    """Telegram crawler listing model — stores raw data from Telegram channel monitor."""

    __tablename__ = "telegram_listings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Core listing fields
    property_type: Mapped[str] = mapped_column(String(50), nullable=False)
    listing_type: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)

    # Property details
    rooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    area_sqm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    floor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    building_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    condition: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    land_purpose: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Location
    region: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    district: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Content
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amenities: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # LLM extraction metadata
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Media
    images: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Source info
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_channel: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Multilingual content
    original_language: Mapped[str] = mapped_column(
        String(5), default="ru", server_default="ru"
    )
    description_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_uz: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address_ru: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    address_uz: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    translation_status: Mapped[Optional[str]] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    translated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Claim / conversion — links to the platform Listing created when a seller claims this Telegram listing
    converted_listing_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Rejection — seller explicitly marked this listing as "not mine"
    rejected_by_seller_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Deduplication
    signature_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )


class OLXListing(Base):
    """OLX crawler listing model — stores raw data from OLX.uz scraper."""

    __tablename__ = "olx_listings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # OLX identifiers
    olx_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Core listing fields
    property_type: Mapped[str] = mapped_column(String(50), nullable=False)
    listing_type: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)

    # Property details
    rooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    area_sqm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    floor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Location
    region: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    district: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True
    )
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Content
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    amenities: Mapped[Optional[list]] = mapped_column(ARRAY(String), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # LLM extraction metadata
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Media
    images: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # OLX source info
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="olx_uz")
    crawled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # OLX-specific fields
    seller_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    seller_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    views_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    posted_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    building_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    condition: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    land_purpose: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    furnishing: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ceiling_height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bathroom: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Raw data
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Multilingual content
    original_language: Mapped[str] = mapped_column(
        String(5), default="ru", server_default="ru"
    )
    description_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_uz: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address_ru: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    address_uz: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    translation_status: Mapped[Optional[str]] = mapped_column(
        String(20), default="pending", server_default="pending"
    )
    translated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Claim / conversion — links to the platform Listing created when a seller claims this OLX listing
    converted_listing_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Rejection — seller explicitly marked this listing as "not mine"
    rejected_by_seller_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Deduplication
    signature_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Table args: unique partial index ensures one-to-one mapping
    __table_args__ = (
        Index(
            "uq_olx_converted_listing",
            "converted_listing_id",
            unique=True,
            postgresql_where=(converted_listing_id.isnot(None)),
        ),
    )
