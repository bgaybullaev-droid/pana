"""Listing schemas."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.regions import validate_region_district
from app.schemas.common import UTCDateTime


class ListingImageResponse(BaseModel):
    """Listing image response."""

    id: UUID
    original_url: str
    thumbnail_url: Optional[str] = None
    medium_url: Optional[str] = None
    large_url: Optional[str] = None
    position: int = 0
    is_primary: bool = False

    model_config = {"from_attributes": True}


class ListingBase(BaseModel):
    """Base listing schema."""

    type: str = Field(..., pattern="^(sell|rent)$")
    property_type: str = Field(..., pattern="^(apartment|house|commercial|land)$")
    rooms: Optional[int] = Field(None, ge=0, le=20)
    area: Optional[float] = Field(None, gt=0, le=1000000)  # Up to 1 million m²
    floor: Optional[int] = Field(None, ge=-5, le=100)
    total_floors: Optional[int] = Field(None, ge=1, le=100)
    region: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    price: int = Field(..., ge=0, le=100000000)
    currency: str = Field(default="USD", pattern="^(USD|UZS)$")
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    phone: Optional[str] = Field(None, max_length=20)  # Flexible phone validation
    # S3 (T-001) widened: developer joins owner|realtor.
    seller_type: Optional[str] = Field(None, pattern="^(owner|realtor|developer)$")

    # Phase 2 fields
    living_area: Optional[float] = Field(None, gt=0, le=1000000)
    kitchen_area: Optional[float] = Field(None, gt=0, le=1000000)
    land_area: Optional[float] = Field(None, gt=0, le=1000000)
    building_type: Optional[str] = Field(None, pattern="^(new|secondary)$")
    # S4 (T-007) widened: condition enum now matches DB CHECK.
    condition: Optional[str] = Field(
        None,
        pattern=(
            "^(shell|none|cosmetic|medium|euro|designer|"
            "turnkey|needs_repair_comm|needs_repair|rough)$"
        ),
    )
    house_type: Optional[str] = Field(None, max_length=50)
    house_condition: Optional[List[str]] = None
    location_type: Optional[List[str]] = None
    water_supply: Optional[List[str]] = None
    electricity: Optional[str] = Field(None, max_length=50)
    heating: Optional[List[str]] = None
    gas_supply: Optional[str] = Field(None, max_length=50)
    sewage: Optional[str] = Field(None, max_length=50)
    is_furnished: Optional[bool] = None
    is_negotiable: bool = False
    # S6 (T-013) widened: land_purpose now matches DB CHECK.
    land_purpose: Optional[str] = Field(
        None,
        pattern="^(construction|commercial_land|agricultural|garden|unspecified)$",
    )
    amenities: Optional[List[str]] = None
    nearby_amenities: Optional[List[str]] = None

    # ── Sprint 2: Rent fields (T-002, T-003) ────────────────────────
    rent_period: Optional[str] = Field(None, pattern="^(long_term|daily)$")
    deposit: Optional[int] = Field(None, ge=0)
    utilities_incl: Optional[bool] = None
    min_rent_months: Optional[int] = Field(None)
    allowed_students: Optional[bool] = None
    allowed_pets: Optional[bool] = None
    rent_payment: Optional[List[str]] = None

    # ── Sprint 2: Sale finance flags (T-004) ────────────────────────
    mortgage_ok: bool = False
    installment_ok: bool = False
    halol_ok: bool = False

    # ── Sprint 2: Deed type (T-005) ─────────────────────────────────
    deed_type: Optional[str] = Field(None, pattern="^(cadastre|order|other)$")

    # ── Sprint 3 (T-001) ────────────────────────────────────────────
    urgent_flag: bool = False
    city: Optional[str] = Field(None, max_length=100)
    microdistrict: Optional[str] = Field(None, max_length=200)
    jk_name: Optional[str] = Field(None, max_length=200)
    landmark: Optional[str] = Field(None, max_length=500)
    metro_station: Optional[str] = Field(None, max_length=50)
    seller_telegram: Optional[str] = Field(None, max_length=100)
    # seller_type widened: owner | realtor | developer
    # NOTE: this overrides the existing `seller_type` field defined above —
    # Pydantic uses the latest declaration. To avoid that confusion we
    # don't redeclare here; the API-layer dual-read accepts `developer`
    # via the broader pattern in ListingUpdate.

    # ── Sprint 4 (T-009) ────────────────────────────────────────────
    commercial_type: Optional[str] = Field(
        None, pattern="^(office|shop|warehouse|production|restaurant|hotel|other)$"
    )
    price_per_sqm: Optional[int] = Field(None, ge=0)
    ceiling_height: Optional[float] = Field(None, gt=0, le=30)
    entrance: Optional[str] = Field(None, pattern="^(separate|yard|street|mall)$")
    parking_comm: Optional[bool] = None
    building_class: Optional[str] = Field(
        None, pattern="^(standalone|embedded|business_center|mall)$"
    )

    # ── Sprint 5 (T-006, T-008) — dual-read window ──────────────────
    market_type: Optional[str] = Field(None, pattern="^(new|secondary)$")
    wall_material: Optional[str] = Field(
        None, pattern="^(brick|gasblock|panel|monolith|other)$"
    )
    furniture: Optional[str] = Field(None, pattern="^(none|partial|full|built_in)$")

    # ── Sprint 6 (T-011, T-014, T-015) ──────────────────────────────
    garage: Optional[bool] = None
    basement: Optional[bool] = None
    buildings_exist: Optional[bool] = None
    fence: Optional[bool] = None
    land_shape: Optional[str] = Field(None, pattern="^(rectangular|irregular)$")
    balcony: Optional[str] = Field(None, pattern="^(none|balcony|loggia|terrace)$")
    listing_subtype: Optional[str] = Field(
        None, pattern="^(standard|studio|free_plan)$"
    )
    floor_plan_url: Optional[str] = Field(None, max_length=500)

    # ── Sprint 7 (T-027) ────────────────────────────────────────────
    jk_id: Optional[UUID] = None

    # ── Sprint 8 (T-023) — slug is system-set; not accepted on input.
    # (No field here; ListingResponse mirrors it back.)

    @field_validator("floor")
    @classmethod
    def validate_floor(cls, v, info):
        """Validate floor is less than or equal to total_floors."""
        if v is not None and info.data.get("total_floors"):
            if v > info.data["total_floors"]:
                raise ValueError("Floor cannot be greater than total floors")
        return v

    @field_validator("min_rent_months")
    @classmethod
    def validate_min_rent_months(cls, v):
        """Enforce the enum {1, 3, 6, 12} per blueprint §1.2."""
        if v is not None and v not in (1, 3, 6, 12):
            raise ValueError("min_rent_months must be one of 1, 3, 6, 12")
        return v

    @field_validator("rent_payment")
    @classmethod
    def validate_rent_payment_elements(cls, v):
        """Reject invalid elements; de-duplicate preserving order.

        Postgres has no clean per-element CHECK on ARRAY columns; enforced
        here at the API boundary per blueprint §1.1.
        """
        if v is None:
            return v
        allowed = {"cash", "payme", "click", "bank"}
        bad = [e for e in v if e not in allowed]
        if bad:
            raise ValueError(
                f"rent_payment elements must be in {sorted(allowed)}; "
                f"got invalid: {bad}"
            )
        seen: set = set()
        out: List[str] = []
        for e in v:
            if e not in seen:
                out.append(e)
                seen.add(e)
        return out

    @model_validator(mode="after")
    def validate_location(self):
        """Validate that district belongs to selected region."""
        if not validate_region_district(self.region, self.district):
            raise ValueError("District does not belong to the selected region")
        return self


class ListingImageCreate(BaseModel):
    """Schema for creating a listing image."""

    original_url: str = Field(..., max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    medium_url: Optional[str] = Field(None, max_length=500)
    large_url: Optional[str] = Field(None, max_length=500)
    position: int = Field(default=0, ge=0)
    is_primary: bool = False


class ListingCreate(ListingBase):
    """Schema for creating a listing."""

    images: List[ListingImageCreate] = Field(..., min_length=1, max_length=10)


class ListingUpdate(BaseModel):
    """Schema for updating a listing."""

    type: Optional[str] = Field(None, pattern="^(sell|rent)$")
    property_type: Optional[str] = Field(
        None, pattern="^(apartment|house|commercial|land)$"
    )
    rooms: Optional[int] = Field(None, ge=0, le=20)
    area: Optional[float] = Field(None, gt=0, le=1000000)  # Up to 1 million m²
    floor: Optional[int] = Field(None, ge=-5, le=100)
    total_floors: Optional[int] = Field(None, ge=1, le=100)
    region: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    price: Optional[int] = Field(None, gt=0, le=100000000)
    currency: Optional[str] = Field(None, pattern="^(USD|UZS)$")
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    phone: Optional[str] = Field(None, max_length=20)  # Flexible phone validation
    # S3 (T-001) widened to match ListingBase.
    seller_type: Optional[str] = Field(None, pattern="^(owner|realtor|developer)$")
    status: Optional[str] = Field(None, pattern="^(active|paused|sold)$")
    images: Optional[List[ListingImageCreate]] = Field(default=None, max_length=10)

    # Phase 2 fields
    living_area: Optional[float] = Field(None, gt=0, le=1000000)
    kitchen_area: Optional[float] = Field(None, gt=0, le=1000000)
    land_area: Optional[float] = Field(None, gt=0, le=1000000)
    building_type: Optional[str] = Field(None, pattern="^(new|secondary)$")
    # S4 (T-007) widened to match ListingBase + DB CHECK.
    condition: Optional[str] = Field(
        None,
        pattern=(
            "^(shell|none|cosmetic|medium|euro|designer|"
            "turnkey|needs_repair_comm|needs_repair|rough)$"
        ),
    )
    house_type: Optional[str] = Field(None, max_length=50)
    house_condition: Optional[List[str]] = None
    location_type: Optional[List[str]] = None
    water_supply: Optional[List[str]] = None
    electricity: Optional[str] = Field(None, max_length=50)
    heating: Optional[List[str]] = None
    gas_supply: Optional[str] = Field(None, max_length=50)
    sewage: Optional[str] = Field(None, max_length=50)
    is_furnished: Optional[bool] = None
    is_negotiable: Optional[bool] = None
    # S6 (T-013) widened to match ListingBase + DB CHECK.
    land_purpose: Optional[str] = Field(
        None,
        pattern="^(construction|commercial_land|agricultural|garden|unspecified)$",
    )
    amenities: Optional[List[str]] = None
    nearby_amenities: Optional[List[str]] = None

    # ── Sprint 2: Rent + sale finance + deed ────────────────────────
    rent_period: Optional[str] = Field(None, pattern="^(long_term|daily)$")
    deposit: Optional[int] = Field(None, ge=0)
    utilities_incl: Optional[bool] = None
    min_rent_months: Optional[int] = Field(None)
    allowed_students: Optional[bool] = None
    allowed_pets: Optional[bool] = None
    rent_payment: Optional[List[str]] = None
    mortgage_ok: Optional[bool] = None
    installment_ok: Optional[bool] = None
    halol_ok: Optional[bool] = None
    deed_type: Optional[str] = Field(None, pattern="^(cadastre|order|other)$")

    # ── Sprint 3-7 Update mirror ────────────────────────────────────
    urgent_flag: Optional[bool] = None
    city: Optional[str] = Field(None, max_length=100)
    microdistrict: Optional[str] = Field(None, max_length=200)
    jk_name: Optional[str] = Field(None, max_length=200)
    landmark: Optional[str] = Field(None, max_length=500)
    metro_station: Optional[str] = Field(None, max_length=50)
    seller_telegram: Optional[str] = Field(None, max_length=100)
    commercial_type: Optional[str] = Field(
        None, pattern="^(office|shop|warehouse|production|restaurant|hotel|other)$"
    )
    price_per_sqm: Optional[int] = Field(None, ge=0)
    ceiling_height: Optional[float] = Field(None, gt=0, le=30)
    entrance: Optional[str] = Field(None, pattern="^(separate|yard|street|mall)$")
    parking_comm: Optional[bool] = None
    building_class: Optional[str] = Field(
        None, pattern="^(standalone|embedded|business_center|mall)$"
    )
    market_type: Optional[str] = Field(None, pattern="^(new|secondary)$")
    wall_material: Optional[str] = Field(
        None, pattern="^(brick|gasblock|panel|monolith|other)$"
    )
    furniture: Optional[str] = Field(None, pattern="^(none|partial|full|built_in)$")
    garage: Optional[bool] = None
    basement: Optional[bool] = None
    buildings_exist: Optional[bool] = None
    fence: Optional[bool] = None
    land_shape: Optional[str] = Field(None, pattern="^(rectangular|irregular)$")
    balcony: Optional[str] = Field(None, pattern="^(none|balcony|loggia|terrace)$")
    listing_subtype: Optional[str] = Field(
        None, pattern="^(standard|studio|free_plan)$"
    )
    floor_plan_url: Optional[str] = Field(None, max_length=500)
    jk_id: Optional[UUID] = None

    # ── Block phase-2 — sale capture (only honored when status=sold) ─
    sold_price: Optional[int] = Field(None, gt=0, le=10**12)
    sold_currency: Optional[str] = Field(None, pattern="^(USD|UZS)$")
    sold_notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("min_rent_months")
    @classmethod
    def validate_min_rent_months(cls, v):
        if v is not None and v not in (1, 3, 6, 12):
            raise ValueError("min_rent_months must be one of 1, 3, 6, 12")
        return v

    @field_validator("rent_payment")
    @classmethod
    def validate_rent_payment_elements(cls, v):
        if v is None:
            return v
        allowed = {"cash", "payme", "click", "bank"}
        bad = [e for e in v if e not in allowed]
        if bad:
            raise ValueError(
                f"rent_payment elements must be in {sorted(allowed)}; "
                f"got invalid: {bad}"
            )
        seen: set = set()
        out: List[str] = []
        for e in v:
            if e not in seen:
                out.append(e)
                seen.add(e)
        return out

    @model_validator(mode="after")
    def validate_location(self):
        """Validate that district belongs to selected region."""
        if not validate_region_district(self.region, self.district):
            raise ValueError("District does not belong to the selected region")
        return self


class ListingResponse(BaseModel):
    """Full listing response."""

    id: UUID
    seller_id: Optional[UUID] = None
    type: str
    property_type: str
    rooms: Optional[int] = None
    area: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    region: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price: int
    currency: str
    title: Optional[str] = None
    description: Optional[str] = None
    phone: Optional[str] = None
    seller_type: Optional[str] = None

    # Phase 2 fields
    living_area: Optional[float] = None
    kitchen_area: Optional[float] = None
    land_area: Optional[float] = None
    building_type: Optional[str] = None
    condition: Optional[str] = None
    house_type: Optional[str] = None
    house_condition: Optional[List[str]] = None
    location_type: Optional[List[str]] = None
    water_supply: Optional[List[str]] = None
    electricity: Optional[str] = None
    heating: Optional[List[str]] = None
    gas_supply: Optional[str] = None
    sewage: Optional[str] = None
    is_furnished: Optional[bool] = None
    is_negotiable: bool = False
    land_purpose: Optional[str] = None
    amenities: Optional[List[str]] = None
    nearby_amenities: Optional[List[str]] = None

    # ── Sprint 2: Rent + sale finance + deed (matrix-gated on write) ──
    rent_period: Optional[str] = None
    deposit: Optional[int] = None
    utilities_incl: Optional[bool] = None
    min_rent_months: Optional[int] = None
    allowed_students: Optional[bool] = None
    allowed_pets: Optional[bool] = None
    rent_payment: Optional[List[str]] = None
    mortgage_ok: bool = False
    installment_ok: bool = False
    halol_ok: bool = False
    deed_type: Optional[str] = None

    # ── Sprint 3-8 Response mirror ──────────────────────────────────
    urgent_flag: Optional[bool] = None
    city: Optional[str] = None
    microdistrict: Optional[str] = None
    jk_name: Optional[str] = None
    landmark: Optional[str] = None
    metro_station: Optional[str] = None
    seller_telegram: Optional[str] = None
    commercial_type: Optional[str] = None
    price_per_sqm: Optional[int] = None
    ceiling_height: Optional[float] = None
    entrance: Optional[str] = None
    parking_comm: Optional[bool] = None
    building_class: Optional[str] = None
    market_type: Optional[str] = None
    wall_material: Optional[str] = None
    furniture: Optional[str] = None
    garage: Optional[bool] = None
    basement: Optional[bool] = None
    buildings_exist: Optional[bool] = None
    fence: Optional[bool] = None
    land_shape: Optional[str] = None
    balcony: Optional[str] = None
    listing_subtype: Optional[str] = None
    floor_plan_url: Optional[str] = None
    jk_id: Optional[UUID] = None
    slug: Optional[str] = None

    source_type: str
    status: str
    moderation_status: str
    views_count: int = 0
    contacts_count: int = 0
    favorites_count: int = 0
    comments_count: int = 0
    is_boosted: bool = False
    boost_until: Optional[UTCDateTime] = None
    is_highlighted: bool = False
    created_at: UTCDateTime
    updated_at: Optional[UTCDateTime] = None
    expires_at: Optional[UTCDateTime] = None
    images: List[ListingImageResponse] = []

    # Computed fields
    is_favorited: bool = False

    # Multilingual metadata
    original_language: Optional[str] = None
    is_translated: bool = False

    # ── Block F V2.0 (F1) — AI description per locale ───────────────
    # Buyer feed / detail responses expose all three locales; the
    # frontend picks the active one based on the user's UI language.
    ai_description_ru: Optional[str] = None
    ai_description_uz: Optional[str] = None
    ai_description_uz_cyrl: Optional[str] = None

    model_config = {"from_attributes": True}


class ListingListResponse(BaseModel):
    """Listing list item response (lighter than full response)."""

    id: UUID
    type: str
    property_type: str
    rooms: Optional[int]
    area: Optional[float]
    floor: Optional[int]
    total_floors: Optional[int]
    region: Optional[str] = None
    district: Optional[str]
    price: int
    currency: str
    title: Optional[str]
    description: Optional[str] = None  # short snippet for card preview
    views_count: int
    favorites_count: int
    comments_count: int = 0
    is_boosted: bool
    is_highlighted: bool
    created_at: UTCDateTime
    primary_image_url: Optional[str] = None
    is_favorited: bool = False

    # ── Sprint 2: Fields for card variants + badge rendering ────────
    rent_period: Optional[str] = None
    land_area: Optional[float] = None
    mortgage_ok: bool = False
    installment_ok: bool = False
    halol_ok: bool = False
    urgent_flag: Optional[bool] = None
    is_verified: Optional[bool] = None  # seller.is_verified (joined)

    model_config = {"from_attributes": True}


class SellerListingListResponse(ListingListResponse):
    """Seller's listing list item response (includes status and contacts_count)."""

    status: str
    contacts_count: int = 0
    source_type: Optional[str] = None


