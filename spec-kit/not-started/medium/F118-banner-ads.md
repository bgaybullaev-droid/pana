# 18 — Banner Ads (Ф-118)

**Status:** NOT STARTED
**Complexity:** MEDIUM — new schema + admin CRUD + impression / click tracking + frontend slot rotation; no exotic mechanics.
**Vision-doc refs:** §9 Phase 3, §7.4 (manager-managed service)
**Why now:** Phase 3. Premium ad inventory for big developers / banks. Defer until Phase 2 monetisation has proven; this is incremental revenue, not foundational.

## Goal

A configurable banner slot at the top of the home feed (Krutilka). Sold manually by sales team in Phase 3 — no self-serve initially.

## Proposed data model

`Banner`:

| Column | Notes |
|---|---|
| `id` | UUID. |
| `image_url` | Hosted image (S3 or local uploads). |
| `link_url` | Where the banner navigates on tap. Could be an internal listing/seller, an external URL, or a Mini App route. |
| `title`, `subtitle` | Optional overlay. |
| `target_audience` | JSONB filter. Initially: `{"district": "...", "language": "..."}`. |
| `start_at`, `end_at` | Time window. |
| `priority` | Int. Higher wins ties when multiple banners match. |
| `impressions_count`, `clicks_count` | Counters. |
| `created_by_admin_id` | Audit. |
| `created_at`, `updated_at` | Lifecycle. |

## API surface

| Verb | Path | Purpose |
|---|---|---|
| GET | `/banners/active` | Returns the active banner for the current user (matched against `target_audience`). Public. |
| GET | `/admin/banners` | Admin list. |
| POST | `/admin/banners` | Create. |
| PATCH | `/admin/banners/{id}` | Edit. |
| DELETE | `/admin/banners/{id}` | Soft delete. |
| POST | `/banners/{id}/impression` | Anonymous impression count. |
| POST | `/banners/{id}/click` | Anonymous click count. |

## Frontend

Home feed top — when an active banner is returned, render a swipeable card before the regular feed. Long-press to dismiss for the session.

## Behaviour & invariants

- **One banner at a time per user** — backend resolves the highest-priority match for the requesting user's locale + district.
- **Time-windowed** — outside `[start_at, end_at]` the banner doesn't render even if matched.
- **No data leakage** — tracking is anonymous; no per-user impression history.

## Acceptance criteria

- Admin can create / edit / delete banners.
- Active banner matching user's locale/district appears at top of feed.
- Tapping it navigates to `link_url` and increments `clicks_count`.
- Impression count increments on render (debounced one impression per user-session).

## Open questions

- Frequency cap (don't show same banner more than 3× to one user) — Phase 3.5.
- A/B testing — Phase 3.5.
