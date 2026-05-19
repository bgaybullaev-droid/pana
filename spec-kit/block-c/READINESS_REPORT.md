# Block C — Implementation Readiness Report

Snapshot taken after Block A V2.0 fully shipped (May 2026, head = `pri_source_metric_notified`). Block B is spec-only.

This report tells you, per task, whether implementation can start **today**, what gates it, what infra/product/schema decisions are still open, and which risks are non-recoverable (money) vs recoverable (UI / detection).

## Per-task readiness

### C1 — Tariff structure display — **READY**

- All upstream deps shipped (A6 i18n, A7 status enum, `formatNumber` helper).
- New work: ~25 i18n keys × 3 locales, new route, new endpoint, config-knob extensions, banner + info-toast hooks.
- **Risk:** copy quality. "Тестовый период" / "test period" terminology is the contract; engineering jargon ("Phase 2") leaking into UI is the observable failure mode.
- **External dep:** native-speaker review of `uz` and `uz-cyrl` strings before the page goes public.
- **Can start:** today. Mid-level FE + half-day BE.

### C2 — Free-listing limit logic — **READY (decisions needed)**

- Counter exists (`Seller.listings_count`) but is broken for billing purposes (counts non-deleted, not active).
- **Open product call:** Option A (fix the counter, write hooks at every status-transition site) vs Option B (live-query, drop the field). Recommendation: B.
- **Open product call:** what happens to existing sellers with > 2 active listings on `test_period_active=false` flip day? Recommend grandfather; confirm.
- **Risk:** the quota middleware lives in production from day 1 but always returns true. The false branch must be unit-tested even though it never runs. If untested, Phase-2 activation is a blind launch.
- **Can start:** today, pending Option A vs B decision (Option B is recommended and is also cheaper). Mid-level BE + light FE.

### C3 — Wallet architecture — **CONDITIONALLY READY (needs schema sign-off)**

