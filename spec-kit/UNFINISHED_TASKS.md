# UcharMarket — Unfinished Tasks Audit

**Generated:** 2026-05-13
**Scope:** Every block except Block B (Block B left untouched per request).
**Method:** Four parallel code audits comparing each spec's stated requirements against the current state of `backend/`, `frontend/`, `telegram-ai/`, and `deploy/`. Each task is classified DONE / PARTIAL / NOT STARTED based on what the code actually does, not what the spec's status field says.

> Anything classified DONE here is **not** repeated in the "Unfinished" sections below — see the per-block summary lists at the bottom for the full picture.

---

## Block A — Launch blockers (V2.0)

### A1 — Claim/Reject V2.0 · **PARTIAL**

| Missing piece | Where it lives / should land |
|---|---|
| `ai_description_ru`/`uz`/`uz_cyrl` not exposed in B2C `ListingResponse` schema. | `backend/app/schemas/listing.py` — `ListingResponse` needs the three nullable AI fields. |
| Skeleton card for `status=PENDING_GENERATION` not rendered on seller cabinet listings page. | `frontend/src/modules/seller/pages/listings/ui/main/` |
| Post-F1 controller-side language picker for AI text not wired into B2C feed. | `backend/app/api/v1/buyer.py` / feed endpoint — pick `ai_description_{locale}` based on user language. |

### A2 — Mockup filters · **PARTIAL**

| Missing piece | Where |
|---|---|
| `house_type`, `house_condition`, `water_supply` not added to `ListingFilters` schema or applied in the query builder. | `backend/app/schemas/listing.py:ListingFilters` + `backend/app/api/v1/listings.py` query construction |
| `utilities` filter has no backend column mapping. | Same. |

### A4 — Push notifications · **PARTIAL**

| Missing piece | Where |
|---|---|
| Callback handlers for inline buttons `claim_crawled:` / `reject_crawled:` not verified in code. | `backend/app/bot/handlers.py` |
| 7-day expiry Celery beat job for stale crawled-match notifications not in `celery_app.py` beat schedule. | `backend/app/workers/celery_app.py` |
| Group-batching with Redis debounce window not present. | `backend/app/workers/tasks/crawled_match.py` |
| Explicit bot-blocked fallback (TelegramForbiddenError handling) needs verification. | Same. |

### A6 — i18n leaks · **PARTIAL**

| Missing piece | Where |
|---|---|
| Spec calls for **`uz-latn`** locale; implementation only ships **`uz-cyrl`**. The third script variant has no JSON files. | `frontend/src/shared/i18n/locales/uz-latn/` — create directory + 4 JSONs (`common`, `seller`, `buyer`, `admin`). |
| ICU plural support not evidenced — date/number formatters still use `toLocaleString("ru-RU")` in several places. | Sweep `frontend/src/` for `toLocaleString("ru-RU"` and replace with i18n-driven formatters. |
| `DescriptionDrawer` regex markers (e.g. emoji/section headers) not localized. | `frontend/src/modules/buyer/pages/listing-detail/ui/dialogs/DescriptionDrawer.tsx` |

### A8 — Channels management · **PARTIAL**

| Missing piece | Where |
|---|---|
| Admin UI under `frontend/src/modules/admin/pages/sources/` exists but spec calls for richer per-source metadata + metrics persistence; not all spec fields verified. | `frontend/src/modules/admin/pages/sources/` |
| Crawler DB read refresh tick (re-read `parser_sources` periodically without restart) not verified. | `telegram-ai/crawler/` |
| Per-channel token-bucket rate limiting not evidenced. | `telegram-ai/crawler/` |

### A — DONE

* **A3** — Mock data Found: `getMockups()` deleted, no Unsplash references remain.
* **A5** — View/Contact counters: `views_7d`/`contacts_7d` present in dashboard response; anonymous dedup via `anon_id`.
* **A7** — Parser quality + F1 trigger: ListingStatus enum extended, AI columns present, F1 worker live, B2C feed gates correctly, junk filter extended.

---

## Block C — Subscriptions & quotas

### C1 — Tariff display · **PARTIAL**

| Missing piece | Where |
|---|---|
| Frontend page `/seller/tariffs` does not exist. | `frontend/src/modules/seller/pages/tariffs/` — create FSD page. |
| No `tariffs.*` i18n keys in any of ru / uz / uz-cyrl. | `frontend/src/shared/i18n/locales/*/seller.json` |
| Seller sidebar nav-item linking to tariffs page missing. | `frontend/src/modules/seller/app/...` (or wherever the seller nav lives) |
| Disabled-pay-buttons modal on the tariff page during test period absent. | Same. |
| "Test period" banner on seller "My Listings" page absent. | `frontend/src/modules/seller/pages/listings/...` |
| Progress-toward-monetization disclosure block absent. | Same. |

