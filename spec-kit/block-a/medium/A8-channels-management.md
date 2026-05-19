# A8 — Telegram channel list management

**Status:** PARTIAL — config-driven channel loading works; failure isolation works; admin CRUD, per-source metadata, and per-source metrics are absent; current count is 14, target 25+.
**Complexity:** MEDIUM — three small sub-deliverables (admin CRUD, metadata schema, metrics aggregation). Each is bounded; together they are a one-developer-week's worth of work.
**Block-A V2.0 ref:** A8 (Section "A8. Расширение списка Telegram-каналов для парсинга").
**Why now:** Channel coverage is the lever for the "весь рынок Ташкента в одном месте" promise. The operational expansion (founder picks channels via tgstat.ru) needs an interface; without one each new channel requires a code edit + restart.

## What's done

- **YAML-driven discovery** — `telegram-ai/crawler/schema_loader.py:27-49` auto-loads every `.yaml` in `telegram-ai/crawler/schemas/`. Channels are defined in `schemas/real_estate.yaml` under `channels:`. Adding a channel to that file is enough; no Python edit required.
- **14 active channels** in `real_estate.yaml`: `baburieltor, realtor_alii, Kvartira_doma_Tashkent, Nedvijimosss, realtor_yunusov, grandestate2019, RealestTash, vitrinanedvizhimosti, arentash, UyCharxiy9, Imkonuyjoysavdoo, ANDIJON_UYJOY, NAMANGAN_UYJOY_BOZORI, testReiltor`.
- **`channels_config.yaml` whitelist mode (lines 12-18)** lists 5 test channels but is overridden by schema-driven discovery in production.
- **Failure isolation** — `FlexibleCrawlerWithHistory.py:267-302` wraps each channel in try/except; one channel going private/private/deleted does not stop the others. Realtime handler at line 330 isolates per-message errors.
- **Source field on import** — `backend_push.py:78` sends `source_channel` so backend can attribute per-listing origin.

## What's missing

1. **No admin endpoint or UI for channels.** Adding a channel requires editing `real_estate.yaml` on the crawler host and restarting. There is no `/admin/sources` route, no admin page under `frontend/src/modules/admin/pages/`.
2. **Per-channel metadata is just a username.** Spec requires display name, status (`active` / `paused` / `unavailable`), date added, possibly priority. None of these exist.
3. **No metrics persistence.** Per-channel extraction success rate is printed to stdout (`FlexibleCrawlerWithHistory.py:304-310`) but never stored. There is no `source_metrics` table, no `/admin/sources/stats` endpoint, no admin dashboard view.
4. **No deviation alert.** Spec calls for "if extraction success drops below threshold, notify admin". Without metrics persistence there is nothing to alert on.
5. **Rate-limit handling is minimal.** `FlexibleCrawlerWithHistory.py:298` does `await asyncio.sleep(1)` between messages. No explicit `FloodWaitError` handler, no exponential backoff. Telethon's library-level retry is there but not customised. For 14 channels the current sleep is fine; for 25+ it may not be.
6. **AI-generation per-source feedback** is referenced by the spec ("source's `% with 'не нравится текст'`") but depends on F1 + F5 to exist; not actionable until F1 lands ([A7](../hard/A7-parser-f1-trigger.md)).
7. **Operational expansion is not engineering.** Reaching 25+ channels is a founder task driven by tgstat.ru — see Block E. This spec only covers what code/UI must exist to support that work.

## Path to DONE

