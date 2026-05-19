# UcharMarket Spec Kit

Source-of-truth specs for what the platform does, organised on **two strict axes**:

```
spec-kit/
├── done/             — fully implemented (truth of what exists)
│   ├── easy/         — small, well-bounded, junior-friendly
│   ├── medium/       — multi-component, mid-level
│   └── hard/         — broad surface or subtle invariants, senior-led
├── partial/          — half-built (truth of what exists + what's missing)
│   ├── easy/  medium/  hard/
└── not-started/      — greenfield design (intent only)
    ├── easy/  medium/  hard/
```

Each `<state>/<complexity>/<feature>.md` is **one isolated feature**, no mixing. Every spec states:

- **Status** (matches the kit) — DONE / PARTIAL / NOT STARTED
- **Complexity** (matches the bucket) — EASY / MEDIUM / HARD with a one-line reason
- **Vision-doc refs** — F-codes / sections from the Project Vision
- **Summary**, **Scope**, **Dependencies**, **Data model**, **API surface**, **Behaviour & invariants**
- **References** (DONE + PARTIAL) or **Open questions** (NOT STARTED)

**State separation principle.** DONE = what exists. PARTIAL = what exists + what's missing. NOT STARTED = intended design only. Engineers reading a spec must instantly know whether they're extending code or building from scratch.

**Complexity separation principle.** Use it to (a) plan sprints by capacity, (b) match tasks to developer level, (c) surface hidden complexity in "simple-looking" features. The reason on each spec is the antidote to wishful estimating.

---

## DONE

### Easy

| Spec | Vision F-codes | Why easy |
|---|---|---|
| [Comments](done/easy/07-comments.md) | — | Single table, idempotent CRUD, hard-delete; no edit endpoint. |
| [Favorites](done/easy/08-favorites.md) | — | M2M with unique constraint, two-tab UI. |
| [UTC serialization invariant](done/easy/12-utc-serialization.md) | — | 12 lines of code; the value is the invariant, not the LOC. |
| [Master-record ranking boost](done/easy/F108-master-record-ranking.md) | Ф-108 | One-line ORDER BY change in the feed query. |
| [Phone uniqueness — global guarantee](done/easy/F089-phone-uniqueness.md) | Ф-89 | Helper extracted + applied across login callsites. |
| [Bot Menu Button](done/easy/bot-menu-button.md) | §4.2 | set_chat_menu_button wired at bot startup. |

### Medium

| Spec | Vision F-codes | Why medium |
|---|---|---|
| [Claim flow](done/medium/04-claim-flow.md) | Ф-105, Ф-106 | Auto-verify + OTP + reject-crawled, all wired end-to-end. |
| [Saved searches](done/medium/05-saved-searches.md) | Ф-68, Ф-69 | CRUD + matcher + last-seen counter; integrates with fanout. |
| [Admin moderation](done/medium/09-admin-moderation.md) | — | Multi-resource queues + audit log. |
| [Telegram bot](done/medium/10-telegram-bot.md) | — | aiogram dispatcher + Redis-bridged singleton. |
| [Ф-107 Seller claim notification](done/medium/F107-seller-claim-notification.md) | Ф-107 | Celery task + dedup constraint, integrated with fanout. |
| [Notification inline keyboards](done/medium/notification-inline-keyboards.md) | §4.2 | Callback handlers for fav/contact + deep-link integration. |
| [Bot inline mode (`@bot query`)](done/medium/bot-inline-mode.md) | §4.2 | inline_query handler tapping Meilisearch + deep links. |

### Hard

| Spec | Vision F-codes | Why hard |
|---|---|---|
| [Authentication & accounts](done/hard/01-authentication.md) | Ф-89 (partial) | Many providers, JWT lifecycle, multi-table phone uniqueness. |
| [Crawler & ingestion](done/hard/02-crawler-ingestion.md) | Ф-10 | Off-process Telethon + Playwright + LLM + dedup + translation. |
| [Listings & images](done/hard/03-listings.md) | — | 8-sprint visibility matrix, dual-read aliases, image pipeline. |
| [Notification system](done/hard/06-notifications.md) | Ф-76, Ф-79, Ф-80 | Two-stage fanout, three orthogonal gates, source-tagging, logs. |
| [Frontend platform](done/hard/11-frontend-platform.md) | — | TWA detection, FSD, BackButton version-gate, dual-token auth. |
| [Bot channel autoposting](done/hard/bot-channel-autopost.md) | §5.2 | my_chat_member listener + multi-channel state machine. |
| [Wallet (Ф-113)](done/hard/F113-wallet.md) | §10 | Click + Payme integration, atomic ledger, idempotent webhooks. |

