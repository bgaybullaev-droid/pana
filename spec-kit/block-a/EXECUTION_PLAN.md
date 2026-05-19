# Block A — Execution Plan

This plan orders the eight Block-A specs by **real dependency**, not by complexity. It is grounded in the spec text + audit of the current code, not by header tier.

## Dependency map

| Task | Hard deps (must precede) | Soft deps (preferable to precede) | Blocks |
|---|---|---|---|
| **A2** mockup filters | — | — | — |
| **A3** mock data Found | — | — | A1 (cleaner test surface), A6 (deletes 5 hardcoded RU titles) |
| **A5** counters (7-day + anon dedup) | — | — | — |
| **A6 foundation** (`uz-latn` skeleton, ICU plurals, `formatNumber` helper) | — | — | every UI-touching downstream task adds its own keys |
| **A7 quality fixes** (signature dedup + floor, junk filter, `UNCONFIRMED` short-circuit) | — | — | A7-F1 plumbing (same file, bundle) |
| **A8 engineering foundation** (`parser_source` table + admin CRUD + per-source metric writeback) | — | — | A8 AI-quality metrics |
| **A1 pre-F1** (raw_text passthrough, disabled buttons, "Show source" block) | A3 | A6 keys for new buttons | A1 post-F1 |
| **A7 F1 plumbing** (`ListingStatus` extensions, `ai_description_*` columns, F1 Celery task, B2C feed gating, edit-time regen wiring) | F1 (Block F) for prompt logic | A7 quality fixes (same file, bundle) | A1 post-F1, A4, A8 AI metrics |
| **A1 post-F1** (AI text in B2C, skeleton on `PENDING_GENERATION`) | A7 F1 plumbing | A1 pre-F1 | A4 |
| **A4** push notifications | A7 F1 plumbing, A1 (claim service reuse) | A6 keys, A8 admin source metadata for source labelling | — |
| **A8 AI-quality metrics** (per-source `ai_failure_rate`, F5 feedback aggregation) | A7 F1 plumbing, A8 engineering foundation, F5 (Block F) | — | — |

A6 (i18n) is **a continuous discipline**, not a single step. Every UI-touching downstream task adds its keys at consumption time. The foundation work (`uz-latn`, ICU, `formatNumber`) lands in Step 1; the per-spec key additions land alongside the consuming spec.

## Final ordered steps

### Step 1 — Parallel cleanup wave (no hard deps)

Six independent units. Any can start on day one. None block each other within this step.

| Unit | Source spec | Deliverable summary | Est. effort |
|---|---|---|---|
| **A3** mock data | [easy/A3](easy/A3-mock-data-found.md) | Delete `getMockups()` (Page.tsx:267-559), flip ternary at :562, add error-state, route timeout to error after 15s | ½ d |
| **A2** mockup filters | [easy/A2](easy/A2-mockup-filters.md) | Drop `MockupBadge` JSX from `building_type`, `condition`, `amenities` (Page.tsx:952-1139); hide `house_type` / `house_condition` / `water_supply` cards; fold `utilities` into `amenities` | ½ d |
| **A5** counters | [medium/A5](medium/A5-view-contact-counters.md) | Extend `/sellers/me/dashboard` + per-card response with 7-day fields; add `anon_id` cookie path; rebuild dedup index to span `(user_id ∪ anon_id, listing_id, event_type, day)` | 2 d |
| **A6 foundation** | [medium/A6](medium/A6-i18n-leaks.md) | Create `frontend/src/shared/i18n/locales/uz-latn/` (copy from `uz/`); register locale in `i18next.init`; wire language switcher; add ICU/plural support; ship a shared `formatNumber(i18n.language)` helper; replace hardcoded `"ru-RU"` formatters at known sites | 1 d eng + native-speaker translation in parallel |
| **A7 quality fixes** | [hard/A7](hard/A7-parser-f1-trigger.md) §Steps 5-7 | Change dedup signature in `crawler_service.py:108-173` from `phone+address+price+rooms+area` to `phone+area+floor+price` with ±5% bucket; extend `SKIP_PATTERNS` in `llm_extractor.py:243-276` with "куплю / услуги / ремонт" and Uzbek equivalents; add `UNCONFIRMED` short-circuit (depends on Step 3 introducing the enum value, so for now use a boolean column or defer the short-circuit alone) | 1-2 d |
| **A8 engineering foundation** | [medium/A8](medium/A8-channels-management.md) §Steps 1-7 | Create `parser_source` table; migrate channels from `real_estate.yaml` into seeded rows; add `GET/POST/PATCH/DELETE /admin/sources`; build admin page under `frontend/src/modules/admin/pages/sources/`; flip crawler to read from DB on a 10-min refresh tick; create `source_metric` table and write to it from the crawler | 4-5 d |

