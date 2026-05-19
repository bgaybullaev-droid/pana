# Block C — Execution Plan

This plan orders the five Block-C specs by **real dependency**, anchored to the live-code audit (May 2026, post-Block-A V2.0). Block A is fully shipped; Block B is spec-only.

Block C is **architecture-heavy**: three of the five tasks are HARD because the schema and contracts they introduce are forward-compatible commitments — wrong on day 1 means painful migrations later. The plan deliberately front-loads schema/decisions and treats UI as the easier follow-up.

## Dependency map (collapsed)

| Task | Hard upstream | Hard downstream | Calendar order |
|---|---|---|---|
| **C1** | A6 (done) | C2 (reads test-period flag) | Wave 1 |
| **C2** | A7 (done), C1 flag | C3 paid-phase consumer | Wave 1 |
| **C3** | AuditLog, Currency enum (done) | C1 modal CTAs in Phase 2 | Wave 2 |
| **C4** | A1, A4 (done), `prf_canonicalize_phone` migration (done) | C5 (must respect aggregation) | Wave 3 |
| **C5** | **C4 schema** | — | Wave 4 |

A6 and AuditLog are inherited from Block A; both are foundational and don't gate anything in this block.

The single critical-path link is **C4 → C5**. Everything else parallelises.

## Execution waves

### Wave 1 — UI + counter (parallelisable)

These two ship in the same release. C1 lays the public-facing tariff page and the config knobs; C2 fixes the counter and gates the future enforcement.

| Task | Owner | Est. dev-days | Notes |
|---|---|---|---|
| **C1 — Tariff display** | FE + light BE | 2.5 | New `/seller/tariffs` route, `GET /tariffs/status` endpoint, ~25 i18n keys × 3 locales. Disabled-CTA modal. Banner on My Listings. |
| **C2 — Free-limit logic** | BE-leaning | 2 | `listing_quota.py` helper, `Depends(check_can_create_listing)` (no-op during test period), dashboard extension, FE header chip + info-toast. |

**Why this wave is first:** purely additive. C1's `test_period_active` config knob is the gate that C2's middleware reads. Neither writes to a new table; the counter cleanup is a query change, not a schema change.

**Dependency between C1 and C2:** soft. C2 can ship without C1's UI; C1 reads counter values that work with or without C2's cleanup. **Recommend pairing them in one release** because the user-facing copy refers to "first 2 free / extra paid" in both.

### Wave 2 — Wallet foundation (single track, no UI)

| Task | Owner | Est. dev-days | Notes |
|---|---|---|---|
| **C3 — Wallet architecture** | Senior BE | 3.5 | Three new tables, idempotent `withdraw`/`deposit` services, Click/Payme adapter Protocols + stubs, admin `POST /admin/wallets/{user_id}/adjust`, Numeric(18,2) money invariant. **No production code calls withdraw/deposit during test period.** |