---

## PARTIAL

### Easy

| Spec | Vision F-codes | Effort |
|---|---|---|
| [Seller dashboard — counters](partial/easy/seller-dashboard-counters.md) | §2.2 #4 | Per-card chips done; aggregate panel + contact endpoint + self-view guard missing. |

### Medium

| Spec | Vision F-codes | Effort |
|---|---|---|
| [Pre-launch fixes (vision §2.2)](partial/medium/pre-launch-fixes.md) | — | ~1 week; mixed checklist + i18n sweep. |

### Hard

| Spec | Vision F-codes | Effort |
|---|---|---|
| [Personalisation — interest vector](partial/hard/F077-personalization.md) | Ф-77, Ф-78 | Phase-1 collection now → Phase-2 scoring → Phase-3 ML. |

---

## NOT STARTED

### Easy

| Spec | Vision-doc location | Phase |
|---|---|---|
| [Deep links — filter pre-fill](not-started/easy/deep-links-filter-prefill.md) | §4.2 | 1 |

### Medium

| Spec | Vision-doc location | Phase |
|---|---|---|
| [Krutilka — three tabs](not-started/medium/F048-krutilka-three-tabs.md) | §4.1 (Ф-48) | 1 |
| [Deal status + final price](not-started/medium/deal-status-and-final-price.md) | §5.3 | 2 |
| [Promotion services — boost / badge / notify-priority](not-started/medium/promotion-services.md) | §7.4 | 2 |
| [Banner ads (Ф-118)](not-started/medium/F118-banner-ads.md) | §9 Phase 3 | 3 |

### Hard

| Spec | Vision-doc location | Phase |
|---|---|---|
| [CRM-light — clients linked to objects](not-started/hard/crm-clients.md) | §5.1 Уровень 2 | 2 |
| [Referral program](not-started/hard/referral-program.md) | §5.4 | 2 |
| [Real-prices analytics export](not-started/hard/real-prices-analytics.md) | §5.3, §9 Phase 3 | 3 |

---

## Suggested execution order — Phase 1 critical path

Picking from the boards above:

1. **easy** → [Master-record ranking](done/easy/F108-master-record-ranking.md) *(DONE)* — half-day quick win, big perceived-quality lift.
2. **easy** → [Bot Menu Button](done/easy/bot-menu-button.md) *(DONE)* — half-day, removes onboarding friction.
3. **easy** → [Deep-link filter prefill](not-started/easy/deep-links-filter-prefill.md) — half-day, marketing-ready ad links.
4. **easy** → [Seller dashboard counters](partial/easy/seller-dashboard-counters.md) — surface existing data; sellers see proof of value.
5. **medium** → [Ф-107 seller claim notification](done/medium/F107-seller-claim-notification.md) *(DONE)* — biggest wow-moment for sellers.
6. **medium** → [Inline keyboards under notifications](done/medium/notification-inline-keyboards.md) *(DONE)* — multiplies push-notification value.
7. **medium** → [Krutilka three tabs](not-started/medium/F048-krutilka-three-tabs.md) — unlocks the saved-search retention loop visually.
8. **easy** → [Phone uniqueness](done/easy/F089-phone-uniqueness.md) *(DONE)* — small but cleans up the auth surface before scale.
9. **hard** → [Channel autoposting](done/hard/bot-channel-autopost.md) *(DONE)* — most strategic Phase-1 feature; schedule after #5.

Phase 2 starts when §7.5 trigger fires (5 000+ active Tashkent listings AND 60+ days post-launch) — that batch starts with **hard / [Wallet](done/hard/F113-wallet.md)** *(DONE)* since every monetisation feature depends on it.

---

## Conventions

- File paths in specs use repo-root-relative form (`backend/app/api/v1/auth.py`).
- Line numbers reflect the state at spec-write time and may drift; treat them as starting points.
- Cross-spec links use relative paths from the source spec — `../<complexity>/X.md` for same-state, `../../<state>/<complexity>/X.md` for different-state.
- Every spec is independently readable. No "see above" — link instead.
