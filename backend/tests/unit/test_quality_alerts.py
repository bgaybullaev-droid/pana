"""Block F V2.0 F5b — quality_alerts service unit tests.

Validates each evaluator returns the expected metric value + tripped
flag against synthetic row sets, and that ``maybe_notify_admins`` only
notifies on healthy→tripped transitions (no all-clear spam).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import quality_alerts
from app.services.quality_alerts import (
    METRIC_BAD_FEEDBACK,
    METRIC_DAILY_COST,
    METRIC_DURATION_P95,
    MetricEvaluation,
    _percentile,
    check_thresholds,
    evaluate_bad_feedback_rate,
    evaluate_daily_cost_usd,
    evaluate_duration_p95,
    maybe_notify_admins,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


# ────────────────────────────────────────────────────────────
# DB stub — returns canned numbers for each evaluator's query
# ────────────────────────────────────────────────────────────


def _make_db(
    *,
    gen_count: int = 0,
    fb_count: int = 0,
    durations: list[int] | None = None,
    cost_micros_today: int = 0,
):
    """Side-effect dispatcher: route every db.execute() to the right
    canned return value by examining the compiled SQL string."""

    async def fake_execute(stmt):
        result = MagicMock()
        s = str(stmt).lower()
        if "ai_generation_feedback" in s and "count" in s:
            result.scalar.return_value = fb_count
            return result
        if "ai_generations" in s and "count" in s:
            result.scalar.return_value = gen_count
            return result
        if "sum" in s and "cost_usd_micros" in s:
            result.scalar.return_value = cost_micros_today
            return result
        if "duration_ms" in s:
            rows = [SimpleNamespace.__call__ for _ in durations or []]
            # We need an iterable of one-tuples to match `r[0]` access.
            result.all.return_value = [(d,) for d in (durations or [])]
            return result
        # Fallback
        result.scalar.return_value = 0
        result.all.return_value = []
        return result

    db = MagicMock()
    db.execute = AsyncMock(side_effect=fake_execute)
    return db


# ────────────────────────────────────────────────────────────
# evaluate_bad_feedback_rate
# ────────────────────────────────────────────────────────────


class TestBadFeedbackRate:
    async def test_zero_generations_never_trips(self):
        db = _make_db(gen_count=0, fb_count=0)
        ev = await evaluate_bad_feedback_rate(db)
        assert ev.tripped is False
        assert ev.value == 0.0

    async def test_below_threshold(self):
        # 100 gens, 5 feedbacks = 5% < 10% threshold.
        db = _make_db(gen_count=100, fb_count=5)
        ev = await evaluate_bad_feedback_rate(db)
        assert ev.value == 0.05
        assert ev.tripped is False

    async def test_above_threshold(self):
        # 100 gens, 11 feedbacks = 11% ≥ 10% threshold.
        db = _make_db(gen_count=100, fb_count=11)
        ev = await evaluate_bad_feedback_rate(db)
        assert ev.value == 0.11
        assert ev.tripped is True


# ────────────────────────────────────────────────────────────
# evaluate_duration_p95
# ────────────────────────────────────────────────────────────


class TestDurationP95:
    async def test_fewer_than_5_rows_never_trips(self):
        # Spec requires ≥ 5 rows to consider — otherwise noise.
        db = _make_db(durations=[20000, 20000, 20000])
        ev = await evaluate_duration_p95(db)
        assert ev.tripped is False

    async def test_under_threshold(self):
        db = _make_db(durations=[100, 200, 300, 400, 500])
        ev = await evaluate_duration_p95(db)
        assert ev.value < 8000
        assert ev.tripped is False

    async def test_over_threshold(self):
        # p95 of 100 values puts the index at 94 (sorted asc). To trip
        # at >=8000ms threshold, the slow tail must reach index 94 — so
        # need at least 10% slow entries.
        durations = [100] * 90 + [20000] * 10
        db = _make_db(durations=durations)
        ev = await evaluate_duration_p95(db)
        assert ev.tripped is True
        assert ev.value >= 8000


# ────────────────────────────────────────────────────────────
# evaluate_daily_cost_usd
# ────────────────────────────────────────────────────────────


class TestDailyCost:
    async def test_below_budget(self):
        # Default budget = $50, so 49.99 = micros 49_990_000 doesn't trip.
        db = _make_db(cost_micros_today=49_990_000)
        ev = await evaluate_daily_cost_usd(db)
        assert ev.tripped is False

    async def test_at_budget_trips(self):
        # Exactly equal to threshold trips (>=).
        db = _make_db(cost_micros_today=50_000_000)
        ev = await evaluate_daily_cost_usd(db)
        assert ev.tripped is True


# ────────────────────────────────────────────────────────────
# percentile helper
# ────────────────────────────────────────────────────────────


class TestPercentile:
    def test_empty_list_zero(self):
        assert _percentile([], 95) == 0.0

    def test_p50_single_value(self):
        assert _percentile([42], 50) == 42

    def test_p95_known_data(self):
        # 100 evenly spaced values 1..100 — p95 ≈ 95.
        values = list(range(1, 101))
        assert int(_percentile(values, 95)) in {94, 95, 96}


# ────────────────────────────────────────────────────────────
# check_thresholds composite
# ────────────────────────────────────────────────────────────


class TestCheckThresholds:
    async def test_returns_all_three_metrics(self):
        db = _make_db(gen_count=0, fb_count=0, cost_micros_today=0)
        out = await check_thresholds(db)
        metrics = {e.metric for e in out}
        assert metrics == {METRIC_BAD_FEEDBACK, METRIC_DURATION_P95, METRIC_DAILY_COST}


# ────────────────────────────────────────────────────────────
# maybe_notify_admins transition behaviour
# ────────────────────────────────────────────────────────────


class _FakeRedis:
    def __init__(self):
        self.data = {}

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, ex=None):
        self.data[key] = value

    async def delete(self, key):
        self.data.pop(key, None)


class TestMaybeNotify:
    async def test_first_trip_notifies_then_silent_on_re_run(self):
        fake = _FakeRedis()
        sent_calls = []

        async def fake_send(chat_id, text, parse_mode):
            sent_calls.append((chat_id, text))

        fake_bot = SimpleNamespace(send_message=fake_send)

        with patch.object(
            quality_alerts, "get_redis", AsyncMock(return_value=fake)
        ), patch("app.bot.notifications.get_bot_instance", lambda: fake_bot):
            tripped = MetricEvaluation(
                metric=METRIC_BAD_FEEDBACK, value=0.2, threshold=0.1, tripped=True
            )
            first = await maybe_notify_admins([tripped], admin_chat_ids=[123])
            second = await maybe_notify_admins([tripped], admin_chat_ids=[123])
        assert first == [METRIC_BAD_FEEDBACK]
        assert second == []  # already-active flag suppresses repeat alerts
        assert len(sent_calls) == 1
        assert sent_calls[0][0] == 123

    async def test_recovery_clears_flag_silently(self):
        fake = _FakeRedis()
        fake.data[f"{quality_alerts._FLAG_PREFIX}{METRIC_BAD_FEEDBACK}:active"] = "1"

        async def fake_send(*_a, **_kw):
            raise AssertionError("should not notify on recovery")

        fake_bot = SimpleNamespace(send_message=fake_send)

        with patch.object(
            quality_alerts, "get_redis", AsyncMock(return_value=fake)
        ), patch("app.bot.notifications.get_bot_instance", lambda: fake_bot):
            healthy = MetricEvaluation(
                metric=METRIC_BAD_FEEDBACK, value=0.01, threshold=0.1, tripped=False
            )
            notified = await maybe_notify_admins([healthy], admin_chat_ids=[123])
        assert notified == []
        assert (
            f"{quality_alerts._FLAG_PREFIX}{METRIC_BAD_FEEDBACK}:active" not in fake.data
        )

    async def test_no_admin_chat_ids_skips_telegram_but_still_flags(self):
        fake = _FakeRedis()
        with patch.object(quality_alerts, "get_redis", AsyncMock(return_value=fake)):
            tripped = MetricEvaluation(
                metric=METRIC_DAILY_COST, value=60.0, threshold=50.0, tripped=True
            )
            notified = await maybe_notify_admins([tripped], admin_chat_ids=[])
        # Flag should still flip even when there's no chat to notify.
        assert notified == [METRIC_DAILY_COST]
        assert (
            fake.data.get(f"{quality_alerts._FLAG_PREFIX}{METRIC_DAILY_COST}:active") == "1"
        )
