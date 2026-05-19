# 16 — Promotion Services (Boost / Badge / Notify-Priority)

**Status:** NOT STARTED (only `Listing.is_boosted` flag exists)
**Complexity:** MEDIUM — three independent services tied to the wallet (dependency); each individually small, the trio adds up to a sprint.
**Vision-doc refs:** §7.4
**Why now:** Phase 2. Activates with monetisation. Depends on [`F113-wallet`](../hard/F113-wallet.md).

## Goal

Three discrete one-off services per the vision doc:

| Service | Price | Effect |
|---|---|---|
| Поднятие в топ | 15 000 sum / listing / 7 days | Bumps listing to top of feed for 7 days. |
| Выделение (badge "Срочно") | 10 000 sum / listing | Coloured badge on the card; no time limit. |
| Приоритет в уведомлениях | 20 000 sum / listing / 7 days | Listing wins ties when matching saved searches / preferences (delivered first, marked as "premium" in notifications). |
| Banner (manager-only) | Phase 3 | See [`F118-banner-ads`](F118-banner-ads.md). |

## What's done

- `Listing.is_boosted: bool` and `Listing.boost_until: datetime` columns exist.
- Feed query already orders by `is_boosted DESC`.
- No purchase flow, no badge, no notify-priority.

## Proposed data model

Reuse `Listing.boost_until` for "Поднятие в топ".
Add:

| Column | Notes |
|---|---|
| `Listing.has_urgent_badge` | Bool, default false. "Выделение" toggle. |
| `Listing.notify_priority_until` | Timestamp, nullable. "Приоритет в уведомлениях" expiry. |

Or — to avoid bloating `Listing` further — a satellite `ListingPromotion` table with rows per active promotion (one row per (listing × kind)). Recommended satellite for cleanness.

## Proposed API surface

| Verb | Path | Purpose |
|---|---|---|
| POST | `/listings/{id}/promotions/boost` | `{}`. Spends 15 000 sum, sets `boost_until = now() + 7 days`. |
| POST | `/listings/{id}/promotions/urgent` | Spends 10 000 sum, sets `has_urgent_badge = true`. |
| POST | `/listings/{id}/promotions/notify-priority` | Spends 20 000 sum, sets `notify_priority_until = now() + 7 days`. |
| DELETE | `/listings/{id}/promotions/{kind}` | Cancel (no refund unless within 1 hour and untouched). |

Each handler calls `wallet.spend(...)` first; on success applies the listing change. Atomic.

## Behaviour & invariants

- **Stacking** — all three are independent; a listing can have all three at once.
- **Boost ordering** — feed ORDER BY: `is_boosted DESC` (already there) THEN claimed THEN created_at. See [`F108-master-record-ranking`](../../partial/easy/F108-master-record-ranking.md).
- **Notify priority** — in `_match_and_notify` and `_match_saved_searches`, if multiple listings match the same user in a single fanout window, dispatch `notify_priority` ones first. Mark with a 🚀 emoji in the message.
- **Urgent badge** — pure UI; renders in the card.
- **Expiry** — celery beat job at hourly cadence resets `boost_until <= now()` and `notify_priority_until <= now()` to past.

## Frontend

- Listing detail in seller cabinet → "Продвинуть" panel with three cards (boost / badge / priority) showing price and current state (active / not).
- Public card → renders `🚀 В топе` strip when `is_boosted=true and boost_until > now()`, urgent badge when set.

## Acceptance criteria

- Each of the three promotions can be purchased by a seller with sufficient balance.
- Insufficient balance → InsufficientFundsError → modal prompts top-up.
- Feed reflects boosted ordering immediately.
- Notifications mark and prioritise notify-priority listings.
- Expiry job runs and clears expired flags.
