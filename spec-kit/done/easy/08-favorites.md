# 08 — Favorites

**Status:** DONE
**Complexity:** EASY — M2M with unique constraint, two-tab UI; no FK on listing_id by design — only thing to remember is uniqueness.

## Summary

A user can favourite a listing. The favourites page has two tabs: **listings** (saved listing cards) and **searches** (saved searches with unread-count badges).

## Data model

`backend/app/db/models.py:700` — `Favorite`.

| Column | Notes |
|---|---|
| `id` | UUID. |
| `user_id` | FK CASCADE. |
| `listing_id` | UUID; **no FK** — favourites can reference listings from any source (main, telegram, olx). |
| `created_at` | Timestamp. |

Unique constraint `uq_user_listing_favorite` on `(user_id, listing_id)`.

## API surface

`backend/app/api/v1/favorites.py`.

| Verb | Path | Purpose |
|---|---|---|
| GET | `/favorites` | Paginated favourite listings (joined to Listing). |
| GET | `/favorites/ids` | Just the listing-id set — used by feed cards to render the heart filled. |
| POST | `/favorites` | `{listing_id}`. Idempotent. |
| DELETE | `/favorites/{listing_id}` | Idempotent unfavourite. |

## Behaviour & invariants

- **No FK on `listing_id`** is intentional — a favourite can survive its source listing being archived or deleted; the UI shows a placeholder card.
- **Unique constraint** prevents double-add.
- **Two tabs in UI** — listings tab uses `/favorites`; searches tab uses `/saved-searches` (see [05-saved-searches](../medium/05-saved-searches.md)).

## Frontend

`frontend/src/modules/buyer/pages/favorites/ui/page/Page.tsx` — Mantine `Tabs` with i18n keys `tabListings` / `tabSearches`.

## References

- `backend/app/api/v1/favorites.py`
- `backend/app/db/models.py:700`
- `frontend/src/modules/buyer/pages/favorites/`
