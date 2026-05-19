# Block B — Implementation Readiness Report

Snapshot taken after Block A V2.0 fully shipped (May 2026), with the live DB at `prh_source_metric_and_seed → pri_source_metric_notified` head and all admin-sources / F1 / A4 plumbing live.

This report tells you, per task, whether implementation can start **today**, what gates it, and what the highest-risk seam is.

## Per-task readiness

### B7 — EmptyState unification — **READY**

- All upstream deps shipped (A6 i18n + A3 EmptyState consumers + Block A's empty-state precedent).
- Component to extend exists; five inline migration targets identified by file:line.
- No product decision pending; the `variant` enum is small and self-contained.
- **Risk:** trivial. Visual drift across the 5 migration sites is the only watch-out; before/after screenshots cover it.
- **Can start:** today. Junior FE work.

### B6 — Aria-label sweep — **READY**

- A6 i18n foundation is in place (3 locales).
- Audit identified ~50+ icon-only buttons; 0 carry labels today.
- New `aria.*` namespace can be added to `common.json` without DB or backend touch.
- **Risk:** PR-size management. Land in 3 PRs (buyer / seller / admin) to avoid conflict with concurrent feature work.
- **External dep:** native-speaker review of the new uz / uz-cyrl strings before launch (operational, not engineering).
- **Can start:** today. Mid-level FE.

### B4 — Seller register unification — **READY**

- Both pages exist, same backend endpoint already used by both.
- A1 + A4 (claim flow + crawled-match push) are live; B4's "trigger parser-search on register" reuses A4's existing `notify_sellers_of_crawled_listing` task.
- **Risk:** nginx-side / saved-link compatibility — `/become-seller` URLs in saved Telegram messages need to keep working. Solution is a permanent client-side `<Navigate>` (and ideally a server-side 301 next time nginx is touched).
- **Open:** canonical path choice (`/seller/register` recommended). One-line product call.
- **Can start:** today, after the canonical-path call. Mid-level FE + small BE PR.

### B1 — Inline characteristics block — **CONDITIONALLY READY**

- A6 + A7 (i18n + parser quality + raw_text + AI columns) all shipped.
- T-020 adapter exists and is the right place to extend.
- **Schema gap:** `year_built` column does not exist on `Listing`, `TelegramListing`, or `OLXListing`. Spec lists it as the first pill.
- **Open product decision:** add `year_built` migration now (Step 0a) or defer (Step 0c, ship without year)? Recommendation in spec is 0c; needs sign-off.
- **Other open:** for apartments, prefer `wall_material` or `building_type` when both are set?
- **Risk:** adapter regression on existing chips. Ship with snapshot tests on `getCardContent()` output.
- **Can start:** as soon as the year-built decision is made. Mid-level FE.

### B2 — Text contrast over photo — **READY**

- A7 / F1 shipped — `ai_description_<locale>` columns exist and are populated by the F1 worker.
- Krutilka gradient + text-shadow already wired; the missing piece is reading `ai_description_*` instead of `description`.
- `formatNumber` from A6 in place; needs a `formatPriceShort` extension for compact UZS.
- **Risk:** locale-fallback policy for missing `ai_description_uz_cyrl` — recommend uz Latin → ru fallback. One-line product call to confirm.
- **Coupling:** B1's pill row sits in the same overlay region. Coordinate with B1 to land in the same wave.
- **Can start:** today. Mid-level FE.

### B5 — Progressive filter disclosure — **BLOCKED ON B3**

- A2 cleanup of mockup sections is done, so the drawer's filter inventory is stable.
- Active-count logic exists at the drawer-icon level; per-section counts derive from the same calculation.
- **Hard block:** B3 should land first so the accordion sits on the unified store. Building on the current split stores would be thrown away.
- **Open:** five-section split per-filter assignment is judgement; spec proposes one — confirm with product.
- **Can start:** the day after B3 PR2 ships. Mid-level FE.

### B3 — Search surface unification — **CONDITIONALLY READY**

- A2 (mockup-section cleanup) shipped; the surface to unify is stable.
- Two filter stores identified by file:line; saved-searches matcher reads the home shape.
- **Hard requirements before code:**
  1. **Canonical route choice** (`/` recommended; `/listings` per spec). Product call.
  2. **F3 SEO grammar sign-off** before B3 PR2 lands. F3 owner needed at the table.
  3. **nginx 301 coordination** for SEO-clean redirects of `/search`, `/browse`, `/listings`. Infra owner needed.
- **Open:** saved-search migration trigger (one-shot script vs lazy-on-read). Recommend one-shot; idempotent.
- **Risk:** saved-search regression is the single biggest risk in the block. Test against production-shaped data before deploy.
- **Can start:** PR1 (store unification, no route changes) can start today; PR2 (route consolidation) waits for the three sign-offs above.
- **Effort:** 4 dev-days. Senior FE.

## What's ready now

| Spec | Day-1 status |
|---|---|
| B7 | ✅ Ready |
| B6 | ✅ Ready (operational follow-up: native-speaker review pre-launch) |
| B4 | ✅ Ready, after a 1-line canonical-path decision |
| B2 | ✅ Ready (locale-fallback policy is a 1-line decision) |
| B1 | 🟡 Ready after `year_built` decision |
| B3 PR1 | ✅ Ready (internal refactor only) |
| B3 PR2 | 🔴 Needs route choice + F3 grammar + nginx coordination |
| B5 | 🔴 Hard-blocked on B3 |

## What's blocked

| Item | Why | Unblock by |
|---|---|---|
| B5 | Sits on B3's unified store | B3 PR2 ships |
| B3 PR2 | F3 SEO grammar + nginx 301 + canonical route choice | Three sign-offs (product, infra, F3 owner) |
| B1 (full pill set including year) | `year_built` schema gap | Migration + LLM extractor update OR defer year pill |

## What requires product decisions

1. **B1**: add `year_built` column now, or defer? (Spec recommends defer.)
2. **B1**: apartments — show `wall_material` or `building_type` when both set? (Spec recommends `wall_material` first.)
3. **B2**: locale fallback for missing `ai_description_uz_cyrl` — uz Latin → ru, or ru first? (Spec recommends uz Latin → ru.)
4. **B2**: compact UZS thresholds — `>= 1e9 → "млрд"`, `>= 1e6 → "млн"`? (Spec recommends.)
5. **B3**: canonical route — `/` (recommended) vs `/listings` (spec)?
6. **B3**: `/listings` and `/browse` post-redirect — kill or repurpose?
7. **B4**: canonical path — `/seller/register` (recommended) vs `/become-seller`?
8. **B4**: post-success redirect — `/seller/dashboard` (recommended) vs `/seller/create`?
9. **B5**: confirm five-section split (spec proposes; per-filter assignment is judgement).
10. **B7**: extend prop API backward-compat (recommended) or break?

## What requires infrastructure / API keys

- **B3 PR2**: nginx 301s for `/search`, `/browse`, `/listings` → canonical. Owner: infra. Coordinate with the same deploy.
- **B3 PR2**: F3 SEO grammar sign-off. Owner: F3 owner.
- **No new external API keys** required for any Block B task. All work is FE + small BE shims; F1's OpenAI key is already covered by Block A.

## What's high-risk

| Risk | Affected task | Severity | Mitigation |
|---|---|---|---|
| Saved-search regression after store rename | B3 PR1 | **HIGH** | Idempotent migration; backup before deploy; test against production-shape data |
| nginx 301 missing on launch day | B3 PR2 | **HIGH** | Land nginx config in the same window as B3 PR2 |
| `year_built` shipped without parser support | B1 (if Step 0a) | MEDIUM | Defer to Step 0c; ship later when A7 metrics confirm coverage |
| Krutilka locale-fallback shows ru text in uz-cyrl mode | B2 | MEDIUM | Document fallback order; surface to support |
| Mass aria-label PR conflicts with concurrent work | B6 | MEDIUM | Split into 3 module-scoped PRs; merge often |
| Filter accordion FPS regression on Android 8/9 | B5 | LOW | Lazy-mount panels if measured jank |
| Visual drift across 5 EmptyState migrations | B7 | LOW | Before/after screenshots per migration step |
| Marketing links to `/listings` outlive the redirect grace period | B3 PR2 | LOW | Re-issue marketing materials before launch |

## What can be shipped independently

These are **fully self-contained** — they don't share files or stores with other Block B tasks beyond i18n keys.

- **B7** EmptyState — single component + 5 migration sites.
- **B6** Aria sweep — split into 3 module-scoped PRs.
- **B4** Seller register — touches only the two pages and one BE endpoint.

These have **light coupling** — share files but not blocking each other:

- **B1** + **B2** — share Krutilka overlay area; land in the same wave.
- **B3 PR1** — internal refactor, can ship without PR2.

## What should be deferred

- **`year_built` schema column + LLM extractor support** — defer to Block C or to a follow-up of A7 once parser-quality metrics measure year-extraction coverage. The B1 spec's Step 0c assumes deferral.
- **F3 SEO SSR rendering** — B3 ships scaffolding for the URL grammar; the actual SSR is F3 territory.
- **D3 deep-link re-issue** — operational, runs in parallel with B3 PR2 deploy.
- **WCAG AA contrast and tap-target sizing** — B6 covers WCAG-A baseline; AA is its own future iteration.
- **Filter-state persistence between sessions (B5)** — explicit "out of MVP" per spec.
- **Native-speaker review of seeded uz-cyrl strings** — runs in parallel with all engineering, doesn't gate any code merge but does gate launch.

## Cross-block risks (Block B's interactions with the rest of the system)

| Block B → | Risk | Mitigation |
|---|---|---|
| Block A's saved searches | B3 store rename could orphan filter shape | Idempotent JSON migration |
| Block F's F3 SEO | Grammar baked into B3 must match F3's SSR | Sign-off before B3 PR2 |
| Block F's F1 generation | B2 reads `ai_description_<locale>`; bad locale fallback shows wrong language | Document fallback chain |
| Block A's A4 push | B4 reuses A4's `notify_sellers_of_crawled_listing` | No new code path; audit shows safe re-use |
| Block A's A8 admin sources | B6 aria sweep includes A8's icon-only buttons | List those buttons explicitly in B6's seller/admin PR |

## Recommended go / no-go gates

Before any code merges:

- [ ] Product confirms canonical path for B3 (`/` vs `/listings`).
- [ ] Product confirms canonical path for B4 (`/seller/register` vs `/become-seller`).
- [ ] Product confirms `year_built` defer-vs-add for B1.
- [ ] F3 owner confirms SEO URL grammar.
- [ ] Infra owner confirms nginx 301 deployment window.
- [ ] One-shot saved-search migration script reviewed and tested against staging data.

When these six gates pass, Block B can land in a 2-week calendar window with 2 devs (or 1.5 weeks with 3 devs).