class ListingFilters(BaseModel):
    """Listing filter parameters."""

    q: Optional[str] = Field(None, max_length=200, description="Search query")
    type: Optional[str] = Field(None, pattern="^(sell|rent)$")
    property_type: Optional[str] = Field(
        None, pattern="^(apartment|house|commercial|land)$"
    )
    rooms: Optional[List[int]] = Field(None, description="List of room counts")
    price_min: Optional[int] = Field(None, ge=0)
    price_max: Optional[int] = Field(None, le=100000000)
    area_min: Optional[float] = Field(None, ge=0)
    area_max: Optional[float] = Field(None, le=100000)
    floor_min: Optional[int] = Field(None, ge=-5)
    floor_max: Optional[int] = Field(None, le=100)
    region: Optional[List[str]] = None
    district: Optional[List[str]] = None
    seller_id: Optional[UUID] = None
    source_type: Optional[str] = Field(None, pattern="^(manual|claimed|parsed)$")

    # ── Sprint 2: Land area range ───────────────────────────────────
    land_area_min: Optional[float] = Field(None, ge=0)
    land_area_max: Optional[float] = Field(None, le=100000)

    # ── Sprint 2: Rent filters (silently dropped when type=sell) ────
    rent_period: Optional[str] = Field(None, pattern="^(long_term|daily)$")
    utilities_incl: Optional[bool] = None
    min_rent_months: Optional[List[int]] = None
    allowed_students: Optional[bool] = None
    allowed_pets: Optional[bool] = None
    rent_payment: Optional[List[str]] = None
    deposit_min: Optional[int] = Field(None, ge=0)
    deposit_max: Optional[int] = Field(None, ge=0)

    # ── Sprint 2: Sale finance + deed (silently dropped when type=rent) ──
    mortgage_ok: Optional[bool] = None
    installment_ok: Optional[bool] = None
    halol_ok: Optional[bool] = None
    deed_type: Optional[str] = Field(None, pattern="^(cadastre|order|other)$")

    # ── Sprint 2: Already-shipped fields exposed as filters ─────────
    condition: Optional[List[str]] = None
    building_type: Optional[str] = Field(None, pattern="^(new|secondary)$")
    furnished: Optional[bool] = None  # maps to is_furnished column
    amenities: Optional[List[str]] = None  # AND-match (listing must contain all)
    nearby_amenities: Optional[List[str]] = None  # AND-match

    # ── A2 — house-specific filters (columns shipped in Phase 2) ────
    # `house_type` is a scalar string; the other two are ARRAY(String)
    # columns and use the array-overlap pattern (matches the listing
    # if it contains ANY of the selected options).
    house_type: Optional[str] = Field(None, max_length=50)
    house_condition: Optional[List[str]] = None  # ARRAY overlap
    water_supply: Optional[List[str]] = None  # ARRAY overlap

    # ── Sprint 3 (T-001) filters ────────────────────────────────────
    urgent_flag: Optional[bool] = None  # true-only (mirrors sale-finance booleans)
    city: Optional[str] = Field(None, max_length=100)
    microdistrict: Optional[str] = Field(None, max_length=200)
    jk_name: Optional[str] = Field(None, max_length=200)
    metro_station: Optional[str] = Field(None, max_length=50)

    # ── Sprint 4 (T-009) filters ────────────────────────────────────
    commercial_type: Optional[str] = Field(
        None, pattern="^(office|shop|warehouse|production|restaurant|hotel|other)$"
    )
    building_class: Optional[str] = Field(
        None, pattern="^(standalone|embedded|business_center|mall)$"
    )
    entrance: Optional[str] = Field(None, pattern="^(separate|yard|street|mall)$")
    parking_comm: Optional[bool] = None
    ceiling_height_min: Optional[float] = Field(None, gt=0, le=30)
    ceiling_height_max: Optional[float] = Field(None, gt=0, le=30)
    price_per_sqm_min: Optional[int] = Field(None, ge=0)
    price_per_sqm_max: Optional[int] = Field(None, ge=0)

    # ── Sprint 5 (T-006, T-008) filters — dual-read window ──────────
    # market_type is the new name for building_type. wall_material and
    # furniture are new columns with no legacy alias.
    market_type: Optional[str] = Field(None, pattern="^(new|secondary)$")
    wall_material: Optional[str] = Field(
        None, pattern="^(brick|gasblock|panel|monolith|other)$"
    )
    furniture: Optional[str] = Field(None, pattern="^(none|partial|full|built_in)$")

    # ── Sprint 6 (T-011, T-014, T-015) filters ──────────────────────
    garage: Optional[bool] = None
    basement: Optional[bool] = None
    buildings_exist: Optional[bool] = None
    fence: Optional[bool] = None
    land_shape: Optional[str] = Field(None, pattern="^(rectangular|irregular)$")
    balcony: Optional[str] = Field(None, pattern="^(none|balcony|loggia|terrace)$")
    listing_subtype: Optional[str] = Field(
        None, pattern="^(standard|studio|free_plan)$"
    )

    # ── Sprint 7 (T-027) filters ────────────────────────────────────
    jk_id: Optional[UUID] = None

    sort_by: str = Field(
        default="created_at", pattern="^(created_at|price|area|views_count)$"
    )
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")

    @field_validator("price_min")
    @classmethod
    def validate_price_range(cls, v, info):
        """Validate price_min is less than price_max."""
        if v is not None and info.data.get("price_max"):
            if v > info.data["price_max"]:
                raise ValueError("price_min cannot be greater than price_max")
        return v

    @field_validator("deposit_min")
    @classmethod
    def validate_deposit_range(cls, v, info):
        if v is not None and info.data.get("deposit_max") is not None:
            if v > info.data["deposit_max"]:
                raise ValueError("deposit_min cannot be greater than deposit_max")
        return v

    @field_validator("land_area_min")
    @classmethod
    def validate_land_area_range(cls, v, info):
        if v is not None and info.data.get("land_area_max") is not None:
            if v > info.data["land_area_max"]:
                raise ValueError("land_area_min cannot be greater than land_area_max")
        return v

    @field_validator("ceiling_height_min")
    @classmethod
    def validate_ceiling_height_range(cls, v, info):
        if v is not None and info.data.get("ceiling_height_max") is not None:
            if v > info.data["ceiling_height_max"]:
                raise ValueError(
                    "ceiling_height_min cannot be greater than ceiling_height_max"
                )
        return v

    @field_validator("price_per_sqm_min")
    @classmethod
    def validate_price_per_sqm_range(cls, v, info):
        if v is not None and info.data.get("price_per_sqm_max") is not None:
            if v > info.data["price_per_sqm_max"]:
                raise ValueError(
                    "price_per_sqm_min cannot be greater than price_per_sqm_max"
                )
        return v

    @field_validator("min_rent_months")
    @classmethod
    def validate_min_rent_months_filter(cls, v):
        if v is None:
            return v
        bad = [m for m in v if m not in (1, 3, 6, 12)]
        if bad:
            raise ValueError(
                f"min_rent_months elements must be in (1, 3, 6, 12); got {bad}"
            )
        return v

    @field_validator("rent_payment")
    @classmethod
    def validate_rent_payment_filter(cls, v):
        if v is None:
            return v
        allowed = {"cash", "payme", "click", "bank"}
        bad = [e for e in v if e not in allowed]
        if bad:
            raise ValueError(
                f"rent_payment elements must be in {sorted(allowed)}; got {bad}"
            )
        return v

    @field_validator("condition")
    @classmethod
    def validate_condition_filter(cls, v):
        if v is None:
            return v
        # S4 (T-007) widened set — matches DB CHECK + ListingBase pattern.
        allowed = {
            "shell",
            "none",
            "cosmetic",
            "medium",
            "euro",
            "designer",
            "turnkey",
            "needs_repair_comm",
            "needs_repair",
            "rough",
        }
        bad = [c for c in v if c not in allowed]
        if bad:
            raise ValueError(
                f"condition elements must be in {sorted(allowed)}; got {bad}"
            )
        return v


