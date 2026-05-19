# 06 — Notification System (Ф-76 / Ф-79 / Ф-80)

**Status:** DONE — was the focus of the most recent work.
**Complexity:** HARD — two-stage fanout, three orthogonal gates (paused / time window / daily limit) with per-stage rules, source-tagging contract, structured per-user skip/send logs, and frontend grouping logic.

**Vision-doc refs:** Section 4 ("Умные уведомления"), Ф-76 (smart matcher), Ф-79 (daily limit), Ф-80 (time window).

## Summary

A new listing fans out through two independent matching stages, each with its own gating rules:

1. **Saved-search stage** — matches the listing against every `SavedSearch` with `notify_enabled=true`. Honours `prefs.paused` and `_is_within_time_window` for Telegram delivery. In-app row always written for matches. Title: "Новое по вашему поиску" / "Qidiruvingizga yangi e'lon".
2. **Preferences stage** — matches against `NotificationPreferences` filters (listing_types, property_types, districts, price range, rooms). Telegram fires regardless of paused / time-window — only the daily Redis cap applies. Title: "Новое объявление" / "Yangi e'lon".

Notifications carry an explicit `source` discriminator (`"saved_search"` | `"preferences"`) so the frontend never has to parse titles.

## Data model

`backend/app/db/models.py`:

- `NotificationPreferences` (line ~895) — `paused`, `enabled` (legacy), `daily_limit`, `time_start`, `time_end`, `timezone`, `disabled_types[]`, `listing_types[]`, `property_types[]`, `districts[]`, `price_min`, `price_max`, `rooms[]`, `source_saved_searches`, `source_seller_follows`, `source_ai_recs`.
- `Notification` (line 1025) — `id`, `user_id`, `type` (enum incl. `NEW_LISTING`, `PRICE_DROP`, `COMMENT_REPLY`, `LISTING_APPROVED`, `LISTING_REJECTED`, etc.), **`source: VARCHAR(32)`** (added in `backend/alembic/versions/20260425_prc_notification_source.py`), `title`, `message`, `listing_id`, `comment_id`, `actor_id`, `read`, `created_at`.

## API surface

`backend/app/api/v1/notifications.py` and `backend/app/api/v1/notification_settings.py`.

| Verb | Path | Purpose |
|---|---|---|
| GET | `/notifications` | Paginated list, ordered by `created_at DESC`. Builds `NotificationResponse` with back-filled `source` for legacy NULL rows. |
| GET | `/notifications/unread-count` | Badge integer. |
| POST | `/notifications/read` | Mark all (no body) or specific ids. |
| GET | `/notification-settings` | Frontend-facing wrapper. |
| PUT | `/notification-settings` | Update; also syncs legacy `enabled = NOT paused`. |
| GET | `/notifications/preferences` | Filter-prefs (separate from settings UI). |
| PUT | `/notifications/preferences` | Filter-prefs update. |

## Background tasks

`backend/app/workers/tasks/notifications.py`:

- `send_new_listing_notifications(listing_id)` — orchestrator. Calls `_match_saved_searches` then `_match_and_notify`.
- `_match_saved_searches(...)` — saved-search stage.
- `_match_and_notify(...)` — preferences stage. Now writes `source="preferences"` and emits per-user **rejection logs** explaining why each non-matching user with prefs was excluded (`district_mismatch(qibray not in [...])`, `property_type_mismatch`, `price_above_max`, etc.).
- `send_telegram_notification(user_telegram_id, message, parse_mode)` — fire-and-forget Telegram delivery.
- `_check_and_increment_daily_limit(redis, user_id, daily_limit, today_str)` — atomic INCR + EXPIRE.
- `_is_within_time_window(prefs)` — uses `prefs.timezone` (default Asia/Tashkent).

Triggered from `POST /listings` after the row commits, via `send_new_listing_notifications.delay(...)`.

## Behaviour & invariants

- **Cross-stage independence** — a user can receive **both** a saved-search and a preferences notification for the same listing (in-app and Telegram). This is product-required.
- **Saved-search Telegram gates** — `not user.telegram_id` → skip with `reason=no_telegram_id`; `prefs.paused` → skip with `reason=paused`; `not _is_within_time_window` → skip with `reason=time_window`. Otherwise dispatch + log `tg-sent`.
- **Preferences Telegram gates** — only `not user.telegram_id` and daily-limit. Time window does NOT apply (preferences are "always on" per product).
- **Daily limit** — Redis key `notif_daily:<user_id>:<YYYY-MM-DD>`, TTL 86400. Both stages share the same counter.
- **Source field** — written on creation. Legacy NULL rows are back-filled in `build_notification_response` via title heuristic ("поиску" / "Qidiruv" → `saved_search`, else `preferences`) so the frontend always sees a non-null source.
- **Datetime semantics** — `created_at` is naive Tashkent, serialised as UTC-with-`Z` via the `UTCDateTime` Pydantic annotated type. See [12-utc-serialization](../easy/12-utc-serialization.md).
- **Match transparency** — every skip / send path emits a structured log line (`saved-search skip user=… listing=… reason=…`, `prefs reject … reason=…`). Greppable for ops.

## Frontend

`frontend/src/modules/buyer/pages/notifications/ui/page/Page.tsx`:

- Date grouping (`Сегодня` / `Вчера` / `Ранее`) keyed off `created_at`.
- Per-row icon + colour are picked from `notification.type`.
- For `type=new_listing`, the explicit `notification.source` controls the label (`По вашему поиску` purple / `По вашим фильтрам` orange) and icon override (search icon for saved-search). **No title parsing.**

`frontend/src/modules/buyer/pages/notification-settings/` — UI for paused, daily limit, time windows, source toggles.

i18n keys: `notifications.sourceSavedSearch`, `notifications.sourcePreferences` (ru + uz).

## References

- `backend/app/workers/tasks/notifications.py` — fanout, both stages.
- `backend/app/api/v1/notifications.py` — list / read endpoints + `build_notification_response`.
- `backend/app/api/v1/notification_settings.py` — settings wrapper.
- `backend/alembic/versions/20260423_pra_notification_settings.py` — paused / time_windows / source_* columns.
- `backend/alembic/versions/20260425_prc_notification_source.py` — `notifications.source` column.
- `frontend/src/modules/buyer/pages/notifications/ui/page/Page.tsx`
- `frontend/src/shared/api/types.ts` — `NotificationSource = "saved_search" | "preferences"`.

## Known gaps

- **Ф-107 seller-side notifications** (when a new crawled listing matches a registered seller's phone) — not yet wired. See `../../not-started/medium/F107-seller-claim-notification.md`.
- Inline keyboard buttons under Telegram notifications ("В избранное", "Написать продавцу") are not attached. See `../../not-started/medium/notification-inline-keyboards.md`.