### C2 — Free-listings limit · **PARTIAL**

| Missing piece | Where |
|---|---|
| "My Listings" header chip showing active count not implemented. | `frontend/src/modules/seller/pages/listings/...` |
| Third-listing info-toast on successful create not wired. | `frontend/src/modules/seller/pages/create-listing/...` (Stage 1 success handler) |
| `GET /sellers/me/dashboard` response lacks `total_active_listings` field. | `backend/app/api/v1/sellers.py` |
| `Seller.listings_count` legacy column still present and not fully replaced in all reads (denormalization risk). | `backend/app/db/models.py` + audit of reads. |

### C4 — Multi-phone connection · **PARTIAL**

| Missing piece | Where |
|---|---|
| Frontend "My Phones" settings UI page absent. | `frontend/src/modules/seller/pages/phones/ui/` — page lives but verify against spec (request OTP / verify / list / delete flows). |
| Phone-picker on listing-create / edit forms not wired (defaults silently to primary). | `frontend/src/modules/seller/pages/create-listing/...` + edit-listing form fields. |
| "Add a number?" hint after first claim not surfaced. | Claim success handler. |
| Delete-with-active-listings 3-option modal flow incomplete on frontend. | `frontend/src/modules/seller/pages/phones/ui/` |
| SMS verification path (Eskiz.uz) not integrated — only Telegram-bot OTP works. Spec leaves this an open question; should be resolved or scoped out. | `backend/app/api/v1/seller_phones.py` + decide if SMS is needed for launch. |

### C5 — Multi-account detection · **NOT STARTED**

Zero progress. Five signal tasks, `account_suspicion` + `account_link` tables, admin queue, evidence JSONB, suppression logic — all greenfield.

| Missing piece | Where |
|---|---|
| Migration for `account_suspicion` + `account_link` tables. | New alembic version. |
| Five signal Celery tasks (phone collision, shared object signature, same-device registration, similar names, suspicious phone-verify patterns). | `backend/app/workers/tasks/suspicions.py` (new). |
| Admin queue endpoints `GET/PATCH /admin/suspicions`. | `backend/app/api/v1/admin_suspicions.py` (new). |
| Admin UI module for triage. | `frontend/src/modules/admin/pages/suspicions/` (new). |
| False-positive suppression logic. | Service layer. |

### C — DONE

* **C3** — Wallet architecture: Wallet + Transaction + Subscription tables and idempotent `deposit()` / `admin_adjust()` services shipped (Block F's F4 cabinet exports + Block D's D4 autopost gate both consume `check_active_subscription`).

---

## Block D — Telegram-native mechanics (V2.0)

**Re-audited 2026-06-12 (code-verified).** All five tasks D1–D5 are functionally
DONE — including every gap listed by the 2026-05-13 audit below-the-fold history:
`PATCH /api/v1/me/language` exists (`backend/app/api/v1/preferences.py:143`),
the TWA Settings language picker is live, autopost transition hooks are wired
(`backend/app/api/v1/listings.py` — `_dispatch_autopost_for_status_change`),
the Cabinet autoposting page with the 48h modal exists
(`frontend/src/modules/seller/pages/autoposting/`), and `User.language` →
i18next sync happens on auth (`frontend/src/app/providers/AuthProvider.tsx:121-132`).

Follow-up work (8 small PRs) is specified in
**`spec-kit/block-d/FOLLOWUP_PLAN.md`** — the live status checklist lives there,
do not duplicate statuses here. **As of 2026-06-17 all eight are done:** FU1–FU7
merged (quick fixes incl. the inline `is_personal` cache bug, per-listing
autopost opt-out + stale badge, bot rate limits, Block D test coverage, parser
telemetry, filter deep-link hydration fix + marketing slugs, saved-search
digest) and **FU8 (docs/ops)** shipped as
[`docs/telegram-bot-setup.md`](../docs/telegram-bot-setup.md) — BotFather setup,
the pre-launch D1–D5 e2e checklist, the manual 48h media spike, telemetry SQL,
and marketing deep-link examples.

---

## Block F — AI generation + SEO

