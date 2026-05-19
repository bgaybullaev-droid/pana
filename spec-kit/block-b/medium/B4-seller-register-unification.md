# B4 — Unified seller-registration path

**Status:** PARTIAL — both pages exist, both call the same backend endpoint; UX, copy, post-redirect, and auth-guard diverge.
**Complexity:** MEDIUM — the merge itself is small (single page + redirect + entry-point sweep), but the divergent post-registration redirects and the missing auth guard need careful handling.
**Block-B V2.0 ref:** B4.
**Why now:** the two paths confuse users and split analytics. Both are mounted in production routes today.

## What's done

- **Both pages mount and work end-to-end:**
  - `/become-seller` — `frontend/src/modules/buyer/pages/become-seller/ui/page/Page.tsx`. Lives in `BuyerLayout`. Orange-gradient hero, three-benefit list, fields = `phone` (required) + `company_name` (optional). "Or via Telegram bot" fallback link.
  - `/seller/register` — `frontend/src/modules/seller/pages/register/ui/page/Page.tsx`. Standalone full-page hero (blue), benefit cards, Mantine `useForm` with phone regex. No Telegram fallback link.
- **Same backend endpoint:** both call `POST /sellers/register` via `registerAsSellerFx` at `frontend/src/modules/seller/shared/state/model/effects/index.ts:12-14`.
- **Auth state coverage in `/become-seller`:** `useAuth()` redirects to `/auth` when unauthenticated and to `/seller/dashboard` when the user is already a seller.

## What's missing

1. **Two parallel UIs.** Different hero, different copy, different validation strategy (manual vs Mantine `useForm`). User confusion + maintenance cost.
2. **Different post-success redirects.**
   - `/become-seller` → `/seller/create` (start adding a listing).
   - `/seller/register` → `/seller/dashboard` (overview).
   Spec wants ONE redirect: into the cabinet, with the **Found** page if there are matched parser listings (Block A1), otherwise the empty-cabinet CTA.
3. **`/seller/register` has no auth guard.** Block A's auth flow assumes the user is logged-in via Telegram before they hit the registration form. `/become-seller` enforces this; `/seller/register` does not. Anonymous direct-link click → form posts → backend rejects, ugly toast.
4. **Telegram bot fallback link is missing on `/seller/register`.** Some users complete onboarding via the bot's `/become_seller` handler instead. The link is a safety net.
5. **Async parser-search trigger after registration.** Spec wants the backend to trigger the phone-suffix search (per A1 / A4) so Found is populated by the time the user lands. Today the backend `/sellers/register` doesn't enqueue that task.
6. **Entry points.** Buttons / banners across the app point to one or the other inconsistently.
7. **Saved-link compatibility.** Telegram saved messages may contain either path. Removing one without a redirect breaks them.

## Path to DONE

### Step 1 — pick the canonical path

Recommendation: keep **`/seller/register`** as canon (more "selling" hero, Mantine form validation already in place, cleaner standalone surface). The other path (`/become-seller`) becomes a redirect.

### Step 2 — port what's good from `/become-seller`

- The Telegram bot fallback link (`https://t.me/${BOT_USERNAME}`) — append to `/seller/register` under the form.
- The auth-guard pattern (`useAuth()` redirect) — port to `/seller/register` so anonymous click is sent to `/auth?next=/seller/register`.

### Step 3 — converge the post-success redirect

Both call sites of `registerAsSellerFx` should redirect to **the same place**. Implementation:

```ts
// frontend/src/modules/seller/shared/state/model/effects/index.ts (or call site)
// After successful seller creation, fetch /sellers/me/crawled/stats and route accordingly.
const stats = await fetchSellerCrawledStats();
const target = stats.total_pending > 0 ? "/seller/found" : "/seller/dashboard";
navigate(target, { replace: true });
```

This satisfies the spec ("Found if found, else empty cabinet") and is the same logic for both old paths once unified.

### Step 4 — redirect the legacy path

`/become-seller` route handler returns `<Navigate to="/seller/register" replace />`. Query parameters (e.g. `?from=banner`) are preserved.

### Step 5 — backend trigger

