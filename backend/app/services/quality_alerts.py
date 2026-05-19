"""Block F V2.0 F5b — AI quality threshold alerts.

Three metrics are evaluated against the thresholds from
``app.core.config``:

* ``bad_feedback_rate`` — fraction of last-24h generations that have
  ≥1 ``ai_generation_feedback`` row. Threshold default 10%.
* ``duration_p95`` — 95th-percentile of ``ai_generations.duration_ms``
  over the last 24h. Threshold default 8000 ms.
* ``daily_cost_usd`` — sum of ``cost_usd_micros`` for today (UTC). The
  threshold from config is in dollars; we convert.

The Celery beat task ``check_quality_thresholds`` invokes
``check_thresholds`` once an hour. Each metric uses a Redis flag
(``alert:<metric>:active`` → ``"1"``) so we emit exactly one admin
Telegram notification on *transition* from healthy → tripped. A
returning-to-healthy transition clears the flag silently — no
"all-clear" spam.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import AIGeneration, AIGenerationFeedback
from app.db.redis import get_redis

logger = logging.getLogger(__name__)

# Redis key prefix for the per-metric "alert currently active" flag.
# TTL set to 7 days — guarantees an eventual reset even if a Celery
# beat outage means the cleanup branch never runs.
_FLAG_PREFIX = "alert:"
_FLAG_TTL_SECONDS = 7 * 24 * 3600


METRIC_BAD_FEEDBACK = "bad_feedback_rate"
METRIC_DURATION_P95 = "duration_p95"
METRIC_DAILY_COST = "daily_cost_usd"


# ────────────────────────────────────────────────────────────
# Evaluators
# ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MetricEvaluation:
    metric: str
    value: float
    threshold: float
    tripped: bool


async def evaluate_bad_feedback_rate(
    db: AsyncSession, *, window_hours: int = 24
) -> MetricEvaluation:
    """Tripped when (feedback count) / (generations count) ≥ threshold."""
    window = datetime.utcnow() - timedelta(hours=window_hours)
    gen_total = int(
        (
            await db.execute(
                select(func.count(AIGeneration.id)).where(
                    AIGeneration.created_at >= window
                )
            )
        ).scalar()
        or 0
    )
    fb_total = int(
        (
            await db.execute(
                select(func.count(AIGenerationFeedback.id)).where(
                    AIGenerationFeedback.created_at >= window
                )
            )
        ).scalar()
        or 0
    )
    rate = (fb_total / gen_total) if gen_total else 0.0
    threshold = float(settings.f5_alert_bad_feedback_rate)
    return MetricEvaluation(
        metric=METRIC_BAD_FEEDBACK,
        value=round(rate, 4),
        threshold=threshold,
        tripped=(gen_total > 0 and rate >= threshold),
    )


async def evaluate_duration_p95(
    db: AsyncSession, *, window_hours: int = 24
) -> MetricEvaluation:
    """Tripped when 95th-percentile generation duration ≥ threshold."""
    window = datetime.utcnow() - timedelta(hours=window_hours)
    durations: list[int] = [
        int(r[0])
        for r in (
            await db.execute(
                select(AIGeneration.duration_ms).where(
                    AIGeneration.created_at >= window,
                    AIGeneration.duration_ms.is_not(None),
                )
            )
        ).all()
    ]
    p95 = _percentile(durations, 95) if durations else 0.0
    threshold = float(settings.f5_alert_p95_duration_ms)
    return MetricEvaluation(
        metric=METRIC_DURATION_P95,
        value=round(p95, 2),
        threshold=threshold,
        tripped=(len(durations) >= 5 and p95 >= threshold),
    )


async def evaluate_daily_cost_usd(db: AsyncSession) -> MetricEvaluation:
    """Tripped when today's (UTC) OpenAI spend ≥ threshold USD."""
    start_of_today = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    micros = int(
        (
            await db.execute(
                select(func.coalesce(func.sum(AIGeneration.cost_usd_micros), 0)).where(
                    AIGeneration.created_at >= start_of_today
                )
            )
        ).scalar()
        or 0
    )
    usd = micros / 1_000_000.0
    threshold = float(settings.f5_openai_daily_budget_usd)
    return MetricEvaluation(
        metric=METRIC_DAILY_COST,
        value=round(usd, 4),
        threshold=threshold,
        tripped=(usd >= threshold),
    )


def _percentile(values: list[int], pct: int) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(pct / 100.0 * (len(s) - 1)))))
    return float(s[k])


