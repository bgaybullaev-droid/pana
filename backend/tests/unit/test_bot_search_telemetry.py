"""Block D (FU5) — unit tests for bot search-query telemetry.

Pure in-memory: the Celery ``.delay`` and the DB session maker are
monkeypatched so no broker or database is touched. Covers the
fire-and-forget enqueue (positional-arg forwarding, ``None`` coercion,
broker-error fail-soft) and the recording task's DB-error fail-soft —
i.e. the FU5 guarantee that a telemetry hiccup never breaks the user's
search reply.
"""

import pytest

from app.workers.tasks import telemetry

pytestmark = pytest.mark.unit


class _DelaySpy:
    """Stand-in for the Celery task: records ``.delay`` calls and can
    raise to simulate an unreachable broker."""

    def __init__(self, exc: Exception | None = None) -> None:
        self.calls: list[tuple] = []
        self.exc = exc

    def delay(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))
        if self.exc:
            raise self.exc


class TestEnqueueSearchQuery:
    def test_forwards_positional_args(self, monkeypatch):
        spy = _DelaySpy()
        monkeypatch.setattr(telemetry, "record_bot_search_query", spy)

        telemetry.enqueue_search_query(
            user_telegram_id=42,
            source="bot",
            raw_text="чиланзар 2 комнаты",
            extracted_fields=["district", "rooms_min"],
            results_count=3,
        )

        assert spy.calls == [
            ((42, "bot", "чиланзар 2 комнаты", ["district", "rooms_min"], 3), {})
        ]

    def test_none_extracted_fields_coerced_to_list(self, monkeypatch):
        spy = _DelaySpy()
        monkeypatch.setattr(telemetry, "record_bot_search_query", spy)

        telemetry.enqueue_search_query(
            user_telegram_id=1,
            source="inline",
            raw_text="x",
            extracted_fields=None,  # type: ignore[arg-type]
            results_count=0,
        )

        (args, _kwargs), = spy.calls
        assert args[3] == []

    def test_swallows_broker_error(self, monkeypatch):
        spy = _DelaySpy(exc=RuntimeError("broker down"))
        monkeypatch.setattr(telemetry, "record_bot_search_query", spy)

        # Must not raise — telemetry is best-effort and never blocks a reply.
        telemetry.enqueue_search_query(
            user_telegram_id=None,
            source="inline",
            raw_text="привет",
            extracted_fields=[],
            results_count=0,
        )

        assert len(spy.calls) == 1


class TestRecordTaskFailSoft:
    async def test_db_error_returns_recorded_false(self, monkeypatch):
        import app.db.database as database

        class _Boom:
            def __call__(self):
                raise RuntimeError("db down")

        monkeypatch.setattr(database, "async_session_maker", _Boom())

        out = await telemetry._record_bot_search_query(
            1, "bot", "x", ["district"], 0
        )

        assert out["recorded"] is False
        assert "error" in out
