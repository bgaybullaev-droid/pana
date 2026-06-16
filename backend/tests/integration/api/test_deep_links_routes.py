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
        # Non-alphanumeric and over-length ids are bounced by the guard.
        assert (await client.get("/api/v1/deep-links/bad-id_here")).status_code == 404
        assert (
            await client.get("/api/v1/deep-links/waytoolongidentifier12345")
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