**All 10 PRs DONE** (F5a, F1a, F1b, F3a, F3b, F3c, F4a, F4b, F5b, F2). Only the ops-side actions of F3c remain (DNS, TLS cert, sitemap submission, Lighthouse audit), and those are deployment actions not code:

| Real-world step | Owner |
|---|---|
| DNS A record for `ucharmarket.uz`. | Ops |
| TLS certificate via Let's Encrypt. | Ops |
| Drop `deploy/nginx/ucharmarket.conf` into the reverse proxy and reload. | Ops |
| Submit `/sitemap.xml` to Google Search Console + Yandex.Webmaster. | Ops |
| Google Rich Results Test pass on a sample listing URL. | Ops |
| Lighthouse mobile audit: Performance ≥ 75, SEO 100. | Ops |

---

## Top-level `partial/` and `not-started/` specs

### Still incomplete

| Spec | Status | What's missing |
|---|---|---|
| `partial/easy/seller-dashboard-counters.md` | **PARTIAL** | No `POST /listings/{id}/contact` endpoint → `contacts_count` frozen at 0. No self-view guard. No `GET /sellers/me/dashboard` aggregate. No favorites-count chip. |
| `partial/medium/pre-launch-fixes.md` | **MIXED** | Mockup filter badges still need flag gating or backend wiring. Hardcoded RU strings across seller module need sweep. `/search` legacy-route redirect to `/?<params>` missing. |
| `partial/hard/F077-personalization.md` | **PARTIAL — Phase 1 data only** | Frontend never calls `POST /listings/{id}/view`. Phase 2 scoring pipeline + Recommended feed not started. Anonymous session attribution deferred. |
| `not-started/easy/deep-links-filter-prefill.md` | **DONE (FU6, #113)** | `parse_filter_slug` ships `chilanzar_2rooms_rent`-style slugs + the `filter_<id>` hydration fix; examples in `docs/telegram-bot-setup.md` §7. |
| `not-started/medium/F048-krutilka-three-tabs.md` | **NOT STARTED** | No tab UI on home page. No `$activeTab` store. No Subscriptions feed endpoint. |
| `not-started/medium/deal-status-and-final-price.md` | **NOT STARTED** | No `ListingSale` table. No `sold_price`, `sold_at`, `sold_currency` columns. `Listing.status=SOLD` exists but carries no sale metadata. |
| `not-started/medium/promotion-services.md` | **PARTIAL — only `is_boosted` exists** | No `has_urgent_badge` or `notify_priority_until` columns. No purchase endpoints (`POST /listings/{id}/promotions/*`). No wallet integration on the purchase path. |
| `not-started/medium/F118-banner-ads.md` | **NOT STARTED** | No `Banner` table. No admin CRUD. No `/banners/active` endpoint. No impression/click tracking. |
| `not-started/hard/crm-clients.md` | **NOT STARTED** | No `SellerClient` or `SellerClientListing` tables. No Kanban/pipeline view. No `/seller/clients` endpoints. |
| `not-started/hard/referral-program.md` | **PARTIAL — minimal** | Only `User.referral_source` exists; spec requires `referral_code` + `referred_by_user_id`. No `ReferralEvent` / `ReferralReward` tables. No qualification logic on paid action. No monthly reward redemption. No `/seller/referrals` endpoint. |
| `not-started/hard/real-prices-analytics.md` | **NOT STARTED** | No materialised views. No `/analytics/price-index` or `/analytics/api/v1/*` endpoints. No B2B API-key auth schema. Hard-blocked on `ListingSale` (`deal-status-and-final-price` first). |

### Effectively DONE despite folder location

These specs were filed under `partial/` or `not-started/` but the audit found them actually implemented (they were shipped under Block A/D/F work):

| Spec | Where it actually lives |
|---|---|
| `partial/easy/F089-phone-uniqueness.md` | `app/services/account_linking.py:reserve_phone_for_user` + DB unique indexes on `users.phone` / `sellers.phone`. |
| `partial/easy/F108-master-record-ranking.md` | `app/api/v1/listings.py` query — `master_record_id IS NULL` dedup + `claim_rank` order. |
| `not-started/easy/bot-menu-button.md` | `app/bot/setup.py` calls `set_chat_menu_button`. |
| `not-started/medium/F107-seller-claim-notification.md` | `app/workers/tasks/crawled_match.py:notify_sellers_of_crawled_listing`. |
| `not-started/medium/notification-inline-keyboards.md` | `app/bot/keyboards.py` + push pipeline. |
| `not-started/medium/bot-inline-mode.md` | `app/bot/inline.py` registered in `app/bot/main.py`. |
| `not-started/hard/bot-channel-autopost.md` | `app/services/autopost.py` + `app/workers/tasks/autopost.py` + `app/services/channel_publisher.py`. **Note:** transition hooks still missing per D4 above. |
| `not-started/hard/F113-wallet.md` | `app/db/models.py:Wallet/WalletTransaction` + `app/services/wallet.py` + admin adjust endpoint. |

These can be moved to `spec-kit/done/` to keep the boards honest.

---

## Summary table — work remaining

| Area | Effort estimate (rough) | Priority |
|---|---|---|
| **A4** push-notification inline-callback handlers + 7-day expiry cron + group-batching | 2 days | Launch-critical |
| **A6** `uz-latn` locale + ICU plurals + drawer regex i18n | 2 days | Launch-critical |
| **A2** missing schema filters (`house_type`, `house_condition`, `water_supply`, `utilities`) | 0.5 day | Launch-critical |
| **A1** AI description fields in B2C response + skeleton state | 1 day | Launch-critical |
| **A8** crawler refresh tick + admin UI polish + rate-limit | 1.5 days | Launch-critical |
| **C1** tariffs frontend page + nav + i18n + banners | 2 days | Pre-launch UX |
| **C2** "My Listings" chip + third-listing toast + dashboard aggregate | 1 day | Pre-launch UX |
| **C4** phone-picker on listing forms + delete-with-active-listings modal | 1.5 days | Pre-launch UX |
| **C5** multi-account detection — five signals, tables, admin queue + UI | 6 days | Post-launch |
| ~~**Block D follow-up** — FU1–FU8 per `spec-kit/block-d/FOLLOWUP_PLAN.md`~~ **DONE 2026-06-17** (all eight PRs merged/shipped) | — | Pre-launch UX / quality |
| **F3c ops** DNS / cert / sitemap submission / Rich Results / Lighthouse | 1 day + propagation | Launch |
| **seller-dashboard-counters** `/contact` endpoint + self-view guard + dashboard aggregate | 1 day | Pre-launch UX |
| **F077-personalization** Phase 2 scoring + Recommended feed | 5 days | Post-launch |
| ~~**deep-links-filter-prefill** filter-shortcut parser — FOLLOWUP_PLAN **FU6**~~ **DONE (#113)** | — | Marketing |
| **F048-krutilka-three-tabs** home tab UI + subscriptions feed | 3 days | Post-launch |
| **deal-status-and-final-price** `ListingSale` table + sale metadata capture | 2 days | Post-launch |
| **promotion-services** urgent badge, notify-priority, purchase endpoints | 4 days | Post-launch (gated on wallet flip) |
| **F118-banner-ads** banners table + admin CRUD + impression/click tracking | 4 days | Phase 3 |
| **crm-clients** Kanban + pipeline tables + endpoints | 8 days | Phase 2 |
| **referral-program** referral_code + ReferralEvent/Reward + qualification + `/seller/referrals` | 5 days | Phase 2 |
| **real-prices-analytics** materialised views + B2B API + auth | 6 days | Phase 3 (blocked on `ListingSale`) |
| **pre-launch-fixes** RU-string sweep + filter badges + `/search` redirect | 2 days | Pre-launch UX |

**Totals (excluding Block B):**
- **Launch-critical work remaining:** ~7 engineer-days across Block A.
- **Pre-launch UX polish:** ~7 engineer-days across Block C + D + dashboard counters.
- **Ops cutover (F3c):** ~1 engineer-day + DNS/cert propagation.
- **Post-launch features (Phase 2/3):** ~38 engineer-days across CRM, referrals, promotions, banners, analytics, krutilka tabs, deal-status, personalization Phase 2.

---

## Notes

- **Block B was not audited**, per request. Whatever B's status is, it isn't reflected here.
- **All Block F PRs (F1a/F1b/F2/F3a/F3b/F3c/F4a/F4b/F5a/F5b) shipped** during this work session. The only F3c gap is the real-world ops cutover (DNS/cert/sitemap submission), not code.
- **Several "not-started" specs are actually DONE** (see section above). The spec-kit folder structure has drifted from reality — moving those files to `spec-kit/done/` will sharpen future audits.
- **No automated tests were run during this audit.** The 415/415 backend unit-test green state is from earlier in the same session. Frontend `tsc --noEmit` is also green on all newly-shipped code; the 4 pre-existing TS errors in `admin/pages/sources`, `seller/pages/phones`, `seller/pages/tariffs` predate the Block F work and are unrelated to anything in this document.