**Why this step is first:** none of these tasks read from anything F1-dependent. Most are deletions, schema-additions, or pure UI wins. They strictly improve the codebase before the bigger F1 surgery starts.

**What this step unlocks:**
- A3 unlocks A1 (no fake cards interfering with claim flow testing).
- A6 foundation unlocks every downstream consumer adding keys.
- A8 engineering foundation unlocks A8 AI metrics in Step 4.
- A7 quality fixes ship inside the same files as A7 F1 plumbing — bundling avoids merge churn.

> Note on `UNCONFIRMED` short-circuit: this requires `ListingStatus.UNCONFIRMED` to exist, which is introduced in Step 3. Two options: (a) defer the short-circuit until Step 3 and do the rest of A7 quality fixes in Step 1, or (b) ship a boolean `is_unconfirmed` column in Step 1 and migrate to the enum in Step 3. **Option (a) is recommended** — keeps the schema surface tighter.

### Step 2 — A1 pre-F1

Single unit. Independent of A7 F1 plumbing for the parts of A1 that don't display AI text.

| Unit | Source spec | Deliverable summary | Est. effort |
|---|---|---|---|
| **A1 pre-F1** | [medium/A1](medium/A1-claim-reject-v2.md) §Path-to-DONE 1-3 | Copy `raw_text` on claim convert (one line each in `crawler_service.py:514, 591`); add `disabled` to Found buttons during in-flight mutation; add Mantine `Collapse` "Show source from origin" on cabinet/listing-detail when `raw_text != null`; wire i18n keys `seller.showSource` / `seller.hideSource` (A6) | 1-2 d |

**Why this step here:** small but user-visible win that ships before the F1 surgery. Validates the raw-text-as-metadata invariant in production. Also surfaces any latent issues in the claim path before A4's inline handlers depend on it.

**What this step unlocks:** validates `raw_text` plumbing end-to-end, which the post-F1 work in Step 4 assumes. Reduces blast radius of A7 F1 plumbing changes.

### Step 3 — A7 F1 plumbing (the bottleneck)

Single sequential unit. **This is the critical-path bottleneck** — three downstream specs (A1 post-F1, A4, A8 AI metrics) are all hard-blocked on it. F1 itself (the Gemini prompt and quality work) belongs to Block F, but the plumbing — status enum, columns, queue, gating, edit hook — is Block A's responsibility.

| Unit | Source spec | Deliverable summary | Est. effort |
|---|---|---|---|
| **A7 F1 plumbing** | [hard/A7](hard/A7-parser-f1-trigger.md) §Steps 1-4, 8-10 | (1) Migration adds `ListingStatus.PENDING_GENERATION / GENERATION_FAILED / UNCONFIRMED`; adds `Listing.ai_description_ru / _uz / _uz_lat`. (2) `backend/app/workers/tasks/ai_generation.py` Celery task skeleton (Block F supplies the Gemini prompt body). (3) Crawler import flips status to `PENDING_GENERATION` and enqueues. (4) Buyer feed at `listings.py:1186-1188` gates on `status IN (ACTIVE, GENERATION_FAILED)`. (5) Listing edit endpoint flips to `PENDING_GENERATION` and re-enqueues when one of `{deal_type, price, district, area_sqm, rooms}` changes. (6) `raw_text[:2000]` truncation in prompt builder. (7) `source_metric` writeback (uses Step 1 A8 table). | 4-5 d eng (Block F supplies prompt content; if Block F not ready, ship the skeleton with a stub that fills `ai_description_*` from `description` so downstream specs unblock) |