**Why this wave is second, not first:** C3 has no immediate user-visible effect. Shipping it after C1+C2 means the disabled CTAs in C1 already exist when C3 lands; the wiring (which is Phase-2 work, not C3's responsibility) plugs into a known target.

**Critical:** C3 is pure foundation. The schema is the commitment. **Land schema-only PR1 first, then services.**

### Wave 3 — Multi-phone (the biggest single task)

| Task | Owner | Est. dev-days | Notes |
|---|---|---|---|
| **C4 — Multi-phone connection** | Senior FE+BE | 7 | `user_phones` table + backfill, OTP verify endpoints, list/delete endpoints, parser/A4 query expansion, frontend "My Phones" page + listing-create phone-picker, post-claim hint banner. |

**Why this wave is third:** C4 is the highest-impact feature in the block (claim-coverage multiplier, A4 push expansion, anti-bypass). It touches the most files. Front-loading it ahead of C3 risked lose-lose: C4 is bigger, C3 is foundation; doing C3 first means C4 can rely on the wallet schema if any unforeseen coupling emerges.

**Forward-compat hook for C5:** C4's schema PR includes the `phone_verify_attempt` log table even though only C5 reads it. Folding it here avoids a tiny migration later.

### Wave 4 — Detection (depends on Wave 3)

| Task | Owner | Est. dev-days | Notes |
|---|---|---|---|
| **C5 — Multi-account detection** | BE-heavy + admin FE | 6 | `account_suspicion` + `account_link` tables, five signal Celery tasks, admin queue endpoints + UI. **C4 must ship before C5 PR2 (signal tasks) or false-positives flood the queue.** |

**Why last:** C5's phone-collision signal is incorrect without C4's `user_phones` table to test "same user, different phones?". Shipping in reverse order means false positives would burn admin trust before the queue has any real value.

## Parallelisation scenarios

### 1 dev (sequential, ~21 dev-days)

```
Days 1-2.5   C1 (tariff display)
Days 3-4     C2 (counter + middleware)
Days 5-8     C3 (wallet foundation)
Days 9-15    C4 (multi-phone)
Days 16-21   C5 (detection)
```

≈ 4-5 weeks calendar at 5 d/wk. Senior dev required for C3 + C4.

### 2 devs (BE + FE-heavy)

```
Dev A (BE-leaning, ~11 d)               Dev B (FE+BE, ~11 d)
Day 1-2     C2 (counter)                Day 1-2.5   C1 (tariff page)
Days 3-6    C3 (wallet)                 Days 3-7    C4 (frontend + BE-light)
Days 7-10   C5 (detection)              Days 8-9    C5 admin UI
                                        Days 10-11  buffer / acceptance
```

Sync points: end of Wave 1 (Day 2.5), end of Wave 3 (Day 7).

≈ 2.5 weeks calendar. C5 work picks up C4's schema as soon as it lands.

### 3 devs (most parallel, ~9 dev-days each)

```
Dev A (FE-leaning)         Dev B (BE/services)        Dev C (BE/migration+admin)
Day 1-2     C1 page         Day 1-2     C2 helper     Days 1-3.5  C3 schema+services
Day 3-4     C4 forms        Days 3-7    C4 BE         Days 4-5    C3 admin endpoint
Day 5-6     C5 admin UI     Days 8-9    C5 signals    Days 6-9    C5 schema + signal tasks
Day 7-9     polish + i18n
```

Sync point: end of Day 7 (C4 BE done, C5 unblocked).

≈ 2 weeks calendar. Recommended scenario for the timeline.

## Critical path

```
A6/A7 (done) ── C1 ── C2 (no-op enforcement) ── (Phase 2 monetization activation)
                              ▲
                              │ reads
                              │
                              C3 (wallet)
                              │
A1/A4 (done) ── C4 ── C5
```

**Block-C-internal critical path: C4 → C5.** ~13 dev-days.

**Whole-block critical path** depends on which is the last to land:
- If C5 last: 21 sequential, but ~13 days when parallelised.
- If C3 last: 11 days minimum because C4 doesn't depend on C3.

Recommendation: parallelise so C4 and C3 land in roughly the same window; C5 follows C4 immediately.

## FE / BE / DB / infra split

| Task | Frontend | Backend | DB migration | Infra |
|---|---|---|---|---|
| **C1** | yes (page, banner, modal) | yes (config + endpoint) | — | Redis cache (already available) |
| **C2** | yes (header chip + info-toast) | yes (helper + middleware) | one (optional, if Option A chosen) | — |
| **C3** | — | yes (heavy) | one (3 tables + 5 enums) | env var slots in `.env.example` (no live keys yet) |
| **C4** | yes (heavy) | yes (heavy) | two (`user_phones`, `phone_verify_attempt`) | OTP delivery channel decision (TG vs SMS) |
| **C5** | yes (admin queue) | yes (heavy) | two (`account_suspicion`, `account_link`, optional User columns) | Celery beat schedule additions, `fuzzystrmatch` Postgres extension |

## Migration ordering

```
pri_source_metric_notified (last in Block A) → pre-existing
prj_wallet_billing                              ← C3 PR1
prk_user_phone                                  ← C4 PR1
prk2_phone_verify_attempt (folded into prk)     ← C4 PR1 (forward-compat for C5)
prl_account_suspicion                           ← C5 PR1
```

Each migration is **purely additive**. No downstream code touches existing tables in incompatible ways. Down-migrations are safe because all new tables ship empty.

## Rollout ordering & infra coordination

1. **Wave 1 (C1 + C2):** standard release. No infra coordination.
2. **Wave 2 (C3):** standard release; add empty env-var slots (`CLICK_*`, `PAYME_*`) to deployment manifests.
3. **Wave 3 (C4):**
   - **Decision gate:** OTP-delivery channel — Telegram-bot (default) or SMS via Eskiz.
   - If SMS: requires Eskiz API key, paid quota, integration. **+2 dev-days, +ops cost.**
   - Otherwise: zero new infra; reuses bot.
4. **Wave 4 (C5):**
   - Postgres `fuzzystrmatch` extension. Verify presence; install in coordination with infra.
   - Celery beat schedule update.

## Operational checkpoints

After each wave:

- **Wave 1:** load `/seller/tariffs` in three locales; `GET /tariffs/status` returns expected JSON; the banner copy is intelligible to a native-Uzbek speaker.
- **Wave 2:** unit tests for `wallet.withdraw` pass with property-based concurrency tests; admin balance-adjust returns 200 + writes AuditLog.
- **Wave 3:**
  - Verify a phone via the chosen OTP channel; matched-listing count is non-zero on a synthetic test seller.
  - Confirm `crawled_match.notify_sellers_of_crawled_listing` lights up for the new phone within an A4 fanout cycle.
- **Wave 4:** signal tasks run dry; no `account_suspicion` rows appear that involve same-user phone aggregation.

## Rollback plans

| Task | Rollback |
|---|---|
| **C1** | Disable `test_period_active` route, hide nav-item. Code is presentation-only. |
| **C2** | Revert `Depends(check_can_create_listing)` from POST routes. Helper stays as dead code. |
| **C3** | `alembic downgrade -1` drops the three tables (empty in production). Settings env vars stay. |
| **C4** | Disable `multi_phone_enabled` feature flag → forms hide phone-picker; backend still reads from `user_phones`. Schema stays. To fully revert: drop `user_phones` (requires backup since backfill happened). |
| **C5** | Pause Celery beat for the five signal tasks. Tables stay. |

Rollback for **C4 schema** is the riskiest; the table has a backfill that mirrors `User.phone`. Recommend keeping the table even on functional rollback.

## Estimated dev-days (single-dev sequential)

| Wave | Tasks | Days |
|---|---|---|
| 1 | C1 + C2 | 4.5 |
| 2 | C3 | 3.5 |
| 3 | C4 | 7 |
| 4 | C5 | 6 |
| **Total** | | **~21** |

Parallel-3-dev: ~9-10 days each. Calendar: ~2 weeks.

## Recommended staffing

- **Senior BE** (must) — C3 wallet services, C4 backend, C5 signal tasks, idempotency guarantees.
- **Senior FE** — C1 page, C4 forms (multi-step), C5 admin queue.
- **Mid BE** — C2 helper, C5 admin endpoints.

## Launch-risk analysis

| Risk | Affected task | Severity | Mitigation |
|---|---|---|---|
| **Money bug in `wallet.withdraw`** (off-by-one, race, idempotency lapse) | C3 | **CRITICAL** | Property-based tests, mandatory peer review, no production callers in test period. |
| **Counter wrong on `test_period_active=false` flip** | C2 | HIGH | Live-query option (Option B) eliminates this; backfill required if Option A chosen. |
| **Phone-collision false positives** | C5 (without C4) | HIGH | Strict ordering: C4 schema lands first. |
| **Engineering jargon leaks into UI** ("Phase 2") | C1 | MEDIUM | Native-speaker copy review pre-launch. |
| **OTP-channel decision delayed** | C4 | MEDIUM | Default to Telegram-bot OTP; document operational risk. |
| **Click/Payme env vars committed with values** (security) | C3 | MEDIUM | `.env.example` only; production config via secret manager. |
| **C4 backfill collides with active OTP flows** | C4 | LOW | Migrate during low-traffic window; backfill is a single INSERT-from-SELECT. |
| **C5 admin queue floods at first run** | C5 | LOW | Disable beat tasks until soft launch; manual run for QA. |

## Do not repeat the Block-A mistake

Block A started shipping code before the dependency map was complete; that left the `year_built` gap (B1) and `test_period_active` flag (C1/C2) coupling unresolved. For Block C:

1. **Land C4 schema before C5 signal-task PRs.** False positives kill admin trust faster than slow detection.
2. **Land C3 schema before any code refers to subscriptions.** Once C1/C2 reference subscription concepts in copy, the schema must back them.
3. **Don't ship C3's `withdraw` or `deposit` without idempotency tests committed in the same PR.**
4. **Confirm OTP-delivery channel before C4 PR2.** Refactoring from Telegram to SMS is small, but the i18n copy and admin-support flow assume one or the other.
5. **Confirm "first 2 free" semantics on test-period-flip day before that day arrives.** Spec says "first 2 by created_at"; that's the de-facto rule. Hardcode it in the spec, not just in product copy.
6. **C5's signal tasks are noisy; production-test them with the beat disabled** until manual triage shows acceptable false-positive rates.

## Mid-block sanity checkpoints

After each wave, verify:

- **After Wave 1:** `/seller/tariffs` renders all three locales without console errors; `GET /tariffs/status` cached at 1h responds < 100ms; the disabled-pay-button modal text contains "тестовый период" / "test period" / "тестовий период" verbatim.
- **After Wave 2:** `pytest backend/tests/unit/test_wallet.py` passes including idempotency and concurrency cases; `POST /admin/wallets/{user_id}/adjust` requires admin auth + reason.
- **After Wave 3:** verify phone via OTP, see matched-listings count in response, confirm `crawled_match` query expansion is in production via log inspection (`grep "phone IN ("` in worker logs).
- **After Wave 4:** run all five signal tasks against a fixture DB; check `account_suspicion` rows are correct; no row exists where both user_a and user_b share a `user_phones` membership.

## Deferred to Phase 2 / out of Block C

- **Click and Payme integration** (real money in/out). C3 ships the adapter Protocol; Phase 2 ships the implementations.
- **Wallet topup UI for sellers.** Spec calls for the page; C3 is server-side only.
- **Subscription renewal billing job.** Phase 2 / D-block.
- **Auto-archive on grace-period exhaustion.** Phase 2.
- **A/B price segmentation.** C1's endpoint is shape-ready, but no code branches yet.
- **Финальная цена сделки** (final transaction price, V2.0 deferral). Phase 2.
- **C5 soft user-side prompt to merge accounts.** Optional in C5, recommend defer until queue volume warrants.
