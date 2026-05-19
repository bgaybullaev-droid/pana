# B3 — Search surface unification

**Status:** PARTIAL — three real surfaces (`/`, `/browse`, `/listings`) plus a dead-redirect `/search`; **two parallel filter stores**; URL ↔ store sync is one-way only on the home page; SEO routes (F3) absent.
**Complexity:** HARD — touches the router, the buyer state layer, saved-searches, deep-linking, and the agreed grammar with F3. The biggest single dependency-hub task in Block B.
**Block-B V2.0 ref:** B3.
**Why now:** every other Block-B refactor (B5 drawer accordion, B6 aria sweep on filter chrome, B7 EmptyState reset-filters action) wants to talk to *one* canonical store. Without B3 they each touch a different surface.

## What's done

- **Three live surfaces:**
  - `/` — `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx`. Has the filter drawer in `BuyerLayout`, uses its own `$filters` store.
  - `/browse` — `frontend/src/modules/buyer/pages/browse/ui/page/Page.tsx`. Card-based infinite scroll, uses `$listings` from its own model.
  - `/listings` — `frontend/src/modules/buyer/pages/listings/ui/page/Page.tsx`. Grid masonry infinite scroll, separate model.
- **`/search` is a redirect** — `frontend/src/app/router/Router.tsx:150-152` preserves query params and redirects to `/`. Effectively dead.
- **Saved-searches feature** at `frontend/src/modules/buyer/feature/saved-searches/` — backend at `backend/app/api/v1/saved_searches.py` + `backend/app/services/saved_search_matcher.py`. Stores filters as JSON; works against whichever filter shape the home page emits today.
- **Filter store(s):**
  - `$filterState` — `frontend/src/modules/buyer/feature/filter/model/stores/index.ts:12`. Holds `{ sortingSelected, priceRange, regions }`. Powers the legacy `FilterPanel.tsx` (no longer the live consumer of the home drawer).
  - `$filters` — `frontend/src/modules/buyer/pages/home/model/stores/index.ts:14`. The live store for the home page. Holds `HomeFilters` shape with all ~19 filter keys.
  No sync between them.
- **One-way URL → store** — home page reads `useSearchParams()` at line 104 and hydrates state. Subsequent filter changes do NOT push back to the URL.

## What's missing

1. **Canonical surface unchosen.** Three pages back the same intent with different layouts. Spec recommends `/listings` as canon; the home `/` is more central in the actual user journey today.
2. **Two filter stores.** They diverge in shape (`HomeFilters` vs the feature store). Saved-searches matcher reads the home shape. Any reorganisation that splits them further makes the matcher brittle.
3. **One-way URL sync.** Filter changes don't update the URL. Sharing a filtered listing-list URL fails.
4. **`/listings` and `/browse` ignore URL params** entirely. Deep links to `/listings?district=chilanzar` show un-filtered content.
5. **No SEO route grammar.** Block F's F3 SEO infra is not started. B3's deliverable is to **agree on the URL grammar and parameterisation** so when F3 starts, the router and the store are already correctly shaped. No actual `/buy/apartment/chilanzar` routes ship in B3.
6. **Deep-link compat with D3** — `D3` (deep links from Telegram bot / marketing) is not in this spec but is referenced. Need to ensure the unified store hydrates from the same params D3 emits.
7. **Saved-search compatibility under store rename.** Saved searches store the filter object as JSON; if we rename keys during unification, old saved searches break. Migration path required.

## Path to DONE

This is the largest task in Block B. The order matters; do it in two PRs.

### PR 1 — store unification (no route changes)

#### Step 1 — pick the canonical store

Recommendation: keep **`$filters`** from the home page (`pages/home/model`). It already has the full `HomeFilters` shape, the saved-searches matcher uses it, and the home is the most-trafficked surface.

Move it to `frontend/src/modules/buyer/shared/state/filters/model.ts` (shared scope; not page-scoped). Re-export from the original location during the transition.

#### Step 2 — kill the second store

`frontend/src/modules/buyer/feature/filter/model/stores/index.ts` and the legacy `FilterPanel.tsx` are dead consumers; the live drawer lives in `home/Page.tsx`. Remove the feature store; remove `FilterPanel.tsx` (or replace with a thin re-export to the shared store).

