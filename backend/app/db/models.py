"""SQLAlchemy database models for Real Estate."""

import enum
from datetime import datetime, time
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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
    text,
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
    """Listing status enum.

    Block A V2.0 introduces three F1-related states:
    - ``PENDING_GENERATION`` — captured by parser, AI description not yet
      generated. Excluded from the B2C feed.
    - ``GENERATION_FAILED`` — F1 retried up to its max and still failed;
      shown in B2C with a base template description from structured params.
    - ``UNCONFIRMED`` — parser couldn't extract one of {deal_type, price,
      district}; visible to admin only, never shown in B2C, F1 not enqueued.
    """

    ACTIVE = "active"
    PAUSED = "paused"
    SOLD = "sold"
    DELETED = "deleted"
    EXPIRED = "expired"
    PENDING_GENERATION = "pending_generation"
    GENERATION_FAILED = "generation_failed"
    UNCONFIRMED = "unconfirmed"
    # Block F F1 — seller cabinet two-step publish flow.
    # Stage 1 commits Listing(status=DRAFT) with photos + params, fires
    # AI generation; Stage 2 flips to ACTIVE after seller approves text.
    DRAFT = "draft"


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
    # Block A V2.0 — A4. Push to a registered seller when a crawled
    # listing's phone matches theirs and F1 has produced an AI description.
    CRAWLED_MATCH = "crawled_match"


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
    seller_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    seller_telegram: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
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

    # Block D D3 — referral tracking. Written only on FIRST registration
    # when a /start ref_<id> payload was present; never retroactively.
    referred_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    referral_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # PR-T — Phase-2 referral program. Auto-generated lazily by the cabinet
    # endpoint (``services.referrals.ensure_referral_code``). UNIQUE via a
    # partial index that ignores NULLs so we never need to backfill.
    referral_code: Mapped[Optional[str]] = mapped_column(
        String(12), nullable=True, unique=True, index=False
    )

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

    # Block F V2.0 F4 — per-seller text-export overrides. Stored as
    # plain text and injected into rendered exports via the sandboxed
    # Jinja2 renderer (``services.text_export``). Signature/CTA give
    # the seller a place to brand the OLX/Telegram/Instagram bodies;
    # extra_hashtags appends to the platform-suggested set.
    export_signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    export_cta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    export_extra_hashtags: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )

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

    # Block D D4 — bot autoposting to seller's own channel.
    # When ``autopost_verified_at`` is NULL we treat the connection
    # as broken (bot kicked, channel gone, etc.) and surface a
    # reconnect prompt in the cabinet. ``autopost_channel_id`` is the
    # authoritative target — usernames can rotate.
    autopost_channel_username: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    autopost_channel_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    autopost_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    autopost_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    # Block D D4 — outcome of the most recent channel-publish attempt, surfaced
    # in the cabinet so sellers see *why* a post did/didn't appear without
    # reading worker logs. ``autopost_last_result`` is "ok" or a reason code;
    # ``autopost_last_result_at`` lets the UI flag a stuck worker (timestamp
    # not advancing after a save).
    autopost_last_result: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    autopost_last_result_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
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

    # ── PR-G: Optional FK to the landmark catalog. Coexists with the
    # free-text `landmark` column (dual-column, mirrors jk_id / jk_name).
    landmark_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("landmarks.id", ondelete="SET NULL"),
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
    # F1 (Block F) AI-generated descriptions per locale. Populated by the
    # AI generation Celery task after parser import. Never set by parser.
    ai_description_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_description_uz: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_description_uz_cyrl: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    ai_generation_attempted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    # Block F F1 — snapshot of {type, district, price, area, rooms} at
    # generation time. Cabinet Stage 2 compares to current params and
    # offers a "regenerate" banner when key params drifted.
    last_ai_param_snapshot: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )
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
    # Block phase-2 — promotions + banners. Urgent badge window + notify-
    # priority window (saved-search delivery looks at this).
    has_urgent_badge: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false"
    )
    urgent_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notify_priority_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Optimistic locking
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Block D D4 — per-listing opt-out of channel autopost. Manual listings
    # default to publishing; claimed / parsed imports default to FALSE
    # (migration backfill + claim handlers) so imported content is never
    # pushed to the seller's channel without an explicit choice.
    publish_to_channel: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

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

    # Block phase-2 — sale snapshot mirror (truth lives in ListingSale).
    # Populated by PATCH /listings/{id} when status flips to SOLD; nulled
    # on revert. Kept on the listing row so feed-side filters ("sold for
    # under X in the last 30 days") avoid a JOIN.
    sold_price: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sold_currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

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
    `Listing.jk_name` from Sprint 3 (T-001); FK is optional.

    Extended (PR-G) into a geo-aware reference catalog: multilingual names,
    a `microdistrict` pin and WGS-84 coordinates, plus `osm_id`/`source`
    provenance so the OSM seed and the listing-name dedup stay idempotent.
    """

    __tablename__ = "housing_complexes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # Localized names (i18n parity with the microdistrict registry). `name`
    # stays the canonical/display value (usually ru); the Uzbek variants are
    # optional and may be machine-transliterated for OSM-sourced rows.
    name_uz_latn: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    name_uz_cyrl: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    developer_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="SET NULL"),
        nullable=True,
    )
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    microdistrict: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # WGS-84 point — enables map pins + nearest-microdistrict assignment.
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Provenance: OSM element id ('way/123') for idempotent re-seeding, and
    # the data source ('osm' | 'listing' | 'manual').
    osm_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="osm"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Landmark(Base):
    """PR-G — Landmark reference catalog (markets, malls, universities,
    parks, stations, …) used as an optional address hint on a listing.

    Mirrors the HousingComplex shape: a flat row pinned to a `district` key
    from REGIONS, with multilingual names and a WGS-84 point. Seeded from
    OpenStreetMap (Overpass). The listing keeps a free-text `landmark`
    column plus an optional `landmark_id` FK — the same dual-column pattern
    as jk_name / jk_id, so a seller can pick a known landmark or type a
    free-text one."""

    __tablename__ = "landmarks"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_uz_latn: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    name_uz_cyrl: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Coarse type: 'market' | 'mall' | 'university' | 'park' | 'station' | …
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    microdistrict: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    osm_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="osm"
    )
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


class ListingViewEvent(Base):
    """Per-user listing-engagement events.

    Personalisation history (Phase 1 of F077). Each authenticated, non-self
    open / contact / share against a listing produces a row. Anonymous
    traffic does not write here — the public ``Listing.views_count``
    counter handles that population separately. Aggregate dashboard
    reads use the cached counters on Listing; this table is purely the
    canonical event log.
    """

    __tablename__ = "listing_view_event"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    # A5 V2.0 — anonymous-viewer dedup. Cookie-based id (24h TTL). Mutually
    # exclusive with user_id at write-time: anonymous rows have user_id=NULL
    # and anon_id set; authenticated rows have user_id set and anon_id NULL.
    anon_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    listing_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    viewed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    dwell_ms: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    __table_args__ = (
        Index(
            "idx_listing_view_event_user_time",
            "user_id",
            "viewed_at",
            postgresql_where=(user_id.is_not(None)),
        ),
        Index(
            "idx_listing_view_event_listing_type_time",
            "listing_id",
            "event_type",
            "viewed_at",
        ),
        # Dedup index built via raw SQL in the migration (functional index
        # on date(viewed_at) plus partial WHERE user_id IS NOT NULL).
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

    # Block A V2.0 — A4: optional auto-expiry. Used by the daily beat job
    # ``crawled_match.expire_old_notifications`` to flip a 7-day-old
    # crawled-match Telegram message into a "see Found" footer.
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

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


class SourceMetric(Base):
    """Daily extraction metric per parser source (Block A V2.0 — A8).

    One row per (source × day). Crawler writes counters at end-of-day or
    on-the-fly via ``POST /admin/sources/{id}/metrics``. The admin
    sources dashboard aggregates the last 7 days for each source.
    """

    __tablename__ = "source_metric"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    source_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("parser_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Calendar day in Asia/Tashkent. Stored as a date.
    day: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    listings_found: Mapped[int] = mapped_column(Integer, default=0)
    listings_extracted: Mapped[int] = mapped_column(Integer, default=0)
    listings_failed: Mapped[int] = mapped_column(Integer, default=0)
    dupes_filtered: Mapped[int] = mapped_column(Integer, default=0)
    # F1-related: how many listings failed AI generation today.
    ai_failed: Mapped[int] = mapped_column(Integer, default=0)
    # A4 — how many listings produced a CRAWLED_MATCH push notification today.
    notified: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "uq_source_metric_day",
            "source_id",
            "day",
            unique=True,
        ),
    )


# =============================================================================
# Block C V2.0 — Multi-phone identity (C4)
# =============================================================================
#
# Contract per decision-pass / PHONE_IDENTITY_MODEL.md:
# - User.phone stays the auth primary (UNIQUE-indexed since initial schema).
# - user_phones.phone is globally UNIQUE; one phone, one owner.
# - exactly one is_primary=true row per user (partial UNIQUE index).
# - User.phone == user_phones.phone WHERE is_primary=true (app-layer invariant).
# - Listing.phone MUST be one of seller's verified phones (app-layer check).
# - delete a phone → resolve listings first via 3-option modal.


class UserPhone(Base):
    """A verified phone attached to a user (Block C V2.0 — C4).

    Primary phone (is_primary=true) mirrors User.phone for auth
    compatibility. Additional phones (is_primary=false) carry the
    same E.164 format and unique constraint.
    """

    __tablename__ = "user_phones"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # 'tg_otp' | 'sms_otp' | 'legacy' (backfilled from User.phone)
    verification_method: Mapped[str] = mapped_column(
        String(16), nullable=False
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class PhoneVerifyAttempt(Base):
    """Phone-verify attempt log (forward-compat for C5 detection).

    C4 writes one row per request_otp + verify_otp call. C5 reads to
    flag suspicious patterns (one phone tried by many users in a
    24h window).
    """

    __tablename__ = "phone_verify_attempt"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    succeeded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )


# =============================================================================
# Block C V2.0 — Wallet / Transaction / Subscription (C3)
# =============================================================================
#
# Contract per decision-pass / WALLET_LIFECYCLE.md:
# - All money values are BIGINT in smallest currency unit. UZS=whole, USD=cents.
# - Lazy wallet creation (one wallet per user; INSERT … ON CONFLICT DO NOTHING).
# - Single-currency wallets (UZS in MVP); multi-currency deferred.
# - Idempotency-key UNIQUE on transactions; webhook re-delivery is no-op.
# - SELECT FOR UPDATE on wallet rows during withdraw/deposit.
# - AuditLog row written for every state change (same DB transaction).
# - No production callers during test period — services exist with tests.


class TransactionType(str, enum.Enum):
    """Transaction kind. ``adjustment`` is admin-driven."""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"


class TransactionStatus(str, enum.Enum):
    """Transaction state machine.

    Allowed transitions per WALLET_LIFECYCLE §9:
      pending → completed | failed
      completed → refunded
      failed, refunded are terminal.
    """

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class SubscriptionType(str, enum.Enum):
    """Subscription kind."""

    CABINET = "cabinet"
    LISTING_EXTRA = "listing_extra"


class SubscriptionStatus(str, enum.Enum):
    """Subscription state."""

    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    GRACE = "grace"  # missed renewal; in grace period before pause


class BillingCycle(str, enum.Enum):
    """Billing cycle for a subscription."""

    MONTHLY = "monthly"
    YEARLY = "yearly"


class Wallet(Base):
    """Per-user wallet (Block C — C3).

    One wallet per user; lazy-created by service layer. UZS-only in MVP.
    Currency stays as a column for forward-compat; service rejects non-UZS.
    """

    __tablename__ = "wallets"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # BIGINT in smallest currency unit (UZS=whole, USD=cents). See
    # decision-pass / MONEY_STORAGE_DECISION.md.
    current_balance: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Smallest currency unit. UZS: whole UZS. USD: cents.",
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency),
        nullable=False,
        default=Currency.UZS,
    )
    # Optimistic-lock counter. Incremented on every balance update by the
    # withdraw/deposit service alongside SELECT FOR UPDATE; provides a
    # secondary guard against lost-update bugs in code paths that bypass
    # the lock.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Transaction(Base):
    """Money-movement ledger entry (Block C — C3).

    Append-mostly: only ``status``, ``completed_at``, and ``metadata``
    can mutate after creation. State machine in WALLET_LIFECYCLE §9.
    """

    __tablename__ = "transactions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    wallet_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Smallest currency unit. Always > 0.",
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency), nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(
            TransactionStatus,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=TransactionStatus.PENDING,
    )
    # External reference (Click/Payme transaction id). Optional for
    # adjustment / internal transactions. Indexed for webhook lookup.
    external_payment_id: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, index=True
    )
    # Optional link to the subscription this transaction is paying for.
    # Adjustment transactions leave this NULL.
    subscription_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Idempotency: same key → same outcome. Webhook re-delivery is a
    # no-op via the unique constraint.
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    # JSONB for context: refund_of, discount_id, admin reason, etc.
    transaction_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    __table_args__ = (
        Index("idx_tx_wallet_status", "wallet_id", "status"),
    )


class Subscription(Base):
    """Recurring billing entry (Block C — C3).

    Two types in MVP: ``cabinet`` (one per user) and ``listing_extra``
    (one per paid listing). Polymorphic ``object_id`` typed by ``type``;
    no FK constraint per decision-pass §3.
    """

    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[SubscriptionType] = mapped_column(
        Enum(
            SubscriptionType,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    # When type=listing_extra, this references listings.id (no FK
    # constraint to allow Listing soft-deletes without cascade pain).
    # When type=cabinet, this is NULL.
    object_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    price: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="Smallest currency unit per billing cycle.",
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency), nullable=False, default=Currency.UZS
    )
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=BillingCycle.MONTHLY,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(
            SubscriptionStatus,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    next_billing_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_sub_user_type", "user_id", "type"),
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


# =============================================================================
# Block D V2.0 (D3) — deep-link payload tables
# =============================================================================


class DeepLinkPayload(Base):
    """Short-id → JSON payload indirection for Telegram-bot deep links.

    Telegram's ``start_param`` is hard-capped at 64 chars. We can't encode
    a full filter state inline, so we store the payload server-side and
    pass the 12-char primary key in the URL. Rows never expire (Block D
    D3-Q4 — shareable links don't rot).

    ``kind`` discriminator keeps the table reusable for future payload
    types (e.g. campaign tracking blobs). MVP only emits ``kind='filter'``.
    """

    __tablename__ = "deep_link_payloads"

    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    used_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


class ClaimInvite(Base):
    """Single-use, expiring B2B onboarding tickets.

    Used for ``/start claim_<id>`` (pre-imported sellers needing to
    confirm crawled listings) and ``/start agent_<id>`` (sellers
    identified by Telegram channel rather than phone).

    Authoritative auth check: row presence + ``used_at IS NULL`` +
    ``expires_at > now()``. The payload value alone is never trusted —
    see security model in DECISION_MATRIX D3-Q2.
    """

    __tablename__ = "claim_invites"

    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # 'claim' | 'agent'
    pre_imported_user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel_username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    used_by_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class DeepLinkEvent(Base):
    """Append-only audit + analytics log of every deep-link entry.

    One row per ``/start <payload>`` or Mini-App ``startapp=<payload>``
    arrival, regardless of payload validity. Powers abuse analysis,
    marketing campaign attribution, and the per-prefix conversion
    funnel. ``outcome`` captures whether the payload was honored.
    """

    __tablename__ = "deep_link_events"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_new_user: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    outcome: Mapped[str] = mapped_column(
        String(24), nullable=False, default="open", server_default="open"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )


# =============================================================================
# Block D V2.0 (D2) — behavioral signals
# =============================================================================


class BehavioralSignal(Base):
    """Append-only personalization signal.

    Single source-of-truth table the recommender (Ф-77 / Ф-78) reads
    from. ``event_type`` is the verb the user performed (``fav_add``,
    ``fav_remove``, etc.); ``source`` is where it was performed
    (``push_inline``, ``in_app``, ``bot_search``, ``inline_mode``).

    Retention: 180 days raw. Pruning is an ops cron, not enforced by
    the model. See migration ``prm_behavioral_signals`` for details.

    Writes funnel through ``services.behavioral_signals.record_event``;
    no caller writes directly to keep the dedup + fail-soft semantics
    centralised.
    """

    __tablename__ = "behavioral_signals"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    # No FK on listing_id: listings can vanish; signals stay readable.
    listing_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


# =============================================================================
# Block D V2.0 (D4) — bot channel-post tracking
# =============================================================================


class BotChannelPost(Base):
    """One row per (listing, channel) the bot has published.

    Stores the Telegram ``message_id`` so we can later edit (price /
    SOLD overlay) or delete the post. ``last_listing_version``
    captures the listing version at publish time — when
    ``Listing.version > last_listing_version`` the cabinet shows a
    "post stale" badge inviting the seller to click "Update post".

    Lifecycle status values (no DB enum to allow forward-compat):
        live          — published, in sync (or stale, depending on version)
        sold_marker   — caption rewritten with "ПРОДАНО/СДАНО" overlay
        deleted       — message removed from channel; row kept for audit

    CASCADE on listing delete: when the seller hard-deletes a listing,
    the row goes with it. Retention strategy is therefore the same as
    the parent listing.
    """

    __tablename__ = "bot_channel_posts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
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
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    last_edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    last_listing_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="live", server_default="live"
    )

    __table_args__ = (
        Index(
            "uq_bot_channel_posts_listing_channel",
            "listing_id",
            "channel_id",
            unique=True,
        ),
        Index(
            "idx_bot_channel_posts_seller_status",
            "seller_id",
            "status",
        ),
    )


# =============================================================================
# Block F V2.0 (F1 + F5) — AI generation foundation
# =============================================================================


class PromptTemplate(Base):
    """Versioned LLM prompt stored in DB.

    The AI generation worker reads the active row at task start; admin
    activates a new version via single-statement atomic swap (the
    partial unique index ``uq_prompt_templates_active_per_kind``
    guarantees ≤1 active per ``kind``).

    Retention: indefinite. Old versions retained for rollback.
    """

    __tablename__ = "prompt_templates"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    model_hint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class AIGeneration(Base):
    """Append-only log of every LLM call (success + failure outcomes).

    Block F F5 — owned by ``services/prompt_registry.record_generation``.
    No caller writes directly. Retention 90 days, pruned by Celery beat
    task ``prune_ai_generations`` (PR-F5b).
    """

    __tablename__ = "ai_generations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    listing_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    prompt_template_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # USD cost in micros ($0.000001 units). BIGINT avoids float drift.
    cost_usd_micros: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    # triggered_by values: manual | auto_parser | param_change | manual_retry
    triggered_by: Mapped[str] = mapped_column(String(32), nullable=False)
    # outcome values: ok | fallback_template | timeout | rate_limit | invalid_response
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class AIGenerationFeedback(Base):
    """Seller-submitted "👎 не нравится" rows for AI text quality.

    Block F F5. Joins to ``ai_generations`` (FK SET NULL so feedback
    survives 90-day generation pruning). Retained indefinitely; volume
    is small (~5–10 rows/day peak).
    """

    __tablename__ = "ai_generation_feedback"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    generation_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_generations.id", ondelete="SET NULL"),
        nullable=True,
    )
    listing_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # category values: grammar | unnatural | factual | too_long | too_short | other
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    handled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


# =============================================================================
# Block F V2.0 F2 — synonym dictionary (rule-based text → param matcher)
# =============================================================================


class SynonymEntry(Base):
    """One (surface_form → parameter) mapping the synonym matcher loads.

    The matcher is a pure-Python keyword scanner over the seller's
    Stage-2 free-text editor — see ``services.synonym_matcher``. Curated
    operationally via the ``/admin/synonyms`` console.

    ``language`` accepts ``"ru" | "uz" | "uz_cyrl"`` (matches the rest
    of Block F's locale convention) and the wildcard ``"*"`` for
    surface forms that work across scripts (e.g. brand names).
    """

    __tablename__ = "synonym_entries"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    parameter_key: Mapped[str] = mapped_column(String(64), nullable=False)
    parameter_value: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    surface_form: Mapped[str] = mapped_column(String(128), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    polarity: Mapped[str] = mapped_column(
        String(8), nullable=False, server_default="positive"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


# =============================================================================
# Block F V2.0 F4 — export templates (Cabinet subscription deliverable)
# =============================================================================


class ExportTemplate(Base):
    """One per-platform, per-language text-export template.

    The partial unique index ``uq_export_template_active`` enforces ≤1
    active row per (platform, language); admins flip versions via a
    single ``UPDATE … SET is_active = (id = :new)`` atomic swap. Body
    is rendered via ``jinja2.sandbox.SandboxedEnvironment`` with an
    allowlisted placeholder set — see ``services.text_export``.
    """

    __tablename__ = "export_templates"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # "olx" | "telegram_channel" | "instagram"
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    template_body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# =============================================================================
# Block phase-2 — deal-status + analytics
# =============================================================================


class ListingSale(Base):
    """One immutable sale record per sold listing.

    Created when ``Listing.status`` transitions to ``SOLD`` via the
    seller cabinet's "Mark as sold" modal. The ``UNIQUE(listing_id)``
    constraint means the PATCH handler upserts in place if a row
    already exists (seller re-confirming sale price). The redundant
    mirror columns on ``listings`` (``sold_price`` / ``sold_currency``
    / ``sold_at``) are kept in sync by the same handler; this table
    remains the source of truth (carries ``notes`` and historical
    integrity even if the listing is later soft-deleted).

    Indexed by ``sold_at`` and ``(sold_currency, sold_at)`` so the
    admin analytics price-index endpoint can range-scan the recent
    window cheaply and split USD vs UZS without a full sort.
    """

    __tablename__ = "listing_sales"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    listing_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    sold_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sold_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    sold_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint("listing_id", name="uq_listing_sales_listing_id"),
        Index("ix_listing_sales_listing_id", "listing_id"),
        Index("ix_listing_sales_sold_at", "sold_at"),
        Index("ix_listing_sales_currency_sold_at", "sold_currency", "sold_at"),
    )


# =============================================================================
# Block phase-2 — promotions + banners
# =============================================================================


class Banner(Base):
    """Marketing banner shown on the buyer home page or inline.

    Placement values:
        ``home_top``       — single hero banner above the listing feed.
        ``home_inline``    — appended between feed cards on the home page.
        ``listing_inline`` — appears on the listing detail page.

    ``language = '*'`` matches any locale (fall-back row). Specific locales
    (``ru`` / ``uz`` / ``uz_cyrl``) are preferred — the API tries the exact
    locale first and falls back to ``*`` only when no row matches.

    ``impressions`` / ``clicks`` are best-effort counters bumped from the
    public read / click endpoints. The partial index
    ``ix_banners_active_placement_lang`` keeps the buyer-facing lookup
    cheap on a denormalised feed.
    """

    __tablename__ = "banners"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    placement: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    impressions: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    clicks: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


# =============================================================================
# Block phase-2 — CRM + suspicions
# =============================================================================
#
# Two related-but-independent feature areas land together in
# ``pru_crm_suspicions``:
#
# * CRM: ``SellerClient`` + ``SellerClientListing`` give every seller a
#   lightweight prospect tracker — name / phone / notes + a 6-stage
#   pipeline (new / contacted / viewing / negotiating / won / lost),
#   plus a join row that pins specific listings to each prospect for
#   the in-cabinet "send these three options to Aziz" workflow.
# * Suspicions: ``AccountSuspicion`` + ``AccountLink`` power the
#   nightly duplicate-account workflow. The daily Celery job runs
#   signal functions (``services.suspicions``) that emit one open
#   ``AccountSuspicion`` per offending pair; admin /admin/suspicions
#   either ``merged`` (writes an ``AccountLink``) or ``dismissed``
#   the row. ``AccountLink`` uses a normalised pair (a < b) so the
#   uniqueness constraint catches duplicates regardless of detection
#   order.


class SellerClient(Base):
    """One CRM prospect owned by a seller."""

    __tablename__ = "seller_clients"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    seller_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sellers.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Pipeline stage: 'new' | 'contacted' | 'viewing' | 'negotiating'
    # | 'won' | 'lost'. Kept as VARCHAR (not an enum) so future stages
    # can be added without an Alembic dance.
    pipeline_stage: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="new",
        server_default="new",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_seller_clients_seller_stage", "seller_id", "pipeline_stage"),
    )


class SellerClientListing(Base):
    """Join row: one (client, listing) attachment."""

    __tablename__ = "seller_client_listings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    client_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("seller_clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "client_id", "listing_id", name="uq_seller_client_listing_pair"
        ),
    )


class AccountSuspicion(Base):
    """Open / reviewed admin item flagging a possible duplicate account."""

    __tablename__ = "account_suspicion"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    primary_user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    # 'phone_collision' | 'similar_names' | …
    signal_kind: Mapped[str] = mapped_column(String(48), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # 'open' | 'reviewed' | 'dismissed' | 'merged'
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="open",
        server_default="open",
    )
    reviewed_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_account_suspicion_status_created",
            "status",
            text("created_at DESC"),
        ),
        Index("ix_account_suspicion_primary_user", "primary_user_id"),
    )


class AccountLink(Base):
    """Resolved relationship between two users (merge / cleared)."""

    __tablename__ = "account_link"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    # ``user_id_a < user_id_b`` is enforced by a CHECK constraint so
    # the (a, b) unique key catches duplicates regardless of the
    # detection order.
    user_id_a: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id_b: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 'duplicate' | 'related' | 'cleared'
    relation: Mapped[str] = mapped_column(String(32), nullable=False)
    decided_by: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id_a", "user_id_b", name="uq_account_link_pair"),
    )


# =============================================================================
# Block phase-2 — referral program
# =============================================================================
#
# Cabinet-side referral program (PR-T). The ``users.referral_code`` column
# is the share key the seller posts to social; events and rewards land in
# their own tables so attribution and payout history are queryable
# independent of the wallet ledger. See ``app/services/referrals.py``.


class ReferralEvent(Base):
    """One row per (referrer, referred, event_type) — attribution ledger.

    Append-only. The UNIQUE constraint on the triple is the idempotency
    fence: callers can blindly retry ``attribute_signup`` / ``maybe_qualify``
    and only the first wins. ``event_type`` is a free-text string but in
    practice one of ``signup`` | ``qualified`` | ``rewarded``.
    """

    __tablename__ = "referral_events"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    referrer_user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    referred_user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # JSONB context (source, qualifying-tx id, etc.). ``metadata`` is a
    # SQLAlchemy reserved name on the Declarative base, hence the rename.
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "referrer_user_id",
            "referred_user_id",
            "event_type",
            name="uq_referral_event_triple",
        ),
        Index(
            "idx_referral_events_referrer_created",
            "referrer_user_id",
            "created_at",
        ),
    )


class ReferralReward(Base):
    """Payout row mirrored against ``transactions`` when possible.

    ``wallet_tx_id`` is NULL when the wallet deposit path is unavailable
    (e.g. the deposit service is gated by a feature flag at the time the
    referrer qualifies). In that case the reward stands as a promise the
    admin can settle later — surfaced in the cabinet so the user sees
    "pending payout" rather than no signal at all.
    """

    __tablename__ = "referral_rewards"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    referrer_user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount_micros: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="UZS micros for parity with wallet primitives.",
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    wallet_tx_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "idx_referral_rewards_referrer_granted",
            "referrer_user_id",
            "granted_at",
        ),
    )


# =============================================================================
# Block D (FU3) — bot rate-limit settings (admin-managed)
# =============================================================================


class BotRateLimitSettings(Base):
    """Singleton config row backing the bot's per-user rate limiter.

    Block D / FU3. The two spammy bot surfaces — in-chat search (``/search`` +
    free text) and Inline Mode — are throttled per Telegram user. The numeric
    caps, on/off toggles and the "too many requests" message are admin-editable
    from the panel rather than baked into code, so ops can tune them without a
    deploy.

    Exactly one row exists, pinned to ``id = 1`` by a CHECK constraint. The bot
    reads this (through a short-lived Redis cache) on every search; the admin
    API is the only writer. The three message columns are seeded with defaults
    in all bot locales by the migration and are never blanked (the API enforces
    non-empty), so the bot always has text to show.
    """

    __tablename__ = "bot_rate_limit_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    # In-chat search ( /search + free text ).
    search_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    search_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("10")
    )
    search_window_sec: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("60")
    )

    # Inline Mode ( @bot <query> ).
    inline_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    inline_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("30")
    )
    inline_window_sec: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("60")
    )

    # "Too many requests" message — shown in chat and (as a single card) in
    # inline. Pre-seeded in all three bot locales; editable but not blankable.
    limit_message_ru: Mapped[str] = mapped_column(Text, nullable=False)
    limit_message_uz: Mapped[str] = mapped_column(Text, nullable=False)
    limit_message_uz_cyrl: Mapped[str] = mapped_column(Text, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by_admin_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_bot_rate_limit_singleton"),
    )
