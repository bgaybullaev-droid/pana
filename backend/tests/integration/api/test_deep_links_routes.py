"""Block D V2.0 (D3) — GET /api/v1/deep-links/{id} integration tests.

The TWA resolves a ``?startapp=filter_<id>`` marketing link by calling
this endpoint to fetch the stored filter JSON. We cover the happy path,
the 404s (unknown id, non-``filter`` kind, malformed id), and the
``used_count`` increment side effect.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DeepLinkPayload

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def _add_payload(db: AsyncSession, *, short_id: str, kind: str, payload: dict):
    row = DeepLinkPayload(id=short_id, kind=kind, payload=payload)
    db.add(row)
    await db.flush()
    return row


class TestResolveFilterDeepLink:
    async def test_found_returns_payload(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        filters = {"district": "chilonzor", "rooms": [2, 3], "type": "rent"}
        await _add_payload(
            db_session, short_id="ABCDEF123456", kind="filter", payload=filters
        )

        resp = await client.get("/api/v1/deep-links/ABCDEF123456")

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "ABCDEF123456"
        assert body["kind"] == "filter"
        assert body["payload"] == filters

    async def test_unknown_id_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/deep-links/ZZZZZZ999999")
        assert resp.status_code == 404

    async def test_wrong_kind_is_opaque_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # ``ref`` payloads must never be readable through this endpoint.
        await _add_payload(
            db_session,
            short_id="REF000000001",
            kind="ref",
            payload={"referrer_user_id": "x"},
        )
        resp = await client.get("/api/v1/deep-links/REF000000001")
        assert resp.status_code == 404

    async def test_malformed_id_rejected_before_db(self, client: AsyncClient):
        # Non-allowed characters (hyphen) and over-length ids are bounced
        # by the guard before any DB / slug work.
        assert (await client.get("/api/v1/deep-links/bad-id-here")).status_code == 404
        assert (
            await client.get("/api/v1/deep-links/" + "a" * 33)
        ).status_code == 404

    async def test_resolve_increments_use_count(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _add_payload(
            db_session, short_id="USED00000001", kind="filter", payload={"a": 1}
        )

        resp = await client.get("/api/v1/deep-links/USED00000001")
        assert resp.status_code == 200

        fresh = (
            await db_session.execute(
                select(DeepLinkPayload.used_count).where(
                    DeepLinkPayload.id == "USED00000001"
                )
            )
        ).scalar_one()
        assert fresh == 1


class TestResolveFilterSlug:
    """FU6 — marketing slugs resolve without a stored short-id row."""

    async def test_full_slug_resolves(self, client: AsyncClient):
        resp = await client.get("/api/v1/deep-links/chilonzor_2rooms_rent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == "chilonzor_2rooms_rent"
        assert body["kind"] == "filter"
        assert body["payload"] == {
            "district": "chilonzor",
            "rooms_min": 2,
            "rooms_max": 2,
            "deal_type": "rent",
        }

    async def test_bare_district_slug_resolves(self, client: AsyncClient):
        resp = await client.get("/api/v1/deep-links/yunusobod")
        assert resp.status_code == 200
        assert resp.json()["payload"] == {"district": "yunusobod"}

    async def test_unknown_slug_returns_404(self, client: AsyncClient):
        # Valid charset, but the head resolves to no known district.
        assert (
            await client.get("/api/v1/deep-links/qwerty_zzz")
        ).status_code == 404

    async def test_stored_short_id_wins_over_slug(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # A stored short-id always takes precedence over slug decoding.
        await _add_payload(
            db_session,
            short_id="yunusobod",
            kind="filter",
            payload={"district": "stored"},
        )
        resp = await client.get("/api/v1/deep-links/yunusobod")
        assert resp.status_code == 200
        assert resp.json()["payload"] == {"district": "stored"}


class TestCreateFilterLink:
    """In-app "Share filter" — POST /deep-links/filter mints a rich link."""

    async def test_create_and_round_trip(
        self, client: AsyncClient, user_headers: dict
    ):
        rich = {
            "district": ["chilonzor"],
            "type": ["rent"],
            "rooms": [2, 3],
            "price_max": 5000,
            "has_photo": True,
            "not_first_floor": True,
        }
        resp = await client.post(
            "/api/v1/deep-links/filter", json=rich, headers=user_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["id"]) == 12
        assert body["url"].endswith(f"?startapp=filter_{body['id']}")

        # The stored link resolves back to exactly the filters we sent.
        resolved = await client.get(f"/api/v1/deep-links/{body['id']}")
        assert resolved.status_code == 200
        assert resolved.json()["payload"] == rich

    async def test_unset_fields_are_dropped(
        self, client: AsyncClient, user_headers: dict
    ):
        resp = await client.post(
            "/api/v1/deep-links/filter",
            json={"district": ["yunusobod"], "type": None},
            headers=user_headers,
        )
        assert resp.status_code == 200
        resolved = await client.get(f"/api/v1/deep-links/{resp.json()['id']}")
        assert resolved.json()["payload"] == {"district": ["yunusobod"]}

    async def test_empty_payload_rejected(
        self, client: AsyncClient, user_headers: dict
    ):
        resp = await client.post(
            "/api/v1/deep-links/filter", json={}, headers=user_headers
        )
        assert resp.status_code == 400

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/deep-links/filter", json={"district": ["chilonzor"]}
        )
        assert resp.status_code in (401, 403)
