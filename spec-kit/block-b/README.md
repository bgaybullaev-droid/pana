# Block B — UX-Polish Specs (V2.0)

Block B is seven UX-polish tasks for the pre-launch run. Unlike Block A, these are **not** technically launch-blockers — the product runs without them — but each leak in the first 30 seconds of a new user's session compounds into "this feels rough". V2.0 inherits Block A's architectural shifts: AI-generated descriptions live in `Listing.ai_description_*`, the parser captures structured params + raw text, and the buyer feed already gates on the new statuses.

This subtree is organised by **complexity only**, mirroring `block-a/`:

```
spec-kit/block-b/
├── README.md
├── EXECUTION_PLAN.md
├── READINESS_REPORT.md
├── easy/
│   └── B7-empty-state-unification.md
├── medium/
│   ├── B1-inline-characteristics.md
│   ├── B2-text-contrast-overlay.md
│   ├── B4-seller-register-unification.md
│   ├── B5-progressive-filter-disclosure.md
│   └── B6-aria-labels-sweep.md
└── hard/
    └── B3-search-surface-unification.md
```

## Status snapshot at write-time (real code, not spec)

| Task | Complexity | Spec status | One-line essence |
|---|---|---|---|
| [B1 — Inline characteristics](medium/B1-inline-characteristics.md) | MEDIUM | NOT STARTED | Add 4-pill block (condition / wall / building / key feature) under chips. Strictly structured params. **Schema gap:** no `year_built` column. |
| [B2 — Text contrast](medium/B2-text-contrast-overlay.md) | MEDIUM | PARTIAL | Gradient + text-shadow already wired; AI text NOT wired into Krutilka, multi-locale length not handled, long UZS prices not shortened. |
| [B3 — Search unification](hard/B3-search-surface-unification.md) | HARD | PARTIAL | Three real surfaces + dead `/search` redirect. Two parallel filter stores. One-way URL sync. F3 grammar undecided. |
| [B4 — Seller register](medium/B4-seller-register-unification.md) | MEDIUM | PARTIAL | Both pages exist, same backend, divergent UX/redirect/auth-guard; `/seller/register` lacks auth guard. |
| [B5 — Filter disclosure](medium/B5-progressive-filter-disclosure.md) | MEDIUM | NOT STARTED | Drawer is a flat ~19-filter list. Active-count exists at icon level only. |
| [B6 — Aria-labels](medium/B6-aria-labels-sweep.md) | MEDIUM | PARTIAL | 0 of 18 sampled icon-only buttons have `aria-label`. No `aria.*` i18n namespace yet. |
| [B7 — EmptyState](easy/B7-empty-state-unification.md) | EASY | PARTIAL | Component exists, used in 3 of ~8 places. ~5 inline duplicates. Missing `variant` prop. |

## Distribution

- **Easy: 1** (B7)
- **Medium: 5** (B1, B2, B4, B5, B6)
- **Hard: 1** (B3)

## Dependency graph

```
                  ┌────────────────┐
                  │  A6 i18n base  │ ← done
                  │  (locales,     │
                  │   formatNumber)│
                  └───────┬────────┘
                          │
       ┌──────────────────┼─────────────────┬───────────────┐
       ▼                  ▼                 ▼               ▼
   B6 (a11y)         B7 (EmptyState)    B5 (filter        B2 (Krutilka
                                         accordion)        AI text +
                                                            length)
       │                                     ▲
       └─────────────┐                       │
                     ▼                       │
             B3 (canonical store) ───────────┘
                     │   (B5 should land after B3)
                     │
                     ├──── coupled with F3 (SEO grammar; F3 not started)
                     │
                     └──── D3 (deep links; out of Block B)


  B1 (pills) ─── reads structured params only
                 ── coupled visually with B2 (Krutilka overlay area)

  B4 (register) ── stand-alone, light coupling to A1/A4 (done)
```

### Dependency facts (see each spec for full detail)

| Task | Hard upstream deps | Soft upstream | Blocks |
|---|---|---|---|
| **B1** | A6 (done), A7 (done) — both already shipped | — | F3 SEO `additionalProperty` (later) |
| **B2** | A7 / F1 AI columns (done) | B1 (overlay layout coordination) | — |
| **B3** | A2 (done) — mockup cleanup | A6 (done) | B5, B7 reset action, F3, D3 |
| **B4** | A1, A4 (done) | — | none |
| **B5** | A2 (done), B3 (preferred to land first) | — | none |
| **B6** | A6 (done) | — | none — touches every UI module |
| **B7** | A6 (done) | — | B5 (counts use the new variant), B3 (filter-no-results) |

### V1 spec-kit cross-references

- B3 has no V1 sibling; the saved-searches feature in `done/medium/05-saved-searches.md` is upstream consumer-protected work that B3 must not break.
- B7 inherits from `partial/easy/seller-dashboard-counters.md`'s precedent for empty/skeleton patterns.
- B1's parser-quality dependency is documented in `done/hard/02-crawler-ingestion.md`.

## V2.0 invariants the specs assume

1. **B2C never shows `raw_text`.** The Krutilka slide reads `ai_description_<locale>` first; `description` is a fallback only; `raw_text` is never user-facing.
2. **Filters and pills both read structured params, not AI text.** B1's pills and B5's filters are consistent — `condition` is in the chip if `condition` is in the column, regardless of what the AI text says.
3. **Single filter store** post-B3. Saved searches, the home drawer, the URL, and any future SEO route all read/write to it.
4. **i18n at write time.** Every new string in B1–B7 lands in ru / uz / uz-cyrl day one; no later cleanup pass.
5. **Decorative icons are aria-hidden; interactive icons get a localised aria-label.**

## Suggested execution order

See [EXECUTION_PLAN.md](EXECUTION_PLAN.md) for full sequencing, parallelism, and critical path. High-level:

1. **B7** (easy) — half-day; ships clean foundation for empty branches in the rest of the block.
2. **B6** (medium) — i18n namespace + sweep; runs in parallel with everything else.
3. **B3** (hard) — store unification PR1, then route consolidation PR2; the pacing constraint.
4. **B5** (medium) — accordion wrap; comes *after* B3 so it sits on the unified store.
5. **B1** + **B2** (medium each) — coupled pair; B1's pill row dictates B2's gradient height. Land together.
6. **B4** (medium) — stand-alone; can ship anywhere in the timeline.

## Open questions tracked in specs

- B1: add `year_built` column or drop the year pill until later? (Step 0 in B1.)
- B2: compact UZS thresholds? Locale fallback order for missing AI translations?
- B3: canonical route `/` or `/listings`? F3 SEO grammar sign-off owner?
- B4: canonical path `/seller/register` or `/become-seller`? Post-success redirect target?
- B5: section split confirmation; sort-order placement?
- B6: aria namespace location (`common.json` vs per-module)?
- B7: extend prop API backward-compatibly or break? (Recommended: extend.)

## Conventions

- File paths use repo-root-relative form.
- Line numbers reflect state at write-time (May 2026); treat as starting points.
- Cross-spec links: `../<complexity>/X.md` for same-state, `../../block-a/<complexity>/X.md` for Block A.
- Every spec is independently readable. No "see above" — link instead.