**Why this step here:** every Step-4 unit reads `Listing.ai_description_*` and `Listing.status IN (PENDING_GENERATION, GENERATION_FAILED)`. Without this step those reads have nothing to point at.

**What this step unlocks:** A1 post-F1, A4 push, A8 AI metrics.

### Step 4 — Parallel fan-out post-F1

Three independent units, all reading from the F1 plumbing in Step 3. None depend on each other.

| Unit | Source spec | Deliverable summary | Est. effort |
|---|---|---|---|
| **A1 post-F1** | [medium/A1](medium/A1-claim-reject-v2.md) §Path-to-DONE 4 | B2C controllers select `Listing.ai_description_<viewer_locale>`; cabinet renders skeleton when `status == PENDING_GENERATION`; "already claimed by other seller" 409 toast wired | 2-3 d |
| **A4** push notifications | [hard/A4](hard/A4-push-notifications.md) §Steps 1-8 | Migration adds `NotificationType.CRAWLED_MATCH` + unique partial idx + optional `Notification.expires_at`; `notify_sellers_of_crawled_listing` Celery task triggered after F1 completes; bot inline keyboard with `claim_crawled:<id>` / `reject_crawled:<id>`; callback handlers reuse Step 2 claim service; daily expiry beat job edits 7-day-old messages and strips keyboards; 5-minute Redis-debounced batcher; bot-blocked branch logs only (listing already in Found via pull) | 5-7 d |
| **A8 AI metrics** | [medium/A8](medium/A8-channels-management.md) §Step 9 | Extend `source_metric` row write with `ai_failed` counter; admin dashboard shows AI failure % per source; (after F5) populate `ai_feedback_dislikes` from F5 events | 1-2 d eng + 1 d after F5 lands |

**Why this step here:** all three rely on `ai_description_*` and the new statuses. Splitting them into Step 4 lets two or three devs run them concurrently.

**What this step unlocks:** Block A is functionally complete after this step. Remaining work is operational.

### Step 5 — Operational (not engineering)

Two units, founder-driven, run in parallel with Step 4 or after.

| Unit | Source spec | Deliverable summary | Owner |
|---|---|---|---|
| **A6 translation pass** | [medium/A6](medium/A6-i18n-leaks.md) §Path-to-DONE 1, 6 | Native-speaker review of `uz-latn/` JSON values; UZ-overflow visual pass on cabinet, found, listing-detail | Operations + designer |
| **A8 channel expansion** | [medium/A8](medium/A8-channels-management.md) §Operational | Found grows source list to 25+ via tgstat.ru and recursive mention analysis (Block E1) | Founder |

## Dependency explanation (why the order is what it is)

### Why **A1** depends on **A7** for the V2.0 part of A1

The V2.0 framing of A1 puts an AI-generated description on the user-visible side and reduces the realtor's raw text to metadata. Two things must exist before "AI text in B2C" is more than wishful thinking:

1. **Schema** — `Listing.ai_description_{ru,uz,uz_lat}` columns. Introduced in Step 3.
2. **Status semantics** — `PENDING_GENERATION` to render a skeleton, `GENERATION_FAILED` to fall back to a template. Introduced in Step 3.

A1 pre-F1 (Step 2) deliberately avoids these — it ships only the parts that are safe to land before the schema exists (`raw_text` copy, disabled buttons, Show-source UI). The post-F1 deltas wait.

### Why **A4** must come after **F1** (Step 3)

A4's push card carries the listing description into Telegram. Per V2.0 spec ("чистое профессиональное первое впечатление, без шумных формулировок типа 'СРОЧНО ХОЗЯИН'"), this **must** be the AI-generated text, not the realtor's raw post. Without `Listing.ai_description_*` columns populated, the trigger has nothing to put in the message body. Even the "AI failed → template" fallback path needs `status == GENERATION_FAILED` to detect the condition.

