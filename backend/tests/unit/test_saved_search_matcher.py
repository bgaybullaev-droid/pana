"""T-034 — Saved-search matcher unit tests.

Pure in-memory tests; no DB / HTTP. Verifies the matcher mirrors
`_apply_filters` semantics from PR3, respects the visibility matrix
(silent-drop), and uses _clear_incompatible_fields for normalization.
"""

import pytest

from app.db.models import Currency, Listing, ListingType, PropertyType
from app.schemas.listing import ListingFilters
from app.services.saved_search_matcher import (
    _match_listing_to_filters,
    match_listing_against_saved_searches,
)

pytestmark = pytest.mark.unit


def _mk(**over) -> Listing:
    """Build an in-memory Listing with the minimum columns we care about."""
    defaults = dict(
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
        # PR2 fields default to None / False so listings start "matrix-clean"
        rent_period=None,
        deposit=None,
        utilities_incl=None,
        min_rent_months=None,
        allowed_students=None,
        allowed_pets=None,
        rent_payment=None,
        mortgage_ok=False,
        installment_ok=False,
        halol_ok=False,
        deed_type=None,
        amenities=None,
        nearby_amenities=None,
        land_area=None,
    )
    defaults.update(over)
    return Listing(**defaults)


# ─────────────────────────────────────────────────────────────────────
# 1. Basic match: rent listing vs rent-shaped saved search
# ─────────────────────────────────────────────────────────────────────
class TestBasicMatch:
    def test_rent_apartment_matches_rent_filter(self):
        listing = _mk(
            type=ListingType.RENT,
            price=600,
            rent_period="long_term",
            min_rent_months=6,
        )
        f = ListingFilters(
            type="rent",
            property_type="apartment",
            rent_period="long_term",
        )
        assert _match_listing_to_filters(listing, f) is True

    def test_sale_apartment_matches_sale_filter(self):
        listing = _mk(mortgage_ok=True)
        f = ListingFilters(type="sell", property_type="apartment", mortgage_ok=True)
        assert _match_listing_to_filters(listing, f) is True


# ─────────────────────────────────────────────────────────────────────
# 2. Mismatch (sell vs rent filters)
# ─────────────────────────────────────────────────────────────────────
class TestTypeMismatch:
    def test_sell_listing_does_not_match_rent_filter(self):
        listing = _mk()  # SELL by default
        f = ListingFilters(type="rent")
        assert _match_listing_to_filters(listing, f) is False

    def test_rent_listing_does_not_match_sell_filter(self):
        listing = _mk(type=ListingType.RENT, price=500, rent_period="long_term")
        f = ListingFilters(type="sell")
        assert _match_listing_to_filters(listing, f) is False

    def test_property_type_mismatch_rejects(self):
        listing = _mk(property_type=PropertyType.HOUSE)
        f = ListingFilters(property_type="apartment")
        assert _match_listing_to_filters(listing, f) is False


# ─────────────────────────────────────────────────────────────────────
# 3. Range match (price inside / outside)
# ─────────────────────────────────────────────────────────────────────
class TestRanges:
    def test_price_inside_range_passes(self):
        listing = _mk(price=80000)
        f = ListingFilters(price_min=50000, price_max=100000)
        assert _match_listing_to_filters(listing, f) is True

    def test_price_below_min_fails(self):
        listing = _mk(price=20000)
        f = ListingFilters(price_min=50000)
        assert _match_listing_to_filters(listing, f) is False

    def test_price_above_max_fails(self):
        listing = _mk(price=200000)
        f = ListingFilters(price_max=100000)
        assert _match_listing_to_filters(listing, f) is False

    def test_area_range_works(self):
        listing = _mk(area=70.0)
        assert _match_listing_to_filters(listing, ListingFilters(area_min=50)) is True
        assert _match_listing_to_filters(listing, ListingFilters(area_max=60)) is False

    def test_deposit_range_only_checked_for_rent(self):
        # deposit_min is rent-group → silently dropped on sell. So a sale
        # listing without a deposit still matches a deposit_min filter.
        sale = _mk(type=ListingType.SELL, deposit=None)
        f = ListingFilters(deposit_min=500)
        # Applicability drops deposit_min on sell, so listing matches.
        assert _match_listing_to_filters(sale, f) is True