- AuditLog (Block A), Currency enum, settings file, services dir all in place.
- Three new tables, ~5 new enums, idempotent withdraw/deposit, adapter Protocols + stubs, admin balance-adjust endpoint.
- **Open product calls:**
  1. Lazy vs eager Wallet creation? Recommend **lazy** (created on first deposit/adjust); zero rows during test period.
  2. `Subscription.object_id` typing — polymorphic-ish (no FK constraint) vs proper FK to listings?
  3. Multi-currency wallets — defer; one wallet per user, fixed currency.
  4. Click vs Payme priority for Phase 2 (doesn't affect C3 stubs, but does affect Phase-2 sequencing).
- **Risk: CRITICAL.** Money bugs are non-recoverable. Strong unit + property-based tests for `withdraw` are mandatory.
- **External dep:** none today. Phase 2: Click + Payme merchant accounts, signing keys, webhook URLs.
- **Can start:** today after schema review. Senior BE.

### C4 — Multi-phone connection — **CONDITIONALLY READY (OTP-channel decision blocks Wave 3 PR2)**

- A1 + A4 (claim flow + crawled-match push) shipped — C4 expands their phone-match logic.
- `prf_canonicalize_phone` migration (Block A) collapsed phones to one-per-account; C4 layers `user_phones` on top.
- **Major open question: SMS (Eskiz.uz) vs Telegram-bot OTP?** Eskiz mentioned in `CLAUDE.md` but never integrated; the bot already delivers OTP for login (`auth.py:767-906`). Default: **Telegram-bot OTP** (zero infra cost). SMS is a Phase-2 upgrade if support volume demands.
- **Open product call:** rename `Listing.phone` to `Listing.contact_phone` for clarity? Or keep + document?
- **Open product call:** drop `Seller.phone` after migration to user_phones?
- **Risk:** schema migration includes a backfill (insert one `user_phones` row per existing user with their canonical `User.phone`). Trivial at MVP scale; document for ops.
- **Risk:** A4 fanout query expansion is the highest-blast-radius change. Add sample-listing test to confirm no regression in matched-seller count.
- **Can start:** PR1 schema (today). PR2 verify endpoints — needs OTP-channel decision.
- **Effort:** 7 dev-days. Senior FE+BE.

### C5 — Multi-account detection — **HARD-BLOCKED ON C4**

- AuditLog, signature_hash, A8 admin pattern all in place.
- **Hard block:** without `user_phones` (C4) the phone-collision signal mis-fires whenever a single user has multiple phones.
- **Open product calls:**
  1. Levenshtein threshold for similar names (recommendation: edit-distance ≤ 2 + matching last-4-char suffix).
  2. Soft user-side "merge accounts?" prompt — ship in MVP or wait for queue-volume signal? Recommend: **wait**.
  3. Where does device-fingerprint data come from — column on User or query AuditLog at signal-time? Recommend column on User.
- **External dep:** Postgres `fuzzystrmatch` extension for fuzzy name matching. Verify enabled; install if not.
- **Risk:** false-positive rate. Mitigate by gating signal tasks behind Celery-beat-disabled flag for the first week, manually triaging.
- **Can start:** PR1 schema (after C4 PR1 lands). PR2 signals (after C4 PR3 lands).

## Readiness summary table

| Spec | Day-1 status |
|---|---|
| C1 | ✅ Ready |
| C2 | ✅ Ready, pending Option A/B + grandfather decisions |
| C3 | 🟡 Ready after schema sign-off |
| C4 PR1 (schema) | ✅ Ready (today) |
| C4 PR2 (verify endpoints) | 🟡 Needs OTP-channel decision |
| C4 PR3 (parser/A4 expansion) | ✅ Ready after PR1 lands |
| C4 PR4 (FE) | 🟡 Needs OTP-channel decision (for copy) |
| C5 PR1 (schema) | 🟡 Needs C4 PR1 |
| C5 PR2 (signals) | 🔴 Needs C4 PR1 + PR3 |
| C5 PR3+ (admin UI) | ✅ Ready in parallel after C5 PR1 |

## What's blocked

| Item | Why | Unblock by |
|---|---|---|
| **C5 phone-collision signal** | Requires `user_phones` table | C4 PR1 ships |
| **C5 admin UI launch** | Needs detection running first | C5 PR2 ships |
| **C4 OTP delivery** | Channel choice unresolved | One-line product/infra decision |
| **C3 Phase-2 activation** | Needs Click/Payme integration (out of C3) | Phase-2 work |
| **C1 disabled-pay-button info modal copy** | Needs canonical "test period" wording in three locales | Native-speaker review |

## What requires product decisions

1. **C1:** A/B price segmentation architecture today vs later? (Recommend: schema-ready endpoint, no current branching.)
2. **C2:** Option A (denormalised counter, fix it) vs Option B (live-query)? Recommend B.
3. **C2:** Grandfathering rule when test-period flag flips and a seller has > 2 active listings? Recommend grandfather all current; new ones paid.
4. **C3:** Lazy vs eager Wallet creation? Recommend lazy.
5. **C3:** Click vs Payme priority for Phase-2 integration?
6. **C4:** Telegram-bot vs SMS (Eskiz) for additional-phone OTP? Recommend Telegram-bot for MVP.
7. **C4:** Rename `Listing.phone` → `Listing.contact_phone`? Recommend yes.
8. **C4:** Drop `Seller.phone` post-migration? Recommend yes (derive from `user_phones`).
9. **C4:** Per-phone listing limit? Spec says no (limit per-account). Confirm.
10. **C5:** Levenshtein threshold for similar-names signal?
11. **C5:** Ship soft "merge accounts" prompt in MVP or wait?

## What requires infrastructure decisions

1. **C3:** Empty Click/Payme env-var slots in `.env.example`. **No live integration.** Phase-2 work.
2. **C4:** OTP delivery infra. If SMS via Eskiz, requires API key, paid quota, integration. **+2 dev-days, recurring ops cost.** If Telegram-bot, zero infra change.
3. **C5:** `fuzzystrmatch` Postgres extension installed in production. Verify with infra owner.
4. **C5:** Celery beat schedule additions for five signal tasks (daily, off-peak Tashkent time). Coordinate with existing beat windows.
5. **C1:** Redis cache for `GET /tariffs/status` with 1h TTL. Redis already deployed; no new infra.

## What requires schema decisions

1. **C2 Option A:** one column added (`Seller.active_listings_count`) + backfill. **Skip if Option B is chosen.**
2. **C3:** three tables (`wallets`, `transactions`, `subscriptions`) + 5 enums. Pure addition; safe.
3. **C4:** `user_phones` table + `phone_verify_attempt` log table (forward-compat for C5).
4. **C5:** `account_suspicion` + `account_link` tables. Optional `User.last_register_ip` + `User.last_register_user_agent_hash` columns.

All schema work is **additive**; rollback drops the new tables only.

## What requires AI / F-block decisions

- **None.** Block C does not touch F1 (AI generation) or F3 (SEO). Wallet/Tariff/Phone work is independent of the AI pipeline.

## What requires localization review

- **C1:** ~25 keys × 3 locales (`tariffs.*` namespace). Native-speaker review of `uz` and `uz-cyrl`.
- **C2:** ~6 keys × 3 locales (banner copy + info-toast).
- **C4:** ~30 keys × 3 locales (phones page, OTP messages, modal copy).
- **C5:** ~15 keys × 3 locales (admin queue UI).

Total ~75 keys × 3 = 225 strings. Native-speaker review is operational work, not engineering.

## What is high-risk

| Risk | Affected | Severity | Mitigation |
|---|---|---|---|
| **Money bug in `wallet.withdraw` / `deposit`** | C3 | CRITICAL | Property-based concurrency tests; mandatory peer review; no production callers during test period. |
| **Counter is wrong on test-period-flip day** | C2 | HIGH | Live-query (Option B) eliminates the risk entirely. |
| **C5 phone-collision false positives** | C5 | HIGH | Strict ordering: C4 lands first; no signals until C4 PR3 ships. |
| **OTP-channel chosen incorrectly** | C4 | MEDIUM | Default Telegram-bot for MVP; document support escalation path. |
| **Click/Payme keys leaked** | C3 | MEDIUM | `.env.example` only; production via secret manager. |
| **Engineering jargon leak in UI** | C1 | MEDIUM | Native-speaker review; lint-rule for "Phase\\s+\\d" in TSX. |
| **C4 schema rollback after backfill** | C4 | LOW | Don't roll back; revert via feature flag instead. |
| **`fuzzystrmatch` not installed** | C5 | LOW | Pre-flight check in deploy script. |

## What can be shipped independently

These are **fully self-contained** — they don't share files or stores beyond i18n keys.

- **C1** Tariff display — page-only.
- **C2** Counter helper + middleware — backend-only with one frontend hook.
- **C3 PR1 schema-only** — pure migration, no behaviour change.
- **C5 admin UI shell** (after C5 PR1) — empty queue rendering.

These have **light coupling** but ship in parallel:

- **C1 + C2** — share `tariffs.*` i18n namespace.
- **C3 services + admin endpoint** — both ship without touching user-facing flows.

These are **strict-order**:

- **C4 PR1 → C5 PR1** — schema ordering.
- **C4 PR3 → C5 PR2** — `crawled_match` query expansion must land before suspicion signal tasks.
- **C3 PR1 schema → C3 PR2 services** — avoid imports referencing tables that don't exist.

## What should be deferred

- **Click + Payme real integration** — Phase 2.
- **Wallet topup UI for sellers** — Phase 2.
- **Subscription renewal Celery beat task** — Phase 2.
- **Auto-archive listings on grace-period exhaustion** — Phase 2.
- **A/B price segmentation logic** — Phase 2 / 3.
- **C5 soft user-side prompt to merge accounts** — wait for queue-volume signal.
- **Финальная цена сделки** — explicit V2.0 spec deferral to Phase 2.
- **WCAG AA on tariff page** — B6 covers WCAG-A; AA is a separate iteration.

## Biggest unknowns

1. **OTP delivery channel for C4.** Single product/infra decision blocks ~3 dev-days of frontend copy and backend service work.
2. **Click vs Payme priority** for Phase 2. Doesn't block Block C, but blocks subsequent monetization work.
3. **Volume of legitimate multi-phone use cases** in the realtor population. Determines whether C4 is high-leverage (>40% of realtors) or marginal (<10%). Pre-launch survey would help.
4. **False-positive rate of C5 signals** at MVP scale. Unknown until live. Plan a 1-week soft-launch.

## Top project risks

1. **C3 money correctness.** Audit-log gap, idempotency lapse, race condition in withdraw/deposit are non-recoverable.
2. **C2 counter drift on Phase-2 activation.** If counter is wrong when monetization starts, billing is wrong on day 1.
3. **C5 false positives drowning admin queue.** Erodes trust; admin stops triaging.

## Top operational risks

1. **OTP-delivery support load.** If Telegram-bot OTP excludes some users (no Telegram), support handles edge cases manually until SMS lands.
2. **Manual primary-phone-change flow.** No UI; ops handles. Document the SOP before C4 launch.
3. **C5 admin queue triage SLA.** No automation; if pairs accumulate faster than admins triage, the queue becomes useless. Define triage cadence.

## Top migration risks

1. **C4 user_phones backfill.** Mostly safe (one INSERT-from-SELECT), but document the recovery path if a user has anomalous data (NULL phone, malformed E.164).
2. **C2 Option A backfill.** Only relevant if Option A chosen; backfill must be idempotent.
3. **C3 enum additions.** Postgres requires `ADD VALUE` outside transactions in some cases; the alembic-block trick from Block A's PR-G applies.

## Top regression risks

1. **C4 parser/A4 query expansion.** Wrong query → entire claim flow stops working for users. Add a smoke test that exercises both single-phone and multi-phone seller cases.
2. **C2 middleware in test period returning true everywhere.** A bug returning false breaks listing creation for all sellers. Default-true logic is the safe path; gate the false branch behind `test_period_active=false` only.
3. **C1 endpoint serving stale data.** 1h cache could lie about progress; minor regression.

## Top UX risks

1. **C1 jargon leak ("Phase 2", "feature flag" in copy).** Erodes trust.
2. **C4 OTP delivery delay** (Telegram → bot push). Users on bad connection wait for code.
3. **C4 modal-on-delete-with-listings.** Three options is the right number, but the labels need polish: "Перенести на основной" sounds clinical; consider "Объявления переедут на основной номер" with a helper sentence.
4. **C5 soft prompt** (if shipped) — wording must avoid making the user feel accused.

## Recommended go / no-go gates before code merges

- [ ] Product confirms C2 Option A vs Option B (recommend B).
- [ ] Product confirms C2 grandfathering rule.
- [ ] Product confirms C3 lazy vs eager Wallet creation (recommend lazy).
- [ ] Product confirms C4 OTP delivery channel (recommend Telegram-bot for MVP).
- [ ] Product confirms C4 `Listing.phone` rename to `contact_phone`.
- [ ] Product confirms C4 `Seller.phone` deprecation (recommend yes).
- [ ] Infra confirms `fuzzystrmatch` Postgres extension available for C5.
- [ ] Native-speaker reviews `tariffs.*` and `phones.*` i18n keys.

When these eight gates pass, Block C can land in a 2-week calendar window with 3 devs (or 4-5 weeks with 1 senior dev).
