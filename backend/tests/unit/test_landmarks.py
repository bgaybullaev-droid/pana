"""PR-G — Landmark schema projection unit tests.

Mirrors the housing-complex suite: ORM row → ListItem / Response shape,
nullable handling, locale + geo + provenance pass-through. The SQL search
logic (`search_landmarks` route) lives in the integration suite where a
real Postgres with ILIKE can run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.api.v1.landmarks import LandmarkListItem, LandmarkResponse
from app.db.models import Landmark

pytestmark = pytest.mark.unit


def _mk(**over) -> Landmark:
    defaults = dict(
        id=uuid4(),
        name="Chorsu Bazaar",
        name_uz_latn="Chorsu bozori",
        name_uz_cyrl="Чорсу бозори",
        category="market",
        region="toshkent_shahri",
        district="shayxontohur",
        microdistrict=None,
        latitude=41.326,
        longitude=69.234,
        osm_id="node/123",
        source="osm",
        created_at=datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc),
    )
    defaults.update(over)
    return Landmark(**defaults)


class TestListItemProjection:
    def test_core_fields_carry_over(self):
        out = LandmarkListItem.model_validate(_mk(name="Mega Planet", category="mall"))
        assert out.name == "Mega Planet"
        assert out.category == "mall"

    def test_locale_and_geo_pass_through(self):
        out = LandmarkListItem.model_validate(_mk())
        assert out.name_uz_latn == "Chorsu bozori"
        assert out.name_uz_cyrl == "Чорсу бозори"
        assert out.latitude == 41.326
        assert out.longitude == 69.234
        assert out.district == "shayxontohur"

    def test_optional_fields_stay_null(self):
        out = LandmarkListItem.model_validate(
            _mk(microdistrict=None, latitude=None, longitude=None)
        )
        assert out.microdistrict is None
        assert out.latitude is None
        assert out.longitude is None


class TestFullResponseProjection:
    def test_provenance_preserved(self):
        out = LandmarkResponse.model_validate(_mk(osm_id="way/777", source="manual"))
        assert out.osm_id == "way/777"
        assert out.source == "manual"
        assert out.region == "toshkent_shahri"

    def test_timestamps_present(self):
        out = LandmarkResponse.model_validate(_mk())
        assert out.created_at is not None
        assert out.updated_at is not None
