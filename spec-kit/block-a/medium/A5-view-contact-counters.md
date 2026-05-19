# A5 — Views + Contacts counters (V2.0)

**Status:** PARTIAL — event table, idempotency, self-view exclusion, contact endpoint, dashboard tile, per-card chips are all live. Only the 7-day rolling window and explicit cross-context unification remain.
**Complexity:** MEDIUM — most of the work is done; what remains is one extra aggregate query, one UI label change, and a small audit of cross-context counting.
**Block-A V2.0 ref:** A5 (Section "A5. Счётчик просмотров и обращений").
**V1 cross-ref:** Supersedes [`../../partial/easy/seller-dashboard-counters.md`](../../partial/easy/seller-dashboard-counters.md) — the contact endpoint and self-view guard listed missing there have shipped.

## What's done

- **`listing_view_event` table** — migration `backend/alembic/versions/20260427_pre_listing_view_event.py`. Columns: `id (uuid)`, `user_id (uuid, nullable, FK users)`, `listing_id (uuid)`, `event_type (varchar 'view' | 'contact')`, `viewed_at`, `dwell_ms (bigint, nullable)`. Indexes: `(user_id, viewed_at desc)`, `(listing_id, event_type, viewed_at desc)`, plus a partial unique `(user_id, listing_id, event_type, date(viewed_at)) WHERE user_id IS NOT NULL` enforcing per-day idempotency at the DB layer.
- **Service** — `backend/app/services/listing_views.py:16-32`: `is_self_view(user, listing)` returns true iff `seller.user_id == user.id`. Returns false for crawled listings without a claimed seller (`seller_id IS NULL`) so anonymous-author listings still count.
- **Endpoints in `backend/app/api/v1/listings.py`:**
    - `POST /listings/{id}/view` (lines 3221-3244) — `ON CONFLICT … DO UPDATE SET dwell_ms = GREATEST(...)`; same-day repeat updates dwell only.
    - `POST /listings/{id}/contact` (lines 3247-3284) — `ON CONFLICT … DO NOTHING`; only the first daily insert bumps `Listing.contacts_count`.
    Both call `is_self_view()` first and return early.
- **Frontend tracker** — `frontend/src/shared/lib/viewTracking.ts:32-96`: `trackView()` posts on mount with `dwell_ms: null`, schedules a dwell-update on `visibilitychange` / unmount; `trackContact()` posts on phone-reveal / message-button click.
- **Cabinet UI** — `frontend/src/modules/seller/pages/listings/ui/page/Page.tsx`:
    - Aggregate band (lines 280-326) — `total_views`, `total_contacts`, `total_favorites` from `GET /sellers/me/dashboard` (`backend/app/api/v1/sellers.py:549-613`).
    - Per-card chips (lines 623-671) — three icons: 👁️ `views_count`, 📞 `contacts_count` (when > 0), ❤️ favorites count.

## What's missing

1. **No 7-day window stats anywhere.** Both the dashboard endpoint and the per-card response sum `Listing.views_count` (denormalized all-time). The event table has the data, but no query reads `viewed_at >= now() - interval '7 days'`. V2.0 spec asks for "all-time AND last-7-days" on every card.
2. **Cross-context unification not verified.** Anonymous viewers (no `user_id`) skip the event table entirely (`viewTracking.ts:22-24`); their views still increment the cached `Listing.views_count` somewhere outside the event flow. So a single human viewing the same listing while authenticated *and* later while anonymous (different device, no login) double-counts. Spec mandates idempotency by `cookie/fingerprint` for anonymous within a day.
3. **No SEO web context** — listing-detail page in the buyer module fires `trackView`, but pages served via the F3 SSR/SEO sub-site (when it lands) need to hit the same endpoint. Currently out of scope until F3 starts; flag as a downstream consumer.

## Path to DONE

1. **Add 7-day aggregate fields.**
    - Backend: extend the seller dashboard response (`sellers.py:549-613`) with `total_views_7d` and `total_contacts_7d`, computed via two `COUNT(*)` queries against `listing_view_event` filtered by `viewed_at >= now() - interval '7 days'` and grouped by `event_type`. Per-card response in the listings endpoint similarly gets `views_7d` / `contacts_7d`.
    - Schema: prefer a single subquery joining `listing_view_event` to seller's listings; index `(listing_id, event_type, viewed_at desc)` already supports the filter.
    - Frontend: render under each card as a smaller second line "за 7 дней: N". Aggregate band shows two pairs: all-time / 7-day.
2. **Anonymous-viewer dedup.**
    - Decide: cookie-only or cookie+fingerprint. For .uz audience, cookie-only is privacy-cleaner; fingerprint adds noise and questionable lift. Recommend cookie + 24h TTL.
    - Backend: extend `listing_view_event` with a nullable `anon_id (varchar 64)`. Drop the `WHERE user_id IS NOT NULL` clause from the unique index and replace with `(coalesce(user_id::text, anon_id), listing_id, event_type, date(viewed_at))`.
    - Frontend: `trackView()` reads `anon_id` from cookie (set on first viewer visit), passes it on the POST.
3. **Document SEO consumer contract.** Once F3 starts, the SSR view handler must call `POST /listings/{id}/view` with `anon_id`. Spec only — implementation belongs to F3.
4. **No new dashboard endpoint** — extend `/sellers/me/dashboard` rather than add `/sellers/me/dashboard/7d`. Single response, two timeframes.

## Behaviour & invariants

- **Per-day idempotency holds for both auth and anon** after the index extension.
- **Self-views never count.** `is_self_view()` already returns true for owners; the patch must not regress this.
- **Contact event implies view event (if not already present that day).** No requirement to atomically combine — the user almost always views first.
- **Anonymous → authenticated transition within a day.** A user who views anonymously then logs in and views the same card same day produces two rows (different keys). Acceptable: the alternative (linking anon→user) is over-engineering for MVP.
- **`Listing.views_count` cached counter** stays in sync with the event table for authenticated users (transaction inserts the event and bumps the counter). For anonymous, the counter bumps without a row. After this spec lands, both paths bump the counter and write a row.

## Acceptance criteria

- `GET /sellers/me/dashboard` returns `total_views`, `total_contacts`, `total_views_7d`, `total_contacts_7d`, plus the existing favorites totals.
- Per-card response includes `views_count`, `contacts_count`, `views_7d`, `contacts_7d`.
- Cabinet card renders a second line "за 7 дней: N просмотров · M обращений" under the all-time chips.
- Anonymous viewers send `anon_id` (cookie) on `/view` and `/contact`; same `anon_id` viewing twice on the same day inserts one row.
- Self-view guard regression test passes (seller views own listing → no row, no counter bump).
- (After F3 lands) SSR pages call `/view` with `anon_id`; counters reconcile across web + TWA for anonymous users on the same browser.

## References

- `backend/alembic/versions/20260427_pre_listing_view_event.py` — event table + indexes.
- `backend/app/services/listing_views.py:16-32` — `is_self_view`.
- `backend/app/api/v1/listings.py:3221-3284` — view + contact endpoints.
- `backend/app/api/v1/sellers.py:549-613` — dashboard endpoint to extend.
- `frontend/src/shared/lib/viewTracking.ts:22-96` — tracker (needs `anon_id` extension).
- `frontend/src/modules/seller/pages/listings/ui/page/Page.tsx:280-326, 623-671` — UI to extend.
- [F108 master-record ranking](../../partial/easy/F108-master-record-ranking.md) — affects which listings get views, not unrelated.