1. **Move channels to a DB table** — `parser_source(id, kind, username, display_name, status, added_at, added_by_user_id, priority)` with `kind ∈ ('telegram','olx')`. Migration adds the table + seeds it from current `real_estate.yaml`.
2. **Crawler reads from DB instead of YAML.** `schema_loader.py` (or its replacement) queries the table on startup, refreshes on a cron tick (every 10 min) so admin edits propagate without a restart. Keep YAML as a fallback for offline dev.
3. **Admin API** — `backend/app/api/v1/admin_sources.py`:
    - `GET /admin/sources` — list with metadata + last-7-day stats (joins source_metrics).
    - `POST /admin/sources` — add channel.
    - `PATCH /admin/sources/{id}` — update status / priority / display_name.
    - `DELETE /admin/sources/{id}` — soft-delete (status='archived').
    Permission: admin role only; mirror the patterns in existing `backend/app/api/v1/admin*` modules.
4. **Admin frontend** — `frontend/src/modules/admin/pages/sources/` (new page following the existing `users/` and `crawled/` shape). Lists channels with status badge, last-7d listings extracted, last-7d extraction-success %, action buttons.
5. **Metrics table** — `source_metric(source_id, day, listings_found, listings_extracted, listings_failed, dupes_filtered)`. Crawler writes one row per source per day, upsert. Optional view layer: `source_metric_7d` aggregates the last 7 rows per source for the dashboard.
6. **Crawler writes metrics.** Where `FlexibleCrawlerWithHistory.py:304-310` currently prints, add a backend POST to `/crawler/source-metric` (admin-only ingest). Same auth as the existing `/crawler/import/*`.
7. **Threshold alert** — Celery beat job daily: for each source, if `extracted/found < 0.5 * trailing_30d_mean`, write a `Notification` to admin users with `source=admin_alert`. Reuse the existing notification fanout.
8. **Rate-limit polish** — replace `await asyncio.sleep(1)` with a per-channel token bucket (one token per second per channel, library-aware backoff on `FloodWaitError`). Acceptable to defer until 25+ channels are live and a problem is observed.
9. **AI-quality per source** — empty placeholder field on `source_metric` (e.g. `ai_failure_rate`). Populated by F1/F5 once they exist. No work until then.

## Behaviour & invariants

- **Adding a channel via admin UI does not require code deploy** — the live crawler picks up the change on its next refresh tick.
- **Disabling a channel via admin UI** stops new captures within the next tick; existing listings stay (status only affects ingest, not historical data).
- **Deleted/private channel ⇒ status auto-flips to `unavailable`** by the crawler, but the row stays. Admin sees the flip in the dashboard.
- **Public channels only.** No invite-link channels, no closed groups. Validation at admin POST: reject if Telethon resolution requires an invite.
- **Rate-limit FloodWait is per-channel and exponential.** A 24h FloodWait on one channel does not stop others.
- **Metrics writes are best-effort** — crawler does not block on metric POST failure.

## Acceptance criteria

- Admin can add a channel via the UI; within ≤ 10 minutes the crawler is fetching from it without a restart.
- Admin can pause/unpause a channel; the crawler honours the change on the next tick.
- Admin dashboard shows, per source: status, listings extracted last 7 days, extraction success %.
- Bot-blocked / private channel ⇒ status flips to `unavailable` automatically; row remains.
- Crawler completes a full pass without a single Python-level KeyError / IndexError when one channel goes 404.
- (Operational, not engineering) `parser_source` table contains 25 or more `status='active'` rows.
- (After F1) Per-source AI-quality column populated.

## References

- `telegram-ai/crawler/schemas/real_estate.yaml` — current source list (14 channels) + extraction schema.
- `telegram-ai/crawler/schema_loader.py:27-49` — YAML loader (replace with DB read).
- `telegram-ai/crawler/FlexibleCrawlerWithHistory.py:267-330` — crawl loop, failure isolation, where metric writes go.
- `telegram-ai/crawler/backend_push.py:44-206` — push to backend (already includes source field).
- `frontend/src/modules/admin/pages/users/`, `frontend/src/modules/admin/pages/crawled/` — patterns to follow for the new sources/ page.
- [Block E1] (out of repo) — operational channel-discovery process via tgstat.ru.
- [A7](../hard/A7-parser-f1-trigger.md) — per-source AI-quality metrics depend on F1.
