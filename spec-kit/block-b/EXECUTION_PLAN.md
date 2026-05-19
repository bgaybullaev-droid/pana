# Block B — Execution Plan

This plan orders the seven Block-B specs by **real dependency**, anchored to the audit of the live code (mid-May 2026). Block A V2.0 has shipped — all `Listing.ai_description_*` columns are populated by the F1 worker, the unified i18n foundation (`uz-cyrl`, `formatNumber`, ICU plurals) is live, and A8 admin sources is online.

The plan is split into two PR-sized waves so reviewers can verify each step against the running app.

## Dependency map (collapsed for execution)

| Task | Hard deps (must land before) | Soft deps | Blocks (delays these) |
|---|---|---|---|
| **B7** EmptyState unification | — | A6 (i18n) | B5 (per-section counts re-use the new variant), B3 (filter-no-results action) |
| **B6** Aria-label sweep | A6 i18n | — | none — touches every UI module |
| **B1** Inline 4-pill block | A6, A7 (done); schema decision on `year_built` | — | F3 SEO `additionalProperty` (later) |
| **B2** Text-contrast overlay | A7 / F1 AI columns (done) | B1 (overlay vertical rhythm) | — |
| **B4** Seller-register unification | A1, A4 (done) | — | none |
| **B3** Search surface unification | A2 (done) | A6 (done) | **B5**, B7 reset-filters wiring, F3, D3 |
| **B5** Progressive filter disclosure | A2 (done); **B3** preferred to land first | — | none |

A6 is shared upstream for *every* B task (every spec adds new strings). A7 is needed by B1 (params from parser) and B2 (AI text). A2 cleared the mockup-section question for B3 and B5.

## Execution waves

### Wave 1 — independent, parallelisable

These three can land in any order, by any developer, in parallel. None block each other.

| Task | Owner suggestion | Est. dev-days | Notes |
|---|---|---|---|
| **B7 — EmptyState** | FE | 1 | Extends one component, migrates 5 inline sites. Lowest blast radius. Establishes `variant` API used by B3 reset-filters action. |
| **B6 — Aria-label sweep** | FE | 1.5 | Three sub-PRs by module (buyer, seller, admin) to keep diff sizes small. New `aria.*` namespace in `common.json` × 3 locales. |
| **B4 — Seller register** | FE + light BE | 1.5 | Frontend page redirect + auth-guard add. Backend: re-use `notify_sellers_of_crawled_listing` (A4) on `register_seller` success. |

**Why this wave is first:** none of these touch the filter store or the canonical search route. B3 hasn't landed; these don't care. Each sets up vocabulary (variants, aria keys) that later waves reuse.

### Wave 2 — store unification

Single track, single owner. Two PRs.

| Task | Owner | Est. dev-days | Notes |
|---|---|---|---|
| **B3 PR1 — store unification** | FE | 2 | Merge `$filterState` + `$filters`. Move to `modules/buyer/shared/state/filters/`. Bidirectional URL sync. Saved-searches matcher compat verified. **No route changes yet.** |
| **B3 PR2 — route consolidation + F3 grammar scaffold** | FE | 2 | Pick canonical (`/` recommended). Redirect `/search`, `/browse`, `/listings`. Mount F3-grammar route placeholder (no SSR). Coordinate with infra for nginx 301s. |

**Why split:** PR1 is internal refactor — easier to review, easier to revert. PR2 has user-visible URL effects and needs server-side coordination (301 rules).

**Critical-path role:** B5 cannot start until both PRs land.

### Wave 3 — coupled visual pair (B1 + B2)

These should land in one PR or in two same-day PRs because the Krutilka overlay vertical rhythm is shared.

| Task | Owner | Est. dev-days | Notes |
|---|---|---|---|
| **B1 — Inline pills** (Step 0c chosen: defer `year_built`) | FE | 2 | Adapter extension + three card components. If product picks Step 0a (add `year_built`), add 0.5 d for migration + LLM extractor update. |
| **B2 — Krutilka AI text + length** | FE | 1 | Wire `ai_description_<locale>`, add `formatPriceShort`, locale-aware font sizing. |

**Coordination point:** the gradient height in `ListingSlideContent.tsx:213-222` is parameterised once in B2 and consumed by B1's pill row. Decide the CSS variable name in the first PR; the second adopts it.

### Wave 4 — filter accordion

| Task | Owner | Est. dev-days | Notes |
|---|---|---|---|
| **B5 — Progressive disclosure** | FE | 1.5 | Wraps the existing flat list in `Mantine.Accordion`. Per-section counts. Auto-expand on saved-search load. **Depends on B3 landing (Wave 2).** |

## Parallelisation scenarios

### 1 dev (sequential, ~14 dev-days)

```
Day 1     B7 EmptyState
Days 2-3  B6 aria sweep (split into 3 PRs)
Day 4     B4 seller register
Days 5-6  B3 PR1 store unification
Days 7-8  B3 PR2 route consolidation
Days 9-10 B1 inline pills
Day 11    B2 contrast + AI text
Days 12-13 B5 filter accordion
Day 14    Buffer / acceptance pass
```

≈ 3 weeks calendar at 5 d/wk.

### 2 devs (FE-leaning + FE/BE light, ~9 dev-days each)

```
Dev A (UX-leaning)               Dev B (state-leaning)
Day 1   B7 EmptyState             Day 1   B6 aria namespace + buyer
Day 2   B6 seller + admin sweep   Day 2   B4 seller register (BE shim)
Day 3   B1 pills (adapter)        Days 3-4 B3 PR1 store unification
Day 4   B2 Krutilka contrast      Days 5-6 B3 PR2 route consolidation
Days 5-6 B1 pills (cards)        Day 7   B5 accordion (after B3)
Day 7   B5 polish + i18n          Days 8-9 buffer / a11y review

```