#### Step 3 — bidirectional URL sync

Add a `urlSync` effect on the shared store:

```ts
// model.ts
sample({
  source: $filters,
  fn: (filters) => filterShapeToSearchParams(filters),
  target: createEffect((sp: URLSearchParams) => {
    const next = new URL(window.location.href);
    next.search = sp.toString();
    window.history.replaceState({}, "", next.toString());
  }),
});
```

And on mount of any consumer page, hydrate from URL:

```ts
useEffect(() => {
  const sp = new URLSearchParams(window.location.search);
  filtersHydratedFromUrl(searchParamsToFilterShape(sp));
}, []);
```

`filtersHydratedFromUrl` is a new event on the store. Use `replaceState` (not `pushState`) so back-button doesn't accumulate filter-change history.

#### Step 4 — `/listings` and `/browse` adopt the same store

Replace each page's local `$listings` model with one that reads from the shared `$filters` store. The page-specific concerns (grid vs cards) stay in the page; the *what to fetch* moves to shared.

#### Step 5 — saved-search matcher compat

`backend/app/services/saved_search_matcher.py` already reads the home filter shape. Verify no key rename is required. If any (e.g. `$filterState.regions` → `$filters.region`), write a one-shot data migration that rewrites old saved-search JSON.

### PR 2 — route consolidation

#### Step 6 — pick the canonical route

Recommendation: keep **`/`** (home) as the canonical search surface. It already has the drawer, it's the deepest-linked page, it's where saved searches land. `/listings` and `/browse` either redirect or get repurposed (`/listings` could be the "all listings, no filter prefilter" view if product wants to keep it).

Alternative (per spec): `/listings` is canon, `/` redirects. That requires moving the drawer; bigger surgery.

#### Step 7 — redirect dead routes

```tsx
<Route path="/search" element={<Navigate to="/" replace />} />
<Route path="/browse" element={<Navigate to="/" replace />} />
<Route path="/listings" element={<Navigate to="/" replace />} />
```

Preserve query params via the Navigate's `to={ search: window.location.search }` pattern.

#### Step 8 — agree on F3 SEO grammar

Document in this spec (and link from F3 when it starts). Recommended grammar:

- `/buy/<property_type>/<region>` — base SEO route, e.g. `/buy/apartment/tashkent`.
- `/buy/<property_type>/<region>/<district>` — nested.
- `/buy/<property_type>/<region>/<district>/<rooms>-rooms` — most specific.
- Query params (`?price_max=…`, `?condition=…`) extend the SEO base; they do **not** create new SEO routes. Search engines see only the base route as canonical.

Mapping from URL → store is symmetric. The `filterShapeToSearchParams` / `searchParamsToFilterShape` helpers in Step 3 know how to handle both query params and SEO path segments.

#### Step 9 — router scaffolding for F3 (no rendering)

Add the `<Route path="/buy/:propertyType/:region/:district?/:rooms?" />` pattern in the buyer router but route it to the same home page component. F3 will replace this with a SSR-served page later; today it's a client-side render that hydrates the store from the path. This means F3 has a one-line change at handover, not a multi-file refactor.

## Behaviour & invariants

- **One filter store** — `$filters` in `modules/buyer/shared/state/filters`. All consumers read/write through it.
- **Bidirectional URL sync** — every filter change replaces the URL; every URL load hydrates the store.
- **`replaceState`, not `pushState`** — filter chips are not navigation events; back button shouldn't have to undo filter selections one-by-one.
- **Saved searches store the canonical filter shape** — no per-route variant.
- **SEO routes hydrate the same store** as query-param routes. Path segments + query params combine; query params win on conflict.
- **Drawer has no local state** — every input is a controlled component bound to the store.

## Acceptance criteria

- `grep -rE "createStore.*[Ff]ilters|filtersChanged" frontend/src/modules/buyer/{feature,pages}` returns hits in **one** location only (the shared store).
- Loading `/` with `?district=chilanzar&rooms=2` produces a filtered list; the drawer reflects the filters; saving as a saved search round-trips back to the same URL.
- Changing a filter in the drawer pushes the URL via `replaceState`; reloading the page restores the same filter state.
- `/search`, `/browse`, `/listings` all redirect to `/` with query params preserved.
- A pre-B3 saved search loads correctly post-B3 (data-migration verified).
- A test deep-link `/buy/apartment/tashkent/chilanzar` hydrates the store with `property_type=apartment, region=tashkent, district=chilanzar`.
- Saved-search matcher tests still pass.