# ────────────────────────────────────────────────────────────
# Threshold orchestrator + Redis transition flags
# ────────────────────────────────────────────────────────────


async def check_thresholds(
    db: AsyncSession,
) -> list[MetricEvaluation]:
    """Run every evaluator, return them as a list. Doesn't notify —
    caller (``maybe_notify_admins``) handles emission so the worker
    layer can mock notifications in tests."""
    return [
        await evaluate_bad_feedback_rate(db),
        await evaluate_duration_p95(db),
        await evaluate_daily_cost_usd(db),
    ]


async def _flag_get(metric: str) -> bool:
    try:
        client = await get_redis()
        return bool(await client.get(f"{_FLAG_PREFIX}{metric}:active"))
    except Exception:  # pragma: no cover — fail-soft
        logger.warning("quality_alerts.flag_get_failed metric=%s", metric)
        return False


async def _flag_set(metric: str, active: bool) -> None:
    try:
        client = await get_redis()
        key = f"{_FLAG_PREFIX}{metric}:active"
        if active:
            await client.set(key, "1", ex=_FLAG_TTL_SECONDS)
        else:
            await client.delete(key)
    except Exception:  # pragma: no cover — fail-soft
        logger.warning("quality_alerts.flag_set_failed metric=%s", metric)


async def current_alert_states() -> dict[str, bool]:
    """Snapshot used by the admin metrics endpoint."""
    return {
        METRIC_BAD_FEEDBACK: await _flag_get(METRIC_BAD_FEEDBACK),
        METRIC_DURATION_P95: await _flag_get(METRIC_DURATION_P95),
        METRIC_DAILY_COST: await _flag_get(METRIC_DAILY_COST),
    }


def _format_alert(eval_: MetricEvaluation) -> str:
    pretty = {
        METRIC_BAD_FEEDBACK: "Bad-feedback rate (24h)",
        METRIC_DURATION_P95: "Generation duration P95 (24h)",
        METRIC_DAILY_COST: "OpenAI spend (today)",
    }.get(eval_.metric, eval_.metric)
    if eval_.metric == METRIC_BAD_FEEDBACK:
        cur = f"{eval_.value * 100:.1f}%"
        thr = f"{eval_.threshold * 100:.1f}%"
    elif eval_.metric == METRIC_DURATION_P95:
        cur = f"{eval_.value:.0f} ms"
        thr = f"{eval_.threshold:.0f} ms"
    else:
        cur = f"${eval_.value:.2f}"
        thr = f"${eval_.threshold:.2f}"
    return (
        f"⚠️ <b>AI quality alert</b>\n"
        f"<b>{pretty}</b>\n"
        f"Current: <b>{cur}</b>\n"
        f"Threshold: {thr}"
    )


async def maybe_notify_admins(
    evaluations: Iterable[MetricEvaluation],
    *,
    admin_chat_ids: Optional[list[int]] = None,
) -> list[str]:
    """For each evaluator: if tripped and the Redis flag isn't already
    set, send a Telegram alert + set the flag. If not tripped and the
    flag IS set, clear the flag silently. Returns the list of metric
    names that emitted a notification — useful for tests.
    """
    from app.bot.notifications import get_bot_instance

    notified: list[str] = []
    chat_ids = admin_chat_ids if admin_chat_ids is not None else settings.admin_chat_ids
    bot = get_bot_instance() if chat_ids else None

    for ev in evaluations:
        was_active = await _flag_get(ev.metric)
        if ev.tripped and not was_active:
            await _flag_set(ev.metric, True)
            notified.append(ev.metric)
            logger.warning(
                "quality_alerts.tripped metric=%s value=%s threshold=%s",
                ev.metric,
                ev.value,
                ev.threshold,
            )
            if bot is not None:
                msg = _format_alert(ev)
                for chat_id in chat_ids:
                    try:
                        await bot.send_message(
                            chat_id=chat_id, text=msg, parse_mode="HTML"
                        )
                    except Exception:
                        logger.warning(
                            "quality_alerts.notify_failed metric=%s chat=%s",
                            ev.metric,
                            chat_id,
                        )
        elif not ev.tripped and was_active:
            # Returning to healthy — clear silently, no "all-clear" spam.
            await _flag_set(ev.metric, False)
            logger.info("quality_alerts.recovered metric=%s value=%s", ev.metric, ev.value)
    return notified
