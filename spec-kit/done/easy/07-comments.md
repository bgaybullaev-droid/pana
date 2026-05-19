# 07 — Comments

**Status:** DONE
**Complexity:** EASY — single table with self-FK, listing-scoped routes, like / unlike toggle via two endpoints; no edit, no soft-delete, no cross-cutting invariants.

## Summary

Threaded comments under listings with one level of replies. Authors can like / unlike. The listing seller and the parent author receive in-app notifications when a new comment or reply lands. Comments are hard-deleted by their author; there is no edit endpoint and no soft-delete column today.

## Data model

`backend/app/db/models.py:733` — `Comment`.

| Column | Notes |
|---|---|
| `id` | UUID PK. |
| `listing_id` | UUID, indexed; **no FK** (listings can come from main / Telegram / OLX sources). |
| `user_id` | FK CASCADE. |
| `parent_id` | UUID self-FK. NULL for top-level. |
| `text` | Required text body. |
| `replies_count`, `likes_count` | Counters maintained by the routes (not via DB triggers). |
| `created_at`, `updated_at` | Lifecycle. |

`Listing.comments_count` mirrors top-level comment count for the listing and is updated on create / delete.

`CommentLike` (`backend/app/db/models.py:790`) — M2M between comment and user.

## API surface

`backend/app/api/v1/comments.py` — six endpoints, all listing-scoped.

| Verb | Path | Purpose |
|---|---|---|
| GET | `/listings/{listing_id}/comments` | Paginated top-level comments (`parent_id IS NULL`). |
| GET | `/listings/{listing_id}/comments/{comment_id}/replies` | Paginated replies for one comment. |
| POST | `/listings/{listing_id}/comments` | Body `{text, parent_id?}`. Create top-level or reply. |
| DELETE | `/listings/{listing_id}/comments/{comment_id}` | Hard delete. Author-only. Decrements `Listing.comments_count` and parent's `replies_count`. |
| POST | `/listings/{listing_id}/comments/{comment_id}/like` | Inserts `CommentLike` + increments `likes_count`. Idempotent. |
| DELETE | `/listings/{listing_id}/comments/{comment_id}/like` | Removes like + decrements counter. |

**No edit endpoint** — `text` is immutable after creation.

## Behaviour & invariants

- **Listing-source neutrality** — `find_listing_any_source(db, listing_id)` resolves Listing / TelegramListing / OLXListing so users can comment on crawled listings too.
- **One reply level** — enforced by the UI; the API does not validate `parent.parent_id IS NULL` server-side, so a malformed client could post a reply-to-a-reply (it would be invisible in the renderer).
- **Hard delete** — there is no `is_deleted` column. Deleting a parent leaves orphan replies; the frontend hides orphan branches but the data layer does not cascade.
- **Notifications fire end-to-end** — the create handler dispatches `NotificationType.COMMENT_REPLY` to the parent author (skipping self-reply) and `NotificationType.NEW_COMMENT` to the listing seller. Both are written as `Notification` rows via the standard pipeline ([06-notifications](../hard/06-notifications.md)).
- **Author identity in responses** — only `user_id`, `first_name`, `username`, `avatar_url` surface; phone / email never leak.

## Frontend

`frontend/src/modules/buyer/pages/listing-detail/ui/main/CommentItem.tsx` plus the parent component renders top-level comments and lazy-loads replies via `/replies`.

## References

- `backend/app/api/v1/comments.py` — entire router.
- `backend/app/db/models.py:733` — `Comment`.
- `backend/app/db/models.py:790` — `CommentLike`.
- `frontend/src/modules/buyer/pages/listing-detail/`

## Known gaps

- **No author edit.** Once posted, a comment's text is immutable. A PATCH endpoint would be a small additive change if "edit within N minutes" is wanted.
- **No soft-delete.** Threads collapse around deleted parents. Adding `is_deleted` + content placeholder would preserve thread shape — separate spec if product asks.

These are deliberate omissions from the current shipped surface, not regressions — model and routes match each other.
