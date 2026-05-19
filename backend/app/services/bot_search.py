"""Block D V2.0 (D5) — Meilisearch executor for bot-side search.

Maps :class:`ParsedQuery` → Meilisearch query → :class:`BotSearchResult`
list. No DB roundtrip in the hot path: Meilisearch holds enough fields
for the result card (title, district, price, currency, rooms, photo
URL) so the bot can render results without loading the full Listing.

Per Block D guardrails:

- **No caching layer.** Meilisearch is already a fast read store
  (<50 ms p95). Add Redis only if profiling shows we exceed budget.
- **No N+1.** One Meilisearch call returns up to N results plus the
  fields needed for rendering — `attributesToRetrieve` is the
  explicit allow-list.
- **Domain returns domain objects.** :class:`BotSearchResult` is a
  plain dataclass; ``bot/inline.py`` adapts it to aiogram types.
- **Graceful degradation.** Meilisearch failures surface as an empty
  list + a logged warning; callers show a friendly fallback message.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional

from app.services.query_parser import ParsedQuery
from app.services.search_index import ensure_index_exists

logger = logging.getLogger(__name__)

# Cap on results returned to the caller. Bot in-chat search shows
# 5–10 (DECISION_MATRIX D5-Q6); Inline Mode shows up to 20 (D5 spec).
DEFAULT_BOT_LIMIT = 10
DEFAULT_INLINE_LIMIT = 20

# Fields we need to render a compact result card. Asking Meilisearch for
# only these keeps the response payload small and avoids accidentally
# leaning on schema fields that may not exist in older index versions.
_RESULT_FIELDS = (
    "id",
    "title",
    "district",
    "region",
    "rooms",
    "area",
    "price",
    "currency",
    "type",
    "property_type",
    "photo_url",
)


@dataclass(frozen=True)
class BotSearchResult:
    """One row in the bot's search result list."""

    id: str
    title: Optional[str] = None
    district: Optional[str] = None
    rooms: Optional[int] = None
    area: Optional[float] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    deal_type: Optional[str] = None        # mirrors Meili "type" field
    property_type: Optional[str] = None
    photo_url: Optional[str] = None


def _build_filter_expression(parsed: ParsedQuery) -> Optional[str]:
    """Translate :class:`ParsedQuery` into Meilisearch filter syntax.

    Returns ``None`` when no filter applies — Meilisearch handles a
    bare-search-string query without a filter clause.
    """
    clauses: list[str] = []
    if parsed.district:
        # district is stored as the canonical key in the index.
        clauses.append(f'district = "{parsed.district}"')
    if parsed.deal_type:
        clauses.append(f'type = "{parsed.deal_type}"')
    if parsed.property_type:
        clauses.append(f'property_type = "{parsed.property_type}"')
    if parsed.rooms_min is not None:
        clauses.append(f"rooms >= {parsed.rooms_min}")
    if parsed.rooms_max is not None:
        clauses.append(f"rooms <= {parsed.rooms_max}")
    if parsed.price_min is not None:
        clauses.append(f"price >= {parsed.price_min}")
    if parsed.price_max is not None:
        clauses.append(f"price <= {parsed.price_max}")

    if not clauses:
        return None
    return " AND ".join(clauses)


def _hit_to_result(hit: dict) -> Optional[BotSearchResult]:
    """Best-effort projection from a Meilisearch hit dict.

    Tolerant of missing fields — the index has evolved over time and
    older docs may not have every column. ``id`` is required;
    everything else is optional.
    """
    if not isinstance(hit, dict):
        return None
    listing_id = hit.get("id")
    if not listing_id:
        return None
    return BotSearchResult(
        id=str(listing_id),
        title=hit.get("title"),
        district=hit.get("district"),
        rooms=hit.get("rooms"),
        area=hit.get("area"),
        price=hit.get("price"),
        currency=hit.get("currency"),
        deal_type=hit.get("type"),
        property_type=hit.get("property_type"),
        photo_url=hit.get("photo_url"),
    )


def search(
    parsed: ParsedQuery,
    *,
    limit: int = DEFAULT_BOT_LIMIT,
) -> list[BotSearchResult]:
    """Run a search and return up to ``limit`` result cards.

    Sorts: relevance first (Meilisearch default), then most recent. The
    caller can sort/filter further if needed; we do not paginate.
    """
    index = ensure_index_exists()
    if index is None:
        logger.warning("bot_search: Meilisearch unavailable")
        return []

    expr = _build_filter_expression(parsed)
    # The free-text part — if the user typed a landmark or street name
    # that the parser didn't pick up (e.g. "Амира Темура"), let
    # Meilisearch fuzzy-match it against searchable attributes.
    fts = (parsed.raw_text or "").strip()
    # If we extracted any filter, drop the FTS query so the user's
    # typed filter words ("Чиланзар", "2-комн", "до 35тыс") don't
    # double-count as text matches and skew relevance.
    if parsed.extracted_fields:
        fts = ""

    try:
        resp = index.search(
            fts,
            {
                "filter": expr,
                "sort": ["created_at:desc"],
                "limit": max(1, min(int(limit), DEFAULT_INLINE_LIMIT)),
                "attributesToRetrieve": list(_RESULT_FIELDS),
            },
        )
    except Exception as exc:
        logger.warning("bot_search: Meilisearch query failed: %s", exc)
        return []

    hits = resp.get("hits", []) if isinstance(resp, dict) else []
    results: list[BotSearchResult] = []
    for hit in hits:
        row = _hit_to_result(hit)
        if row is not None:
            results.append(row)
    return results


def recent_listings(limit: int = DEFAULT_INLINE_LIMIT) -> list[BotSearchResult]:
    """Empty-query fallback for Inline Mode: most-recent listings.

    Same projection as :func:`search`; no filter applied. ``limit``
    capped at ``DEFAULT_INLINE_LIMIT`` for safety.
    """
    return search(ParsedQuery(raw_text=""), limit=limit)


__all__ = (
    "BotSearchResult",
    "search",
    "recent_listings",
    "DEFAULT_BOT_LIMIT",
    "DEFAULT_INLINE_LIMIT",
)
