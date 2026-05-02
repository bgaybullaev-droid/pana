"""PR-F — HousingComplexes schema + helper unit tests.

Covers:
    - HousingComplexListItem / HousingComplexResponse shape projection
      from ORM rows
    - Nullable fields map to None, not empty strings

The SQL search logic (`search_housing_complexes` route) lives in the
integration suite where a real Postgres with ILIKE can run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.api.v1.housing_complexes import (
    HousingComplexListItem,
    HousingComplexResponse,
)
from app.db.models import HousingComplex

pytestmark = pytest.mark.unit


def _mk(**over) -> HousingComplex:
    defaults = dict(
        id=uuid4(),
        name="Tashkent City",
        developer_id=None,
        region=None,
        district=None,
        created_at=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
    )
    defaults.update(over)
    return HousingComplex(**defaults)


class TestListItemProjection:
    def test_required_fields_carry_over(self):
        row = _mk(name="Boulevard")
        out = HousingComplexListItem.model_validate(row)
        assert out.name == "Boulevard"
        assert out.id == row.id

    def test_optional_region_district_pass_through(self):
        row = _mk(region="toshkent_shahri", district="yunusobod")
        out = HousingComplexListItem.model_validate(row)
        assert out.region == "toshkent_shahri"
        assert out.district == "yunusobod"

    def test_null_region_district_stay_null(self):
        out = HousingComplexListItem.model_validate(_mk())
        assert out.region is None
        assert out.district is None


class TestFullResponseProjection:
    def test_all_fields_preserved(self):
        dev = uuid4()
        row = _mk(
            developer_id=dev,
            region="toshkent_shahri",
            district="mirzo_ulugbek",
        )
        out = HousingComplexResponse.model_validate(row)
        assert out.developer_id == dev
        assert out.region == "toshkent_shahri"
        assert out.district == "mirzo_ulugbek"

    def test_null_developer_id_allowed(self):
        out = HousingComplexResponse.model_validate(_mk(developer_id=None))
        assert out.developer_id is None

    def test_timestamps_present(self):
        out = HousingComplexResponse.model_validate(_mk())
        assert out.created_at is not None
        assert out.updated_at is not None