A4's trigger also fires *only after* F1 completes (per spec: "не отправлять push с пустым описанием"). If `status == PENDING_GENERATION`, the trigger waits; the natural enqueue point is the F1 task's success callback, which is itself part of Step 3.

### Why **A4** also depends on **A1** (claim service)

The bot inline buttons "Это моё" / "Не моё" must perform the same operation as the web Found buttons. Reusing the existing `convert_*_to_listing()` services keeps the data path consistent (one master-record creation code path, one rejection-tracking write). A1 ships the service surface in Step 2; A4 in Step 4 just reuses it from a different transport.

### Why **A3** is preferable before **A1**

`getMockups()` returns 20 fake cards with phone-less Unsplash listings. Tapping "Это моё" on one of them currently passes through the real claim endpoint and fails (no matching record). With A3 done first, the claim flow can be tested against real backend data without false positives.

### Why **A6** is *not* a single step

i18n is a write-time discipline. Bolting it on later doubles the cost. The repo's existing `uz/` and `ru/` dictionaries are healthy precisely because keys were added at the moment a screen was written. The Block-A i18n work splits into:

- **Foundation** in Step 1 (locale set, ICU, `formatNumber` helper) — engineering-only.
- **Per-spec keys** in every subsequent step (A1 needs `seller.showSource`, A4 needs the bot template family, A5 needs `seller.dashboard.last7Days`, etc.) — added by the consuming spec at the moment of consumption.
- **Translation pass** in Step 5 — operational, not engineering.

Trying to ship A6 as one step before A1-A8 would mean adding keys with no consumers, which rots fast.

### Why **A2**, **A5**, **A8 engineering** can land in Step 1 alongside A3

None of these reads from F1 columns or AI status. A5's anonymous-viewer dedup, A2's filter cleanup, A8's admin CRUD — each is a self-contained engineering deliverable. Putting them in Step 1 frees senior bandwidth in Step 3 for A7's surgical work.

### Why **A7 quality fixes** ship in Step 1 even though they're inside A7

A7 has two halves. The signature-dedup fix, junk-filter additions, and (with caveat) the `UNCONFIRMED` short-circuit don't depend on F1 or any new schema. They ship in Step 1; the F1 plumbing (status enum, columns, queue, B2C gating) ships in Step 3. Bundling both halves into Step 3 would create a 7-day PR — splitting them into Step 1 and Step 3 keeps each PR reviewable.

### Why **A8 AI metrics** is in Step 4, not Step 1

`ai_failure_rate` per source is the only A8 deliverable that depends on F1 actually running. Per-source `listings_extracted`, `listings_failed`, `dupes_filtered` ship in Step 1's A8 engineering foundation; the AI-failure column is added in Step 4 after Step 3 starts producing F1 outcomes.

## Parallel work plan

Estimates are wall-clock dev-days, assuming a senior who can switch between BE and FE. Actual calendar time depends on review cadence and Block-F readiness.

### 1 dev (sequential)

A serial dev runs the steps in order. Step 1 itself is a queue of six independent units; do them in any order during ~4-5 days, then proceed.

```
Days 1-5    Step 1 (six units, any order)
Days 6-7    Step 2 (A1 pre-F1)
Days 8-12   Step 3 (A7 F1 plumbing)
Days 13-15  Step 4a (A1 post-F1)
Days 16-22  Step 4b (A4 push)
Day 23      Step 4c (A8 AI metrics)
            Step 5 runs in parallel as operational work, not on dev clock
```

Total: ~22 dev-days (≈ 4.5 weeks calendar at 5 d/wk).

### 2 devs (FE/BE split)

Sync points: end of Step 1, end of Step 3.

