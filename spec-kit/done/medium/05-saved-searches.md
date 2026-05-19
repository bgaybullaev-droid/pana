# 05 — Saved Searches (Ф-68 / Ф-69)

**Status:** DONE
**Complexity:** MEDIUM — CRUD + matcher service + last_seen counter; clean boundaries but the matcher integrates with the notification fanout.

## Summary

Buyers persist a search filter set as a `SavedSearch` row. Each saved search has `notify_enabled` toggle. When a new listing is created or imported, the notification fanout (see [06-notifications](../hard/06-notifications.md)) runs every saved search through a matcher; any hit produces a "Qidiruvingizga yangi e'lon" / "Новое по вашему поиску" notification. The Favorites page surfaces saved searches as a dedicated tab with an unread-count badge.

## Data model

`backend/app/db/models.py` — `SavedSearch`.

| Column | Notes |
|---|---|
| `id` | UUID. |
| `user_id` | FK CASCADE. |
| `name` | Optional human label. |
| `query` | Optional free-text token. |
| `filters` | JSONB. Hydrated into `ListingFilters` by `_filters_to_listing_filters`. |
| `notify_enabled` | Bool. False disables matching for this search. |
| `last_seen_at` | Updated when the user opens the saved-search results page; drives the unread-count badge. |
| `created_at`, `updated_at` | Lifecycle. |

`backend/alembic/versions/20260424_prb_saved_searches_schema.py` is the additive migration that introduced the current shape.

## API surface

`backend/app/api/v1/saved_searches.py`.

| Verb | Path | Purpose |
|---|---|---|
| GET | `/saved-searches` | Lists current user's saved searches with derived `new_count` (matched listings since `last_seen_at`). |
| POST | `/saved-searches` | Create with `{name, filters, notify_enabled}`. |
| PATCH | `/saved-searches/{id}` | Rename, toggle `notify_enabled`, edit `filters`. |
| DELETE | `/saved-searches/{id}` | Hard delete. |
| POST | `/saved-searches/{id}/seen` | Update `last_seen_at = datetime.now()` (DB-local time to match `func.now()` semantics). |

## Matcher

`backend/app/services/saved_search_matcher.py` — `_match_listing_to_filters(listing, filters)` runs the same filter logic the public feed uses. Returns bool.

Used from `_match_saved_searches` in the notification fanout (see [06-notifications](../hard/06-notifications.md)).

## Behaviour & invariants

- **`last_seen_at`** is stored as DB-naive Tashkent time so it compares cleanly with `Notification.created_at` (also naive Tashkent) when computing `new_count`.
- **Filter shape** — JSONB. Schema is `ListingFilters` Pydantic model. Hydration is lossy on unknown keys (forward-compat).
- **Search ownership** — endpoints scope by `current_user.id`; cross-user reads return 404.
- **Notification dispatch** — saved-search hits are notified by the saved-search **stage** of the fanout, which is gated by `prefs.paused` and `_is_within_time_window` for Telegram delivery. In-app rows are always written. See [06-notifications](../hard/06-notifications.md) for the full state machine.

## Frontend

`frontend/src/modules/buyer/pages/favorites/` — second tab is saved searches; cards show `new_count` and link to a results page that calls `/saved-searches/{id}/seen` on mount.

Card component: `frontend/src/modules/buyer/pages/favorites/ui/main/SavedSearchCard.tsx`.

## References

- `backend/app/api/v1/saved_searches.py`
- `backend/app/services/saved_search_matcher.py`
- `backend/alembic/versions/20260424_prb_saved_searches_schema.py`
- `frontend/src/modules/buyer/pages/favorites/`

## Known gaps

- None for the saved-search domain itself. Adjacent gaps live in [06-notifications](../hard/06-notifications.md) (e.g., paused gating semantics).
