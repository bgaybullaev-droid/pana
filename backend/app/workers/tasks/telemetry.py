"""Block D V2.0 (FU5) — bot search-query telemetry.

Fire-and-forget capture of every executed bot / Inline-Mode search.
The data feeds two product decisions:

* iterating the rule-based query parser's dictionaries — the top
  unrecognized ``raw_text`` values (``extracted_fields = []``) tell us
  which districts / room phrasings / deal-type words to add next;
* whether to switch rule-based → LLM, per DECISION_MATRIX (revisit when
  the miss rate clears 10% over a month).

Why a Celery task and not a direct DB write at the call site: the inline
handlers run **without** a DB session (see FU3), so a direct write there
is impossible — and we never want telemetry to block a user's search
reply. The capture is therefore enqueued and runs in a worker; both the
enqueue helper and the task itself are fail-soft.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Mirror of ``BotSearchQuery.raw_text`` column width; we truncate here too
# so an oversized query never trips a DB-side length error in the worker.
_RAW_TEXT_MAXLEN = 200


@celery_app.task(name="app.workers.tasks.telemetry.record_bot_search_query")
def record_bot_search_query(
    user_telegram_id: Optional[int],
    source: str,
    raw_text: str,
    extracted_fields: List[str],
    results_count: int,
) -> Dict[str, Any]:
    """Persist one ``bot_search_queries`` row. Fail-soft: never raises."""
    return asyncio.run(
        _record_bot_search_query(
            user_telegram_id,
            source,
            raw_text,
            extracted_fields,
            results_count,
        )
    )


async def _record_bot_search_query(
    user_telegram_id: Optional[int],
    source: str,
    raw_text: str,
    extracted_fields: List[str],
    results_count: int,
) -> Dict[str, Any]:
    # Imported lazily so the module stays importable in constrained test
    # envs and so the shared pool is only touched inside the worker.
    from app.db.database import async_session_maker
    from app.db.models import BotSearchQuery

    try:
        async with async_session_maker() as session:
            session.add(
                BotSearchQuery(
                    user_telegram_id=user_telegram_id,
                    source=(source or "bot")[:8],
                    raw_text=(raw_text or "")[:_RAW_TEXT_MAXLEN],
                    extracted_fields=list(extracted_fields or []),
                    results_count=int(results_count or 0),
                )
            )
            await session.commit()
        return {"recorded": True}
    except Exception as exc:
        logger.warning(
            "telemetry.record_bot_search_query_failed: %s", exc, exc_info=True
        )
        return {"recorded": False, "error": str(exc)}


def enqueue_search_query(
    *,
    user_telegram_id: Optional[int],
    source: str,
    raw_text: str,
    extracted_fields: List[str],
    results_count: int,
) -> None:
    """Fire-and-forget enqueue of a search-telemetry row.

    Swallows broker errors (Celery ``.delay`` can raise if the broker is
    momentarily unreachable) so a telemetry hiccup never breaks the
    user's search reply. The capture is best-effort by design.
    """
    try:
        record_bot_search_query.delay(
            user_telegram_id,
            source,
            raw_text,
            list(extracted_fields or []),
            results_count,
        )
    except Exception:
        logger.warning("telemetry.enqueue_search_query_failed", exc_info=True)