```
Dev A (FE-leaning, 14 days)
  Days 1-3    A3 (½ d) → A2 (½ d) → A6 foundation (1 d) → A1-pre FE part (1 d)
  Days 4-6    [waits or helps Dev B with A8 admin FE page]
  Days 7-9    A1-post FE (skeleton, controllers)  ← starts when Dev B finishes Step 3
  Days 10-14  A4 FE (bot card rendering, copy, i18n keys for inline keyboard)

Dev B (BE-leaning, 14 days)
  Days 1-3    A5 (2 d) → A7 quality fixes (1-2 d)
  Days 4-7    A8 engineering foundation (CRUD + table + metric writeback) — 4 d
  Days 8-12   A7 F1 plumbing — 5 d  ← Step 3 critical path
  Days 13-14  A4 BE (trigger, callback handlers, expiry beat job, batch debouncer)

Both contribute their consumer-side i18n keys at consumption time (no separate sweep).
```

Total: ~14 dev-days each (≈ 3 weeks calendar). Critical path = Dev B's chain.

### 3 devs

Sync points: end of Step 1, end of Step 3.

```
Dev A (FE — buyer/seller pages, 10-12 days)
  Days 1-2    A3 → A2
  Days 3-4    A1-pre FE (Show-source block, disabled buttons)
  Days 5-6    A6 foundation polish (formatNumber helper, plural setup)
  Days 7-9    A1-post FE (skeleton on PENDING_GENERATION, AI text rendering)
  Days 10-12  A4 FE (bot copy, found-page error-state alignment)

Dev B (BE-listings/parser, 12 days)
  Days 1-2    A7 quality fixes (signature, junk, unconfirmed)
  Days 3-4    A5 (BE part: 7-day aggregate query, anon_id schema migration)
  Days 5-9    A7 F1 plumbing  ← Step 3 critical path
  Days 10-12  A4 BE (trigger task, callback handlers, expiry beat, batch)

Dev C (BE-infra/admin/i18n eng, 9 days)
  Days 1-3    A8 engineering: parser_source table + admin endpoints
  Days 4-5    A8 engineering: admin frontend page (sources/) + metric writeback
  Days 6-7    A6 foundation engineering: uz-latn registration, ICU plural lib, replace toLocaleString sites
  Days 8-9    A8 AI-metrics column + admin dashboard tile  ← starts when Dev B finishes Step 3
```

Total: ~10-12 dev-days (≈ 2-2.5 weeks calendar). Critical path = Dev B.

Step 5 (translation review, channel expansion) runs operationally in parallel and does not consume engineering days.

## Critical path

The longest dependency chain through the plan:

```
A7 quality fixes  →  A7 F1 plumbing  →  A1 post-F1  →  A4 push
   (Step 1, 1-2d)      (Step 3, 4-5d)    (Step 4, 2-3d)   (Step 4, 5-7d)
```

Calendar: **~13-17 dev-days for one developer running this chain alone.** Even with 3 devs, A4 push depends on A7 F1 plumbing, so Dev B's chain (A7 quality → A7 F1 → A4 BE) defines the floor at roughly 12 days regardless of how much parallelism Dev A and Dev C add elsewhere.

**The single most expensive node is A7 F1 plumbing**: it has both the most downstream consumers (A1 post-F1, A4, A8 AI metrics) and a dependency on Block F supplying the Gemini prompt. If Block F is not ready when Step 3 starts, ship a stub that copies `description` into `ai_description_*` so downstream work unblocks; replace with the real prompt when F1 lands.

**Risks that can extend the critical path:**

1. **F1 (Block F) prompt unfinished** when Step 3 starts. Mitigation: ship the F1-plumbing skeleton with the `description`-copying stub; replace the stub when Block F supplies the prompt body. Costs ~1 d more, doesn't extend the chain.
2. **A4 spec ambiguity** on group-batch threshold (when to switch from inline-buttons to "open Found" button). Resolve up front via product Q (open question in [hard/A4](hard/A4-push-notifications.md)).
3. **`uz-latn` translation review** stalls if no native speaker is available. A6 translation is operational (Step 5) and not on the engineering critical path; a missing reviewer at launch blocks **launch**, not Block A engineering.
4. **A2 path choice** (Path 1 backend filtering vs Hybrid) needs product sign-off; default Hybrid in Step 1 if no answer by day 1.

Open questions that should be resolved before Step 1 starts: see the consolidated list in [README.md](README.md#open-questions-raised-across-specs).