# ─────────────────────────────────────────────────────────────────────
# 4. Amenities AND logic
# ─────────────────────────────────────────────────────────────────────
class TestAmenitiesAndMatch:
    def test_listing_must_contain_all_filter_amenities(self):
        listing = _mk(amenities=["tv", "ac", "internet"])
        f = ListingFilters(amenities=["tv", "ac"])
        assert _match_listing_to_filters(listing, f) is True

    def test_missing_one_amenity_rejects(self):
        listing = _mk(amenities=["tv"])
        f = ListingFilters(amenities=["tv", "ac"])
        assert _match_listing_to_filters(listing, f) is False

    def test_empty_listing_amenities_rejects_when_filter_nonempty(self):
        listing = _mk(amenities=None)
        f = ListingFilters(amenities=["tv"])
        assert _match_listing_to_filters(listing, f) is False


# ─────────────────────────────────────────────────────────────────────
# 5. rent_payment OR logic
# ─────────────────────────────────────────────────────────────────────
class TestRentPaymentOrMatch:
    def test_overlap_passes(self):
        listing = _mk(
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
            rent_payment=["cash", "payme"],
        )
        f = ListingFilters(type="rent", rent_payment=["payme", "click"])
        assert _match_listing_to_filters(listing, f) is True

    def test_no_overlap_fails(self):
        listing = _mk(
            type=ListingType.RENT,
            price=500,
            rent_period="daily",
            rent_payment=["cash"],
        )
        f = ListingFilters(type="rent", rent_payment=["payme", "click"])
        assert _match_listing_to_filters(listing, f) is False

    def test_listing_with_no_payment_method_fails_when_filter_set(self):
        listing = _mk(
            type=ListingType.RENT,
            price=500,
            rent_period="daily",
            rent_payment=None,
        )
        f = ListingFilters(type="rent", rent_payment=["cash"])
        assert _match_listing_to_filters(listing, f) is False


# ─────────────────────────────────────────────────────────────────────
# 6. Boolean flags — only TRUE matters
# ─────────────────────────────────────────────────────────────────────
class TestBooleanTrueOnly:
    def test_mortgage_ok_true_matches_only_true_listing(self):
        match = _mk(mortgage_ok=True)
        miss = _mk(mortgage_ok=False)
        f = ListingFilters(type="sell", mortgage_ok=True)
        assert _match_listing_to_filters(match, f) is True
        assert _match_listing_to_filters(miss, f) is False

    def test_mortgage_ok_false_in_filter_is_ignored(self):
        # SQL semantics: `if filters.mortgage_ok and ...` — a False/None
        # filter is a no-op, so a listing without mortgage still matches.
        listing = _mk(mortgage_ok=False)
        f = ListingFilters(type="sell", mortgage_ok=False)
        assert _match_listing_to_filters(listing, f) is True

    def test_halol_and_installment_combined(self):
        match = _mk(installment_ok=True, halol_ok=True)
        partial = _mk(installment_ok=True, halol_ok=False)
        f = ListingFilters(installment_ok=True, halol_ok=True)
        assert _match_listing_to_filters(match, f) is True
        assert _match_listing_to_filters(partial, f) is False


# ─────────────────────────────────────────────────────────────────────
# 7. Applicability drop (rent filter on sell → ignored)
# ─────────────────────────────────────────────────────────────────────
class TestApplicabilitySilentDrop:
    def test_rent_period_filter_ignored_on_sell_listing(self):
        # Listing is a sale with no rent_period. A saved search with
        # rent_period='daily' would normally reject it. But matrix says
        # rent_period isn't applicable to sell listings → silent drop →
        # the sale listing still matches every other (applicable) filter.
        listing = _mk(type=ListingType.SELL, rent_period=None)
        f = ListingFilters(rent_period="daily")
        # rent_period is matrix-applicable when type is None or rent. The
        # listing's deal_type is sell, so the filter is dropped per
        # `_filter_is_applicable("rent_period", "apartment", "sell")`.
        assert _match_listing_to_filters(listing, f) is True

    def test_mortgage_filter_ignored_on_rent_listing(self):
        listing = _mk(type=ListingType.RENT, price=500, rent_period="long_term")
        f = ListingFilters(mortgage_ok=True)
        # mortgage_ok isn't visible for rent → silent-drop → matches.
        assert _match_listing_to_filters(listing, f) is True

    def test_rooms_filter_ignored_on_commercial(self):
        listing = _mk(property_type=PropertyType.COMMERCIAL, rooms=None)
        f = ListingFilters(rooms=[3])
        assert _match_listing_to_filters(listing, f) is True