Both devs sync at end of Day 6 (B3 done). Calendar ~2 weeks.

### 3 devs (most parallel, ~7 dev-days each)

```
Dev A (visuals)         Dev B (a11y/copy)        Dev C (state)
Day 1   B7              Day 1   B6 buyer         Days 1-2 B3 PR1
Days 2-3 B1 + B2        Day 2   B6 seller/admin  Days 3-4 B3 PR2
Day 4   B5 accordion    Day 3   B4 register      Day 5   F3 grammar review
Day 5   final polish    Day 4   buffer           Day 6   buffer
```

≈ 1.5 weeks calendar with daily standup; B5 starts on Day 4 once B3 PR2 is merged.

## Critical path

```
A6 (done) ── B3 PR1 ── B3 PR2 ── B5
                       ▲
                       │
               (server-side 301 coordination)
```

Cumulative 5 dev-days for the longest chain. Adding ops time for nginx 301 work makes it ~5–6 calendar days. Everything else (B7, B6, B1, B2, B4) parallelises off this chain.

## FE / BE / infra split

| Task | Frontend | Backend | Infra |
|---|---|---|---|
| B7 | yes | — | — |
| B6 | yes | — | — |
| B1 | yes | optional `year_built` migration if Step 0a picked | — |
| B2 | yes | — | — |
| B3 | yes (heavy) | possible saved-search migration | nginx 301s for `/search`, `/browse`, `/listings` |
| B4 | yes | small enqueue tweak in `register_seller` | — |
| B5 | yes | — | — |

## Operational dependencies

- **F3 SEO infra (Block F)** — B3 PR2 leaves F3-shaped route scaffolding but doesn't ship a real SSR. F3 is responsible for the actual server-side rendering and the schema.org markup. **Coordinate URL grammar before B3 PR2 lands.**
- **D3 deep links** — marketing materials must point at the canonical route after B3 PR2. Re-issue any `/listings?…` links pre-launch.
- **Saved-search migration** — if any filter key is renamed during B3 PR1, run the idempotent migration script as part of the deploy. Test against a copy of production data first.
- **Native-speaker review of new uz / uz-cyrl strings** — the aria namespace (B6, ~25 keys × 3 locales = 75 strings) and the new B5 section labels need review. This is operational work (founder / translator), not engineering, but it's a launch-readiness item.

## Rollout risks

| Risk | Mitigation |
|---|---|
| Saved searches break post-B3 | Idempotent migration; backup before deploy |
| SEO crawler hits `/listings` before nginx 301 ships | Land nginx 301 in same window as B3 PR2 |
| `year_built` adds extraction-quality variance | Defer to Step 0c; Block A metrics measure coverage first |
| Mass aria-label diff conflicts with active feature work | Split B6 into 3 module-scoped PRs; merge often |
| Krutilka AI-text fallback shows ru text in uz-cyrl locale | Document fallback order; surface to support team |
| Filter accordion regression on Android 8/9 | Performance test in Wave 4; lazy-mount panels if needed |
| Saved-search matcher subtly drifts after store unification | Backend tests on `saved_search_matcher.py` before B3 PR1 lands |
| `/become-seller` saved Telegram links 404 | Permanent redirect in B4 (kept ≥ 3 months post-launch) |

## Estimated dev-days (single-dev, sequential)

| Wave | Tasks | Days |
|---|---|---|
| 1 | B7 + B6 + B4 | 4 |
| 2 | B3 PR1 + PR2 | 4 |
| 3 | B1 + B2 | 3 |
| 4 | B5 | 1.5 |
| **Total** | | **~12.5** |

Parallel-3-dev calendar: ~7-8 days.

## Don't repeat the Block-A mistake

Block A started shipping code before the dependency map was complete; that left a few seams (e.g. the `year_built` field that Block B now exposes as a gap). For Block B:

1. **Don't start B5 before B3 lands** — B3's unified store is the substrate for the accordion. Building B5 on the legacy split stores will be thrown away.
2. **Don't ship B1 before product confirms `year_built`** — adding the migration later means a second rollout of the LLM extractor.
3. **Don't sweep B6 in one giant PR** — split by module to keep diff size reviewable; reduces conflict surface with concurrent feature work.
4. **Don't merge B3 PR2 without nginx 301 coordination** — server-side redirects are the SEO equivalent of the canonical-tag question; client-side `Navigate` doesn't satisfy crawlers.
5. **Treat B7's variant API as a contract for B3 and B5** — name it once, then both downstream specs adopt it; avoid drift.

## Mid-block sanity checkpoints

After each wave, verify:

- **After Wave 1:** the `aria.*` namespace lints clean across all three locales; the four EmptyState consumers (3 existing + new home filter-no-results) render without visual regression.
- **After Wave 2 PR1:** saved-searches end-to-end test (create, list, apply, delete) passes; URL ↔ store sync round-trips.
- **After Wave 2 PR2:** crawler-test of `/listings → /` redirect via cURL; nginx 301 in place.
- **After Wave 3:** Krutilka in three locales on a 360 px viewport — no text wrap, no clipping.
- **After Wave 4:** open the drawer with a saved search containing both Основные and Параметры объекта filters — both expand automatically; per-section count badges match.

## Deferred to Block C / D / F

- **F3 SEO SSR** — scaffolding lands in B3 PR2; full SSR is F3.
- **D3 deep links** — re-issue marketing URLs; not in Block B.
- **Native-speaker review of seeded `uz-cyrl`** — operational, not engineering.
- **B6 WCAG AA contrast / size** — beyond WCAG-A baseline B6 covers; defer.
- **Filter persistence between sessions (B5)** — explicit "out of MVP" per spec.