class FacetBucket(BaseModel):
    """Single (value, count) bucket in a facet response."""

    value: object  # scalar: str | int | bool — serialized to JSON as-is
    count: int


class FacetsResponse(BaseModel):
    """T-019 facets response.

    Keys are the facet dimensions advertised by the backend. Non-applicable
    facets for the caller's (property_type, type) combo are omitted entirely.
    Empty facets are also omitted (no key returned rather than an empty list).
    """

    deal_type: Optional[List[FacetBucket]] = None
    property_type: Optional[List[FacetBucket]] = None
    region: Optional[List[FacetBucket]] = None
    district: Optional[List[FacetBucket]] = None
    rooms: Optional[List[FacetBucket]] = None
    rent_period: Optional[List[FacetBucket]] = None
    rent_payment: Optional[List[FacetBucket]] = None
    mortgage_ok: Optional[List[FacetBucket]] = None
    installment_ok: Optional[List[FacetBucket]] = None
    halol_ok: Optional[List[FacetBucket]] = None
    # ── Sprint 3–5 facet additions ──────────────────────────────────
    urgent_flag: Optional[List[FacetBucket]] = None
    commercial_type: Optional[List[FacetBucket]] = None
    building_class: Optional[List[FacetBucket]] = None
    market_type: Optional[List[FacetBucket]] = None
    furniture: Optional[List[FacetBucket]] = None

    # Route declares response_model_exclude_none=True so omitted facets
    # disappear from the JSON payload (instead of serializing as null).