`backend/app/api/v1/sellers.py register_seller` — after successful seller creation, enqueue a parser-search task by phone. The phone-match query already exists in `seller_crawled_listings.py` (used by Block A's Found endpoints). Wrap it in a Celery task or run it inline if cheap.

```python
# In register_seller, after db.commit():
from app.workers.tasks.crawled_match import notify_sellers_of_crawled_listing
# Find any unclaimed crawled listings whose phone matches the new seller
# and enqueue the A4 fanout for each.
```

If A4's task is the right surface, no new code is needed beyond invoking it. If a new task is needed, add `prime_seller_crawled_index(seller_id)` and call it.

### Step 6 — entry-point sweep

`grep -rn "/become-seller\|/seller/register" frontend/src` — every button / `<Link>` is updated to point to `/seller/register`. The `/become-seller` redirect handles forgotten cases.

### Step 7 — bot deep-link (optional polish)

`backend/app/bot/handlers.py` — the `/become_seller` bot command can deep-link into the Mini App with `?startapp=register` so the bot path lands on the same UI.

## Behaviour & invariants

- **One canonical URL** — `/seller/register`. Everything else either redirects there or links to it.
- **Auth precedes form** — anonymous click → `/auth?next=/seller/register` → back to form when authenticated.
- **Already-seller short-circuit** — if `useAuth().user.is_seller` is true, redirect to `/seller/dashboard` with a toast "You're already registered."
- **Post-success redirect uses live data** — checks for matched crawled listings and routes accordingly.
- **Parser-search runs async** — registration response time is unaffected by the search; results show in Found within minutes (per A4).

## Acceptance criteria

- `grep -r "/become-seller" frontend/src` returns only the redirect-route declaration; all other usages have been updated to `/seller/register`.
- Hitting `/become-seller` → 302 / client-side `<Navigate>` to `/seller/register` with query params preserved.
- Anonymous click on `/seller/register` lands on `/auth` with `next=/seller/register`; after auth, returns to the form.
- Already-seller hitting `/seller/register` lands on `/seller/dashboard` with a toast.
- Successful registration with matched crawled listings → `/seller/found`. Without → `/seller/dashboard`.
- The Telegram bot fallback link is present on the canonical page.
- Backend `/sellers/register` triggers the parser-search task (verifiable in logs / A4 notification appearing in seller's bot).

## Edge cases

- **Form draft on navigation away.** User starts filling, taps a banner, comes back — local state preserved (Mantine `useForm` + tab visibility). Don't persist to backend (out of MVP scope).
- **Phone already used by another seller.** Backend rejects with 400; toast surfaces the message in localised form (no Russian leak — A6 enforced this for backend errors).
- **Network timeout during registration.** Form stays mounted; error toast; user retries with the same data.
- **User tries `/seller/register` while the bot's `/become_seller` flow is still in progress.** Both paths converge on the same backend endpoint; the duplicate is rejected by the "already registered" guard.
- **Race with A4 push.** If parser-search finds matches very quickly, an A4 push could arrive *before* the user sees the Found page. That's fine — the push is informational, the cabinet still shows the same listings.

## Production risks

- **Saved Telegram links** — users may have `/become-seller` URLs in saved messages from before launch. The redirect protects them. Remove the redirect only after 2-3 months post-launch.
- **Analytics rewiring** — if Mixpanel / Plausible tracks "registration" by URL path, the merge changes the dimension. Update before the deploy.
- **Backend trigger** — if the parser-search task is heavy, calling it on every registration could pressure the worker. Wrap in `.delay()` (Celery) so it's async; keep the response fast.

## Dependencies

- **Upstream:** A1 (claim/reject works against found listings — done), A4 (`notify_sellers_of_crawled_listing` Celery task — done).
- **Coupled:** B7 (success post-registration empty-cabinet uses unified `EmptyState`).
- **Blocks:** none.

## Open questions

1. **Canonical path** — `/seller/register` (recommended) or `/become-seller`? Spec leaves it open; recommend `/seller/register` for the better hero.
2. **`/seller/create` — does it still make sense as a redirect target post-registration when there are no found listings, or is `/seller/dashboard` clearly better?** Recommend dashboard (overview before action). Confirm.
3. **Backend parser-search trigger** — re-use A4's existing task or add a new `prime_seller_index`? Recommend re-use; A4 already does the right thing.

## References

- `frontend/src/modules/buyer/pages/become-seller/ui/page/Page.tsx`
- `frontend/src/modules/seller/pages/register/ui/page/Page.tsx`
- `frontend/src/modules/seller/shared/state/model/effects/index.ts:12-14` — `registerAsSellerFx`.
- `frontend/src/modules/buyer/app/router/Router.tsx:161` — `/become-seller` route.
- `frontend/src/modules/buyer/app/router/Router.tsx:172` — `/seller/register` route.
- `backend/app/api/v1/sellers.py` — `register_seller` endpoint.
- [A1](../../block-a/medium/A1-claim-reject-v2.md), [A4](../../block-a/hard/A4-push-notifications.md), [B7](../easy/B7-empty-state-unification.md).
