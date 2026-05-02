"""PR10 — Read-path backend dispatcher.

Chooses between Postgres (source of truth) and Meilisearch (performance
layer) based on `settings.search_backend`. On ANY Meili failure — missing
client, network error, bad filter expression, unexpected result shape —
the router falls back to Postgres silently. The buyer never sees a 5xx
from this layer.

Public API:
    async def get_listings(filters, db_session, page, per_page,
                           current_user, postgres_runner) -> PaginatedResponse
    async def get_facets(filters, db_session, postgres_runner) -> dict

The callers (list_listings / list_facets in the API layer) pass their
own Postgres "runner" closures. That keeps this module free of the
response-building glue (which needs image URLs, favorites, multilingual
field resolution, etc.) and free of imports from app.api.v1.listings,
avoiding a circular import.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable

from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_listings(
    filters,
    db_session,
    page: int,
    per_page: int,
    current_user,
    postgres_runner: Callable[..., Awaitable],
):
    """Route the listings read. Falls back to Postgres on any Meili error.

    Shape of the return value is whatever `postgres_runner` returns (a
    PaginatedResponse[ListingListResponse]). When the Meili path
    succeeds, we still load the full listing rows from Postgres using
    the Meili-returned id list, preserving the rank order — this keeps
    the response schema byte-identical to the Postgres-only path.
    """
    if settings.search_backend == "meili":
        try:
            # Local import keeps the router importable without Meili at
            # process start; any exception here (incl. ImportError /
            # network / bad-filter) hits the fallback.
            from app.services.search_index import search_listings_in_meili

            ids, total = search_listings_in_meili(filters, page, per_page)
            return await postgres_runner(
                filters=filters,
                db_session=db_session,
                page=page,
                per_page=per_page,
                current_user=current_user,
                # Precomputed Meili hits — tells the PG runner to fetch
                # only these IDs in rank order instead of running
                # _apply_filters against the DB.
                meili_ids=ids,
                meili_total=total,
            )
        except Exception as exc:
            logger.warning("meili listings failed, falling back to postgres: %s", exc)
    # Postgres-only path (default, or Meili fallback).
    return await postgres_runner(
        filters=filters,
        db_session=db_session,
        page=page,
        per_page=per_page,
        current_user=current_user,
        meili_ids=None,
        meili_total=None,
    )


async def get_facets(
    filters,
    db_session,
    postgres_runner: Callable[..., Awaitable],
):
    """Route the facets read. Falls back to Postgres on any Meili error.

    When Meili succeeds, we return its facet distribution directly — the
    shape already matches FacetsResponse (see
    search_facets_in_meili()).  When it fails we defer to the caller's
    `postgres_runner` which rebuilds the dict from SQL aggregates.
    """
    if settings.search_backend == "meili":
        try:
            from app.services.search_index import search_facets_in_meili

            result = search_facets_in_meili(filters)
            # Sanity: `result` must be a dict. Anything else → fallback.
            if not isinstance(result, dict):
                raise RuntimeError(
                    f"meili facets returned {type(result).__name__}, expected dict"
                )
            return result
        except Exception as exc:
            logger.warning("meili facets failed, falling back to postgres: %s", exc)
    return await postgres_runner(filters=filters, db_session=db_session)