# ─────────────────────────────────────────────────────────────────────
# 8. Partial filters (only pt or only dt set)
# ─────────────────────────────────────────────────────────────────────
class TestPartialFilters:
    def test_only_property_type_set_matches_apartment(self):
        listing = _mk()
        f = ListingFilters(property_type="apartment")
        assert _match_listing_to_filters(listing, f) is True

    def test_only_property_type_set_rejects_house(self):
        listing = _mk(property_type=PropertyType.HOUSE)
        f = ListingFilters(property_type="apartment")
        assert _match_listing_to_filters(listing, f) is False

    def test_only_type_set_matches_sell(self):
        listing = _mk()
        f = ListingFilters(type="sell")
        assert _match_listing_to_filters(listing, f) is True


# ─────────────────────────────────────────────────────────────────────
# 9. Edge: empty filters → match everything
# ─────────────────────────────────────────────────────────────────────
class TestEmptyFilters:
    def test_empty_filter_set_matches_any_listing(self):
        f = ListingFilters()
        for pt in (
            PropertyType.APARTMENT,
            PropertyType.HOUSE,
            PropertyType.COMMERCIAL,
            PropertyType.LAND,
        ):
            for dt in (ListingType.SELL, ListingType.RENT):
                if pt is PropertyType.LAND and dt is ListingType.RENT:
                    continue  # P3-illegal
                listing = _mk(
                    property_type=pt,
                    type=dt,
                    rent_period=("long_term" if dt is ListingType.RENT else None),
                )
                assert _match_listing_to_filters(listing, f) is True


# ─────────────────────────────────────────────────────────────────────
# 10. Matrix consistency — rent + sale listings + the same filter
# ─────────────────────────────────────────────────────────────────────
class TestMatrixConsistency:
    def test_combined_filter_set_matches_only_correct_listings(self):
        """A filter requesting `apartment + rent + long_term` should match
        a long-term apt rental and reject a daily rental and a sale."""
        long_term = _mk(
            type=ListingType.RENT,
            property_type=PropertyType.APARTMENT,
            price=600,
            rent_period="long_term",
            min_rent_months=6,
        )
        daily = _mk(
            type=ListingType.RENT,
            property_type=PropertyType.APARTMENT,
            price=80,
            rent_period="daily",
        )
        sale = _mk(type=ListingType.SELL)

        f = ListingFilters(
            type="rent",
            property_type="apartment",
            rent_period="long_term",
        )
        assert _match_listing_to_filters(long_term, f) is True
        assert _match_listing_to_filters(daily, f) is False
        assert _match_listing_to_filters(sale, f) is False

    def test_finance_filter_against_mixed_listings(self):
        with_mortgage = _mk(mortgage_ok=True)
        without = _mk(mortgage_ok=False)
        rental = _mk(type=ListingType.RENT, price=500, rent_period="long_term")

        f = ListingFilters(mortgage_ok=True)
        assert _match_listing_to_filters(with_mortgage, f) is True
        assert _match_listing_to_filters(without, f) is False
        # rental: silent-drop on mortgage_ok → matches
        assert _match_listing_to_filters(rental, f) is True


# ─────────────────────────────────────────────────────────────────────
# match_listing_against_saved_searches (fanout entry point)
# ─────────────────────────────────────────────────────────────────────
class TestFanout:
    def test_returns_only_matching_searches(self):
        listing = _mk(type=ListingType.RENT, price=600, rent_period="long_term")
        searches = [
            ListingFilters(type="rent"),  # match
            ListingFilters(type="sell"),  # miss
            ListingFilters(price_min=100, price_max=1000),  # match
            ListingFilters(price_min=10000),  # miss
        ]
        matches = match_listing_against_saved_searches(listing, searches)
        # Order preserved.
        assert matches == [searches[0], searches[2]]

    def test_normalizes_listing_via_clear_helper(self):
        """A rent listing carrying a stale mortgage_ok=True (e.g. from a
        crawler import) gets normalized BEFORE matching, so it can't
        accidentally satisfy a sale-finance saved search."""
        dirty = _mk(
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
            mortgage_ok=True,  # stale — should be wiped by P2
        )
        # Direct match (no normalize) would pass via silent-drop. With
        # normalize, the listing has mortgage_ok=False but the matcher
        # silent-drops mortgage_ok on rent anyway → still matches.
        searches = [ListingFilters(mortgage_ok=True)]
        matches = match_listing_against_saved_searches(dirty, searches)
        # Silent-drop returns True regardless. The normalization is a safety
        # net for OTHER columns (e.g. rent_period left over from sale flips).
        assert matches == searches
        # And the listing has been normalized:
        assert dirty.mortgage_ok is False

    def test_empty_saved_search_list_returns_empty(self):
        listing = _mk()
        assert match_listing_against_saved_searches(listing, []) == []
