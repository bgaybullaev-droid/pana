# C1 — Tariff structure display in seller cabinet

**Status:** NOT STARTED — no `/seller/tariffs` route, no monetization config knobs, no tariff i18n keys.
**Complexity:** MEDIUM — UI-only feature, but touches feature-flag plumbing (new), dynamic stats endpoint (new), three locales of fresh copy, and the legal-friendly "test period" terminology that must NOT leak engineering jargon ("Phase 2") into UI.
**Block-C V2.0 ref:** C1.
**Why now:** the psychological contract spec calls for is broken if tariffs only appear on monetization-trigger day. They need to be visible from launch with a clear "test period active" message.

## What's done

- **`Seller.listings_count` denormalised counter** lives at `backend/app/db/models.py:298`:
  ```python
  listings_count: Mapped[int] = mapped_column(Integer, default=0)
  ```
  Incremented on create (`listings.py:2849`), claim (`claims.py:113, 232`, `crawler_service.py:608, 685`), decremented on soft-delete (`listings.py:3200`). **Caveat:** counts all non-deleted listings regardless of status. Fixing this is C2's job; C1 reads it as-is.
- **i18n foundation** (Block A6) is in place — three locales (`ru`, `uz`, `uz-cyrl`) live in `frontend/src/shared/i18n/locales/`. `formatNumber` helper in `frontend/src/shared/lib/formatNumber.ts` handles UZS pretty-printing.
- **Seller cabinet routes** are mounted at `frontend/src/modules/seller/app/router/Router.tsx`. The seller layout already includes a nav-item iteration pattern (we used it in Block A's A8 admin sources page).

## What's missing

1. **`/seller/tariffs` route does not exist.** No page module under `frontend/src/modules/seller/pages/`.
2. **Zero monetization configuration knobs.** `backend/app/core/config.py:11-188` has no `TEST_PERIOD_*`, `MONETIZATION_*`, `is_paid_phase` etc.
3. **No dynamic stats endpoint** for the "Подробнее об условиях завершения" disclosure block. Spec wants live progress: "В системе сейчас X объявлений, прошло Y дней". `backend/app/api/v1/sellers.py:549` only exposes per-seller dashboard, not system-wide totals or launch-day arithmetic.
4. **No tariff i18n keys** in any locale (`tariff` / `subscription` / `test_period` / `тестовый` / `подписка` returned no hits).
5. **No "3rd-listing hint" on listing-create flow.** `frontend/src/modules/seller/pages/create-listing/` page doesn't reference any limit copy today.
6. **No tariff banner in "My Listings".** The page header (`seller/pages/listings/ui/page/Page.tsx`) has no banner slot.
7. **No disabled-pay-buttons component.** Spec wants visually present buttons that open an info modal — the modal pattern needs reuse from somewhere; A8 has a delete-confirm modal precedent.

## Path to DONE

### Step 1 — config knobs

Add to `backend/app/core/config.py`:

```python
# Block C — Test-period / monetization triggers
test_period_active: bool = True       # Single feature flag the UI reads
test_period_started_at: Optional[datetime] = None  # ISO; defaults to now() if null
monetization_trigger_listings: int = 5_000
monetization_trigger_days: int = 60
free_listings_per_seller: int = 2
extra_listing_price_uzs: int = 25_000
cabinet_subscription_price_uzs: int = 99_000
```

These are **the only** source of truth for tariff values; the page reads them via a new endpoint (Step 3). Hard-coding any of these in TypeScript is forbidden.

### Step 2 — system-wide stats endpoint

`backend/app/api/v1/admin.py` (or a new `monetization.py`):

```
GET /tariffs/status     → public, cached 1h
{
  "test_period_active": bool,
  "test_period_started_at": iso,
  "current_listings_total": int,   // count from listings WHERE deleted_at IS NULL AND status=ACTIVE
  "trigger_listings": int,
  "trigger_days": int,
  "days_elapsed": int,
  "extra_listing_price_uzs": int,
  "cabinet_subscription_price_uzs": int,
  "free_listings_per_seller": int
}
```

Cached 1 hour (Redis) — listing count is expensive to recompute on every page-view, freshness is not critical for a banner. Cache key: `tariffs:status:v1`.

### Step 3 — page module

`frontend/src/modules/seller/pages/tariffs/ui/page/Page.tsx`:
- Header: «Тестовый период активен. Точные сроки завершения объявим за 14 дней.»
- Disclosure block with progress bars derived from the new endpoint.
- Two-column tariff card: "Размещение" / "Кабинет".
- Disabled "Оплатить" / "Подписаться" / "Пополнить кошелёк" buttons that open an info modal.

Reuse the V1 Mantine/Effector patterns from existing seller pages. State store: `frontend/src/modules/seller/pages/tariffs/model/` with one effect (`fetchTariffStatusFx`) and one store (`$tariffStatus`).

### Step 4 — entry points + nav

- Add a nav-item "Тарифы" / "Tariflar" / "Тарифлар" in `frontend/src/modules/seller/app/ui/layout/SellerLayout.tsx` (mirror of A8's pattern).
- "My Listings" header banner — small `Alert`/`Box` reading the tariff status, link to `/seller/tariffs`.
- Listing-create flow — show inline copy when `seller.listings_count >= 2`: "Сейчас все объявления бесплатны. По завершении тестового периода от 3-го объявления — 25 000 сум/мес".

### Step 5 — i18n keys (3 locales × ~25 keys)

```
tariffs.pageTitle
tariffs.heroBanner
tariffs.detailsToggle
tariffs.detailsTriggerLabel  // "при достижении X объявлений и Y дней"
tariffs.progress.listings    // "{{current}} из {{target}}"
tariffs.progress.days        // "{{current}} из {{target}} дней"
tariffs.placement.title
tariffs.placement.line1      // 2 free forever
tariffs.placement.line2      // 25 000 UZS / extra
tariffs.cabinet.title
tariffs.cabinet.price        // "99 000 сум / месяц"
tariffs.cabinet.featureBot   // bot autopost
tariffs.cabinet.featureAnalytics
tariffs.cabinet.featureClients
tariffs.payButton            // "Оплатить"
tariffs.subscribeButton      // "Подписаться"
tariffs.topupButton          // "Пополнить кошелёк"
tariffs.modalDisabledTitle   // "Тестовый период активен"
tariffs.modalDisabledBody    // "Оплата откроется автоматически по завершении тестового периода"
tariffs.banner.myListings    // banner copy on /seller/listings
tariffs.banner.thirdListingHint
tariffs.grandfathering       // grandfathering note
tariffs.freeForever          // 2 free forever
```

Mirror across `ru/seller.json`, `uz/seller.json`, `uz-cyrl/seller.json`.

### Step 6 — analytics breadcrumbs

The spec explicitly notes "просмотр страницы тарифов" is a useful signal even before monetization. Wire whatever telemetry layer the project uses (none observed in repo today, so likely a no-op for now — but flag the slot).

## Behaviour & invariants

- **Single source of truth for prices** — `backend/app/core/config.py`. Frontend never hardcodes 25 000 / 99 000.
- **Test-period banner is the unconditional default** — when `test_period_active=true`, every monetary CTA on the page is disabled and opens the info modal.
- **No "Phase 2" / "Phase 1" / engineering vocabulary in UI strings** — all three locales use «тестовый период» / "test period". Engineering vocabulary stays in code (variable names, comments) and in this spec-kit.
- **Trigger condition lives in config**, not in code — admin can change `monetization_trigger_listings` from 5 000 to 10 000 without a code release.
- **System-wide stat endpoint is cached** — 1h Redis cache; the disclosure block tolerates staleness up to that window.
- **A11y** — disabled buttons keep their tab-order and announce "недоступно во время тестового периода" via aria-disabled + aria-describedby. Connect to B6's aria sweep.

## Architecture notes

- The endpoint sits under `/admin` only if it's admin-only; the spec wants the *progress* visible to sellers, so put it under a public-but-cached path: `GET /tariffs/status` (no auth required).
- `/sellers/me/dashboard` already returns `total_listings` for one seller; we don't reuse it. We need a global count.
- Computing global active count cheaply at scale: `SELECT count(*) FROM listings WHERE deleted_at IS NULL AND status='ACTIVE'`. Index on `status` + partial index on `deleted_at IS NULL` already cover this. Cache.

## Upstream dependencies

- **A6** (i18n foundation) — DONE.
- **A7** (`ListingStatus.ACTIVE` semantic) — DONE.
- **C2** for the per-seller counter copy on "My Listings" banner — couples; recommend C1 + C2 land in same wave.

## Downstream dependencies

- **C2** uses C1's `test_period_active` flag for its display-only-vs-block decision.
- **C3** (Wallet) — when C3 lands, the disabled "Пополнить кошелёк" button on the page can be replaced with a real one (post-Phase-2 work, not C1's responsibility).
- **D-block / marketing** — Telegram bot copy referencing tariffs needs the same i18n keys.

## Migration / schema implications

- **None.** C1 is presentation only; no schema changes. Config-only.

## API implications

- New endpoint `GET /tariffs/status`. Public, cached. Documented OpenAPI.
- No backend write APIs in C1.

## Crawler / bot implications

- **Bot copy** — the seller-onboarding bot flow (in `backend/app/bot/handlers.py`) currently doesn't mention tariffs. Spec calls for the bot to point at the tariffs page. One-line addition; coordinate with C1 i18n keys.
- **Crawler** — none.

## AI / F-block implications

- **None.** C1 doesn't touch F1 or F3.

## SEO implications

- **None.** `/seller/tariffs` is auth-gated; not indexed.

## Localization implications

- ~25 new keys × 3 locales × native-speaker review for `uz` and `uz-cyrl`.
- Special care: the Russian word «тестовый период» must translate to natural Uzbek — not a literal calque. Native-speaker pass.
- Currency formatting uses `formatNumber()` from A6.

## Infra / deploy implications

- Redis is already available; no new infra.
- `test_period_started_at` defaults to deploy timestamp on first run; otherwise read from settings.

## Edge cases

- **`test_period_active=false` while no real payment integration** — must not break the page. Buttons stay disabled until C3+ activates them.
- **System-wide count = 0 at launch** — disclosure shows "0 / 5 000". Acceptable.
- **Days-elapsed crosses negative** when `test_period_started_at` is in the future — clamp to 0; never show a negative number.
- **Locale switch mid-session** — page re-renders cleanly with the new `t()` calls; no caching of the old locale's strings.
- **A/B price segmentation** (out of MVP, but spec mentions architecture readiness) — the endpoint already returns prices in the response, so a segmentation strategy is one extra param away.
- **Admin changes a price mid-session** — the page has stale data for ≤ 1h; that's fine.

## Operational risks

- **Engineering jargon leak** — biggest risk. A copy slip ("after Phase 2 begins") makes the test-period contract feel unprofessional. Mitigate: single i18n review pass with a non-engineer.
- **Config drift** — if anyone hardcodes `25_000` in the UI for a test, it will desync from settings the day a price changes. Add a lint rule (or a runtime warning) that flags hardcoded UZS amounts in TSX.
- **Cache TTL miscalibration** — too long, and the progress bar lies; too short, and DB cost rises. 1h is reasonable; revisit after launch.

## Rollout strategy

- Behind no flag; C1 ships as a static page. The trigger stays at `test_period_active=true` until C3+ are ready.
- Soft-launch: ship the page hidden from the nav, share the URL with a few realtors for copy review, then add to the nav.

## Acceptance criteria

- `GET /tariffs/status` returns the documented JSON; no auth required; cached 1h.
- `/seller/tariffs` is reachable from the seller-cabinet nav and renders without console errors in all three locales.
- Disabled buttons open an info modal whose body is the localised "test period" copy.
- The disclosure block shows live counts: "X из 5000", "Y из 60 days", driven by the endpoint.
- `grep -RnE "(25\\s?000|99\\s?000)\\s*(сум|so'm|UZS)" frontend/src` returns zero results in TSX (only in JSON/i18n).
- All new strings have entries in `ru/seller.json`, `uz/seller.json`, `uz-cyrl/seller.json`.
- Lighthouse a11y on the page ≥ 95.
- "Phase" / "Фаза" / "phase 2" don't appear in any user-visible string.

## Recommended PR split

- **PR1** (BE) — config knobs + `/tariffs/status` endpoint + cache + tests.
- **PR2** (FE) — page module + nav-item + i18n keys (3 locales).
- **PR3** (FE) — banners on "My Listings" + listing-create hint.

## Estimated complexity

~2 dev-days FE, ~0.5 dev-day BE. Total ~2.5 dev-days.

## References

- `backend/app/core/config.py:11-188` — config knobs to extend.
- `backend/app/api/v1/sellers.py:549-634` — pattern for stats endpoint shape.
- `backend/app/db/models.py:298` — `Seller.listings_count`.
- `frontend/src/modules/seller/app/router/Router.tsx` — where to mount route.
- `frontend/src/modules/seller/app/ui/layout/SellerLayout.tsx` — nav-item pattern.
- `frontend/src/shared/lib/formatNumber.ts` — UZS formatting helper.
- [A6](../../block-a/medium/A6-i18n-leaks.md), [A8](../../block-a/medium/A8-channels-management.md) — patterns to mirror.
- [C2](./C2-free-limit-logic.md) — paired counter work.
- [C3](../hard/C3-wallet-architecture.md) — what the disabled buttons will eventually call.