## Edge cases

- **Old browser tabs** — a tab open with `/listings` while the redirect lands navigates on the next interaction. Acceptable.
- **Deep-link with both SEO segments AND conflicting query params** — query params win. e.g. `/buy/apartment/tashkent/chilanzar?district=mirzo` → final `district=mirzo`. Document loud.
- **Empty filters** — URL is clean (`/`), no `?` suffix. `replaceState` cleans up trailing `?`.
- **Filter-no-results** — surfaces the `EmptyState` with `variant="search-no-results"` (B7); reset action clears the store, which clears the URL.
- **Saved-search collision with URL** — if the user opens a URL-filtered list, then loads a saved search, the saved search wins (replaces store + URL).
- **TWA context** — query params still work; SEO grammar isn't needed (TWA isn't indexed). Use the same code path; the SEO segments don't appear because TWA always opens with query params.
- **Hash-based routing** — confirm the app uses path-based, not hash-based; if hash-based, URL-sync logic differs (not the case in this codebase).

## Production risks

- **Saved-search data migration** — biggest risk. Write the migration as idempotent: it inspects each row's `payload.filters`, renames keys if needed, leaves it alone otherwise. Test against a copy of production data before deploying.
- **SEO crawler vs client-side hydration** — the client-side `Navigate` redirects (Step 7) are invisible to crawlers. Set up server-side 301s in nginx for `/search`, `/browse`, `/listings` so search engines see the canonical URL. Coordinate with infra.
- **D3 deep links** — if D3 hardcodes `/listings?…` in marketing materials, the redirect catches them but the URL-history footprint is wrong. Re-issue marketing links pointing to `/`.
- **`useSearchParams` reconciliation race** — if both URL → store and store → URL fire on the same tick, you can get a feedback loop. Guard with a "hydrating" flag during the initial mount.

## Dependencies

- **Upstream:**
  - A2 (mockup-section cleanup — done; required so we don't unify nerfed UI).
  - A6 (i18n foundation — done; needed for filter labels).
- **Downstream:**
  - B5 (filter accordion sits on the unified store).
  - B7 (filter-no-results uses unified store's `clearFilters`).
  - F3 (SEO routes consume the URL grammar agreed here).
  - D3 (deep links land on the canonical surface).
- **Critical-path block** for B5 (B5 should land after B3).

## Open questions

1. **Canonical route — `/` or `/listings`?** Recommendation: `/`. Confirm.
2. **Should `/listings` redirect, or be repurposed to "no-filter all-listings"?** Defer to product.
3. **F3 grammar finalisation** — recommended above; needs F3 owner sign-off before we land Step 8/9 scaffolding.
4. **Saved-search migration trigger** — at deploy time (one-shot script) or lazy on first read? Recommend one-shot; it's idempotent.
5. **`pushState` vs `replaceState`** — replaceState recommended. Confirm UX expectation.
6. **Server-side redirects for SEO** — owner of nginx config?

## References

- `frontend/src/app/router/Router.tsx:150-152` — `/search` redirect.
- `frontend/src/modules/buyer/app/router/Router.tsx` — `/`, `/browse`, `/listings` mounts.
- `frontend/src/modules/buyer/pages/home/model/stores/index.ts:14` — `$filters` (canonical candidate).
- `frontend/src/modules/buyer/feature/filter/model/stores/index.ts:12` — `$filterState` (legacy, to remove).
- `frontend/src/modules/buyer/feature/filter/ui/FilterPanel.tsx` — legacy panel, to remove or thin out.
- `frontend/src/modules/buyer/pages/{browse,listings}/ui/page/Page.tsx` — pages to migrate or redirect.
- `backend/app/api/v1/saved_searches.py`, `backend/app/services/saved_search_matcher.py` — saved-search backend; migration target.
- [A2](../../block-a/easy/A2-mockup-filters.md), [B5](../medium/B5-progressive-filter-disclosure.md), [B7](../easy/B7-empty-state-unification.md), [F3 — TBD], [D3 — TBD].
