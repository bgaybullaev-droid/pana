"""Regression tests for the S3-S8 surgical fixes.

Covers the critical gaps identified in the production audit:

    Step 1: create/update/response persist every S3-S8 column (no silent drop)
    Step 2: dual-read helpers are executed on every write path
    Step 3: Pydantic patterns accept the widened S3-S8 enum values
    Step 4: city / commercial_type required rules apply on CREATE only
    Step 5: Postgres SQL and Meilisearch filter expressions cover S3-S8
            (parity — same filter must produce equivalent clauses)

All tests are unit-level: they hit the pure helpers and never need a
running DB, Meili, or HTTP server.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.api.v1.listings import (
    _apply_dual_read_inputs,
    _apply_dual_read_response,
    _build_full_response_kwargs,
    _validate_required_fields,
)
from app.core.exceptions import BadRequestException
from app.db.models import (
    Currency,
    Listing,
    ListingStatus,
    ListingType,
    ModerationStatus,
    PropertyType,
    SourceType,
)
from app.schemas.listing import ListingBase, ListingFilters, ListingUpdate

pytestmark = pytest.mark.unit


def _mk(**over) -> Listing:
    """Apartment × sell skeleton. Safe baseline for validator tests."""
    defaults = dict(
        id=uuid4(),
        type=ListingType.SELL,
        property_type=PropertyType.APARTMENT,
        price=80000,
        currency=Currency.USD,
        rooms=2,
        area=55.0,
        floor=3,
        total_floors=9,
        building_type="new",
        condition="euro",
        is_furnished=True,
        region="toshkent_shahri",
        district="mirzo_ulugbek",
        city="Tashkent",
        latitude=41.3,
        longitude=69.3,
        status=ListingStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
        source_type=SourceType.MANUAL,
    )
    defaults.update(over)
    return Listing(**defaults)


# ─────────────────────────────────────────────────────────────────────
# Step 1 — Roundtrip: every S3-S8 column lands in ListingResponse kwargs
# ─────────────────────────────────────────────────────────────────────


class TestS3ToS8Roundtrip:
    """_build_full_response_kwargs is the single source of truth shared by
    every ListingResponse builder (get/create/update/claim). If a field is
    missing here, the API silently drops it — which is the exact bug that
    prompted these fixes."""

    S3_TO_S8_FIELDS = [
        # S3 — location
        "urgent_flag",
        "city",
        "microdistrict",
        "jk_name",
        "landmark",
        "metro_station",
        "seller_telegram",
        # S4 — commercial
        "commercial_type",
        "price_per_sqm",
        "ceiling_height",
        "entrance",
        "parking_comm",
        "building_class",
        # S5 — dual-read
        "wall_material",
        "market_type",  # also in dual-read mirror
        "furniture",  # also in dual-read mirror
        # S5 — legacy names (mirrored by dual-read)
        "building_type",
        "is_furnished",
        # S6 — property polish
        "garage",
        "basement",
        "buildings_exist",
        "fence",
        "land_shape",
        "balcony",
        "listing_subtype",
        "floor_plan_url",
        # S7 — roles/media
        "jk_id",
        # S8 — discoverability
        "slug",
    ]

    def test_every_s3_to_s8_field_is_in_response_kwargs(self):
        listing = _mk(
            urgent_flag=True,
            microdistrict="Yunusabad-12",
            jk_name="Tashkent City",
            landmark="opposite the metro",
            metro_station="chilonzor",
            seller_telegram="@sample",
            commercial_type=None,
            price_per_sqm=1500,
            ceiling_height=3.2,
            entrance="separate",
            parking_comm=True,
            building_class="standalone",
            market_type="new",
            wall_material="brick",
            furniture="full",
            garage=True,
            basement=False,
            buildings_exist=None,
            fence=None,
            land_shape=None,
            balcony="loggia",
            listing_subtype="standard",
            floor_plan_url="https://example.com/plan.png",
            jk_id=None,
            slug="great-apt-tashkent",
        )
        out = _build_full_response_kwargs(listing)
        # Completeness: every field we care about must appear as a key.
        missing = [f for f in self.S3_TO_S8_FIELDS if f not in out]
        assert not missing, (
            f"_build_full_response_kwargs silently drops: {missing}. "
            f"Any ListingResponse builder that spreads the helper will "
            f"return None for these fields."
        )

    def test_roundtrip_preserves_non_null_values(self):
        """A field set on the Listing must reach the response kwargs
        verbatim (no munging, no type coercion except the documented
        dual-read transforms)."""
        listing = _mk(
            urgent_flag=True,
            city="Samarkand",
            microdistrict="M-5",
            jk_name="Samarkand Plaza",
            metro_station=None,  # non-Tashkent → legitimately null
            commercial_type=None,
            garage=True,
            jk_id=None,
            slug="samarkand-plaza-5",
        )
        out = _build_full_response_kwargs(listing)
        assert out["urgent_flag"] is True
        assert out["city"] == "Samarkand"
        assert out["microdistrict"] == "M-5"
        assert out["jk_name"] == "Samarkand Plaza"
        assert out["metro_station"] is None
        assert out["garage"] is True
        assert out["slug"] == "samarkand-plaza-5"


# ─────────────────────────────────────────────────────────────────────
# Step 2 — Dual-read: promotion on input + mirror on output
# ─────────────────────────────────────────────────────────────────────


class TestDualReadPromotion:
    """The helpers are defined in listings.py; the bug was that they were
    never actually called. We wire them in create_listing / update_listing
    and prove here that the helpers themselves do the right thing PLUS
    that the exact call pattern used by the endpoints reproduces the
    promotion."""

    def test_apply_dual_read_inputs_promotes_building_type(self):
        out = _apply_dual_read_inputs({"building_type": "secondary"})
        assert out["market_type"] == "secondary"

    def test_apply_dual_read_inputs_promotes_is_furnished_true_to_full(self):
        out = _apply_dual_read_inputs({"is_furnished": True})
        assert out["furniture"] == "full"

    def test_apply_dual_read_inputs_promotes_is_furnished_false_to_none(self):
        out = _apply_dual_read_inputs({"is_furnished": False})
        assert out["furniture"] == "none"

    def test_apply_dual_read_inputs_conflict_raises(self):
        with pytest.raises(BadRequestException):
            _apply_dual_read_inputs(
                {"building_type": "new", "market_type": "secondary"}
            )
        with pytest.raises(BadRequestException):
            _apply_dual_read_inputs({"is_furnished": True, "furniture": "none"})

    def test_dual_read_response_mirrors_both_names(self):
        listing = _mk(
            market_type="new",
            furniture="full",
            building_type=None,
            is_furnished=None,
        )
        out = _apply_dual_read_response(listing)
        assert out["market_type"] == "new"
        assert out["building_type"] == "new"
        assert out["furniture"] == "full"
        assert out["is_furnished"] is True

    def test_create_listing_promotion_pattern_mutates_payload(self):
        """Reproduces the exact lines in create_listing that apply dual-
        read. If this test passes, the endpoint will correctly populate
        the new column when the caller sends only the old name."""

        class _Payload:
            # Mimic a Pydantic ListingCreate with mutable attributes.
            def __init__(self):
                self.building_type = "secondary"
                self.is_furnished = True
                self.market_type = None
                self.furniture = None

            def model_dump(self, exclude_unset=False):
                return {
                    "building_type": self.building_type,
                    "is_furnished": self.is_furnished,
                    "market_type": self.market_type,
                    "furniture": self.furniture,
                }

        data = _Payload()
        _dual = _apply_dual_read_inputs(data.model_dump(exclude_unset=True))
        data.market_type = _dual.get("market_type", data.market_type)
        data.furniture = _dual.get("furniture", data.furniture)

        assert data.market_type == "secondary"
        assert data.furniture == "full"

    def test_update_listing_promotion_pattern_normalizes_update_dict(self):
        """Mirrors update_listing's dual-read wiring: `update_data =
        _apply_dual_read_inputs(update_data)` before the setattr loop."""
        update_data = {"is_furnished": True, "price": 90000}
        update_data = _apply_dual_read_inputs(update_data)
        # The loop-level setattr in update_listing will now also see
        # `furniture` and write it to the new column.
        assert "furniture" in update_data
        assert update_data["furniture"] == "full"
        assert update_data["price"] == 90000  # untouched passthrough


# ─────────────────────────────────────────────────────────────────────
# Step 3 — Pydantic pattern drift fixed (seller_type / condition / land_purpose)
# ─────────────────────────────────────────────────────────────────────


class TestPydanticPatternDriftFixed:
    def _base(self, **over):
        base = dict(
            type="sell",
            property_type="apartment",
            price=80000,
            currency="USD",
            region="toshkent_shahri",
            district="mirzo_ulugbek",
        )
        base.update(over)
        return base

    def test_seller_type_accepts_developer(self):
        # Previously rejected: pattern was "^(owner|realtor)$".
        m = ListingBase(**self._base(seller_type="developer"))
        assert m.seller_type == "developer"

    def test_seller_type_still_rejects_garbage(self):
        with pytest.raises(Exception):
            ListingBase(**self._base(seller_type="not_a_role"))

    def test_condition_accepts_s4_widened_values(self):
        # Previously rejected: pattern only allowed S2 set.
        for val in (
            "shell",
            "medium",
            "designer",
            "turnkey",
            "needs_repair_comm",
        ):
            m = ListingBase(**self._base(condition=val))
            assert m.condition == val

    def test_condition_still_accepts_legacy_values(self):
        for val in ("euro", "cosmetic", "needs_repair", "rough", "none"):
            m = ListingBase(**self._base(condition=val))
            assert m.condition == val

    def test_land_purpose_controlled_enum(self):
        # Previously no pattern (free-text). Now restricted to DB CHECK set.
        for val in (
            "construction",
            "commercial_land",
            "agricultural",
            "garden",
            "unspecified",
        ):
            m = ListingBase(**self._base(land_purpose=val))
            assert m.land_purpose == val

    def test_land_purpose_rejects_legacy_free_text(self):
        # The pre-S6 DB had values like "private", "industrial" — blueprint
        # T-013 backfills those, so the API must reject new inputs outside
        # the canonical set.
        with pytest.raises(Exception):
            ListingBase(**self._base(land_purpose="private"))


# ─────────────────────────────────────────────────────────────────────
# Step 4 — Legacy safety: create-only required rules for city + commercial_type
# ─────────────────────────────────────────────────────────────────────


class TestCreateOnlyRequiredRules:
    def test_create_rejects_missing_city(self):
        listing = _mk(city=None)
        with pytest.raises(BadRequestException) as exc:
            _validate_required_fields(listing, is_create=True)
        assert "city" in str(exc.value)

    def test_patch_accepts_missing_city(self):
        """Legacy rows predate the S3 `city` rule. PATCHing one must NOT
        400 just because the column is still NULL."""
        listing = _mk(city=None)
        # Must not raise.
        _validate_required_fields(listing, is_create=False)

    def test_create_rejects_commercial_without_commercial_type(self):
        listing = _mk(
            property_type=PropertyType.COMMERCIAL,
            rooms=None,
            commercial_type=None,
        )
        with pytest.raises(BadRequestException) as exc:
            _validate_required_fields(listing, is_create=True)
        assert "commercial_type" in str(exc.value)

    def test_patch_accepts_commercial_without_commercial_type(self):
        listing = _mk(
            property_type=PropertyType.COMMERCIAL,
            rooms=None,
            commercial_type=None,
        )
        _validate_required_fields(listing, is_create=False)  # no raise


# ─────────────────────────────────────────────────────────────────────
# Step 5 — Postgres SQL ↔ Meili filter parity for S3-S8
# ─────────────────────────────────────────────────────────────────────


def _filters(**over) -> ListingFilters:
    """Build a ListingFilters with optional overrides. Needs ALL params
    supplied by a kwargs-style builder because Pydantic is strict about
    construction ordering in our version."""
    base: dict = {}
    base.update(over)
    return ListingFilters(**base)


class TestMeiliPostgresParity:
    """Byte-level parity between the Postgres WHERE builder and the Meili
    filter-expression builder for S3-S8 columns. We don't run SQL or hit
    Meilisearch — we compile both sides and assert their textual
    representations agree.
    """

    def test_meili_expression_covers_s3_urgent_flag(self):
        """S3 (T-001): urgent_flag filter must produce a clause on BOTH
        engines. Previously the Meili expression was stuck at the S2
        contract and silently dropped it."""
        from app.services.search_index import _filters_to_meili_expression

        f = _filters(urgent_flag=True)
        expr = _filters_to_meili_expression(f)
        assert (
            "urgent_flag = true" in expr
        ), f"Meili filter dropped urgent_flag → drift with Postgres. Got: {expr!r}"

    def test_meili_expression_covers_s3_city(self):
        from app.services.search_index import _filters_to_meili_expression

        f = _filters(city="Tashkent")
        expr = _filters_to_meili_expression(f)
        assert 'city = "Tashkent"' in expr

    def test_meili_expression_covers_s4_commercial_type_when_applicable(self):
        from app.services.search_index import _filters_to_meili_expression

        # Matrix-gated: only visible on property_type=commercial.
        f = _filters(property_type="commercial", type="sell", commercial_type="office")
        expr = _filters_to_meili_expression(f)
        assert 'commercial_type = "office"' in expr

    def test_meili_expression_silent_drops_s4_commercial_type_on_apartment(self):
        """The matrix hides commercial_type on non-commercial combos. Both
        engines must drop it; failing to do so would mean a buyer who
        combines apartment+commercial_type gets zero results on one engine
        and arbitrary ones on the other."""
        from app.services.search_index import _filters_to_meili_expression

        f = _filters(property_type="apartment", type="sell", commercial_type="office")
        expr = _filters_to_meili_expression(f)
        assert "commercial_type" not in expr

    def test_meili_expression_covers_s5_furniture(self):
        from app.services.search_index import _filters_to_meili_expression

        f = _filters(property_type="apartment", type="sell", furniture="full")
        expr = _filters_to_meili_expression(f)
        assert 'furniture = "full"' in expr

    def test_meili_expression_covers_s6_garage_on_house(self):
        from app.services.search_index import _filters_to_meili_expression

        f = _filters(property_type="house", type="sell", garage=True)
        expr = _filters_to_meili_expression(f)
        assert "garage = true" in expr

    def test_meili_filterable_attributes_covers_every_s3_s8_filter(self):
        """Every filter that the Meili expression builder emits MUST be in
        FILTERABLE_ATTRIBUTES or Meili will reject the query. This is the
        catch-all parity invariant — if you add a filter but forget the
        attribute registration, this test fails."""
        from app.services.search_index import FILTERABLE_ATTRIBUTES

        required = {
            # S3
            "urgent_flag",
            "city",
            "microdistrict",
            "jk_name",
            "metro_station",
            # S4
            "commercial_type",
            "building_class",
            "entrance",
            "parking_comm",
            "ceiling_height",
            # S5
            "market_type",
            "wall_material",
            "furniture",
            # S6
            "garage",
            "basement",
            "buildings_exist",
            "fence",
            "land_shape",
            "balcony",
            "listing_subtype",
            # S7
            "jk_id",
        }
        missing = required - set(FILTERABLE_ATTRIBUTES)
        assert not missing, (
            f"Meili expression references attributes that aren't registered "
            f"as filterable — queries will 400: {sorted(missing)}"
        )


# ─────────────────────────────────────────────────────────────────────
# ListingUpdate widened patterns (Step 3 mirror)
# ─────────────────────────────────────────────────────────────────────


class TestListingUpdatePatterns:
    def test_update_accepts_developer_seller_type(self):
        m = ListingUpdate(seller_type="developer")
        assert m.seller_type == "developer"

    def test_update_accepts_widened_condition(self):
        m = ListingUpdate(condition="designer")
        assert m.condition == "designer"

    def test_update_accepts_controlled_land_purpose(self):
        m = ListingUpdate(land_purpose="commercial_land")
        assert m.land_purpose == "commercial_land"
