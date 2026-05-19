# 05 — Pre-Launch Fixes (Vision §2.2)

**Status:** PARTIAL — mixed. Some items closed during recent work, some still open.
**Complexity:** MEDIUM — mixed checklist of small fixes plus an i18n sweep across the seller module — multiple touch points, ~1 week elapsed.
**Vision-doc refs:** Section 2.2 (8 critical pre-launch items)

## Status by item

### 1. Claim/reject in "Found" — remove "в разработке" stub
**Status:** **DONE.** Verified end-to-end — `POST /claims/`, `POST /claims/{id}/verify`, `POST /listings/reject-crawled/{source}/{crawled_id}` all wired and called from the Found page. No "в разработке" copy found in `frontend/src/modules/seller/pages/found/`. Spec covered in [`../../done/medium/04-claim-flow.md`](../../done/medium/04-claim-flow.md).

### 2. Mockup badges in filters (5 sections without backend)
**Status:** **OPEN.** Confirmed: the buyer home page (`Page.tsx`) imports `mockupFilters` and renders 5 filter sections with a `MockupBadge` (lines ~50, 167-189). These show "Mockup" copy to users.
**Action:** for each section either (a) wire the backend filter param if the field exists on `Listing`, or (b) hide the section behind a `VITE_SHOW_MOCKUP_FILTERS=true` flag (default false in production). Easiest path: ship behind a flag now, wire incrementally as backend filters land.

### 3. Notify seller on new crawled listing matching their phone (Ф-107)
**Status:** NOT STARTED. Tracked as separate spec → [`../../not-started/medium/F107-seller-claim-notification.md`](../../not-started/medium/F107-seller-claim-notification.md).

### 4. View counter visible to seller
**Status:** **PARTIAL.** Per-card view chip + contacts chip already render in the seller portfolio (`frontend/src/modules/seller/pages/listings/ui/page/Page.tsx:546-565`). Aggregate dashboard panel, the `POST /listings/{id}/contact` endpoint, and the self-view guard are still missing — tracked as → [`../easy/seller-dashboard-counters.md`](../easy/seller-dashboard-counters.md).

### 5. Unify search surfaces (remove `/search` legacy)
**Status:** **OPEN.** Confirmed: `/search` is registered in `frontend/src/app/router/Router.tsx` (rootPaths array, ~line 59) alongside the home filter drawer. Two surfaces for the same intent.
**Action:** add a redirect `/search` → `/?<filter params>` (with filter-state translation), then delete the legacy `/search` page module. Don't just unmount — the redirect prevents broken bookmarks / link-shares.

### 6. Hardcode RU strings → i18n
**Status:** **OPEN.** Larger than the "checklist item" framing implied. Confirmed offenders include:
- `frontend/src/modules/seller/pages/found/ui/page/Page.tsx` — hardcoded mockup titles ("2-комн. Квартира Юнусабадский район", "Современный дом в Мирзо-Улугбекском районе", …, lines ~302-531).
- `frontend/src/modules/seller/pages/edit-listing/ui/page/Page.tsx` — hardcoded validation strings ("Добавьте хотя бы одно фото", "Осталось заполнить…", lines ~425, ~475).
- Likely others across `modules/seller/`.

**Action:** sweep with `rg -n '[А-Яа-я]' frontend/src/modules/seller --type tsx | grep -v '/__tests__/'`, move each to `shared/i18n/locales/{ru,uz}/seller.json`, and add UZ translations simultaneously (otherwise UZ users see RU fallback strings).
**Scope:** budget ~3-5 days, not a half-day item.

### 7. Inline characteristics block in card
**Status:** DONE. `frontend/src/shared/ui/ListingCard.tsx` renders rooms/area/floor as chips with icons — see [03-listings](../../done/hard/03-listings.md).

### 8. Photo-overlay text contrast
**Status:** PARTIAL. `ListingCard` applies a gradient overlay; verify on a bright photo (white walls, sunny exterior shots). If still unreadable, switch to a solid pill behind price/title text.

## Acceptance criteria

| # | Item | Done when |
|---|---|---|
| 1 | "В разработке" stub | ✅ already verified — no action. |
| 2 | Mockup badges | All 5 sections gated behind a flag default-off in production, or wired to backend filters. |
| 3 | Ф-107 seller-claim notify | Tracked separately in `../../not-started/medium/F107-seller-claim-notification.md`. |
| 4 | Seller view counter | Tracked separately in `../easy/seller-dashboard-counters.md` (per-card chips done; aggregate + endpoint + guard missing). |
| 5 | `/search` legacy | Redirect lands; legacy module deleted. |
| 6 | RU → i18n in seller module | `rg '[А-Яа-я]'` over seller .tsx returns 0 hits outside tests; both `ru` and `uz` JSON updated. |
| 7 | Inline characteristics chips | ✅ already DONE — no action. |
| 8 | Photo-overlay contrast | Visual check on bright photos passes; if not, switch to solid pill. |