class ListingClaimRequest(BaseModel):
    """Request to claim a parsed listing."""

    listing_id: UUID


class ListingClaimVerifyRequest(BaseModel):
    """Request to verify claim with OTP."""

    otp_code: str = Field(..., min_length=6, max_length=6)


# =============================================================================
# Block F V2.0 (F1) — DRAFT two-step publish schemas
# =============================================================================


class DraftPreviewResponse(BaseModel):
    """``GET /listings/{id}/draft-preview`` response payload.

    The frontend Stage 2 polls this until ``ai_description_ru`` is non-null
    (max 30s @ 2s interval). The ``last_ai_param_snapshot`` lets the
    frontend detect param drift between Stage 1 edits and the text in
    the editor.
    """

    id: UUID
    status: str
    ai_description_ru: Optional[str] = None
    ai_description_uz: Optional[str] = None
    ai_description_uz_cyrl: Optional[str] = None
    last_ai_param_snapshot: Optional[dict] = None
    ai_generation_attempted_at: Optional[UTCDateTime] = None


class RegenerateRequest(BaseModel):
    """``POST /listings/{id}/regenerate`` body.

    ``language=None`` regenerates all three locales (the worker always
    emits all three per the F1 spec; per-language regeneration is
    reserved for future scope).
    """

    language: Optional[str] = Field(
        None,
        pattern=r"^(ru|uz|uz_cyrl)$",
        description="Reserved — currently all three locales always re-emitted",
    )
    triggered_by: str = Field(
        default="manual_retry",
        pattern=r"^(manual_retry|param_change)$",
    )


class RegenerateResponse(BaseModel):
    """``POST /listings/{id}/regenerate`` response."""

    status: str = "queued"


class SourceTextResponse(BaseModel):
    """``GET /listings/{id}/source-text`` response — B2B owner only."""

    raw_text: Optional[str] = None
    source: Optional[str] = None  # "telegram" | "olx" | "manual"
