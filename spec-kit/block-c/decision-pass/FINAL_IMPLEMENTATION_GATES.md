# Final Implementation Gates — Block C

This is the final gate-clearance document for Block C. Before any code is written, every item below must be either ✅ resolved or 📋 explicitly accepted-as-pending with a named owner.

The decision pass closed 29 of 36 questions from [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md). The remaining 7 are operational confirmations, not design choices. Implementation can begin **as soon as the gates in §1 below are confirmed.**

## §1 Required confirmations before any Block C code merges

These are the gates that, if unanswered, would force re-architecture. **All MUST be confirmed before the first PR.**

| # | Gate | Status | Owner | Resolution |
|---|---|---|---|---|
| G1 | C4 OTP delivery channel = Telegram-bot for MVP | 🟢 closed | engineering | Forced by code: no SMS infra exists. Telegram-bot only. |
| G2 | C2 strategy = Option B (kill counter, live-query) | 🟢 closed | engineering | Architecturally superior; eliminates drift; no migration. |
| G3 | C3 money storage = BigInteger smallest-currency-unit | 🟢 closed | engineering | Matches `Listing.price` precedent; no Decimal anywhere in codebase. |
| G4 | C2 grandfathering policy = Option A (grandfather all) | 🟢 closed | engineering + founder | Grounded in spec V2.0 trust-contract; lowest-churn migration path. |
| G5 | `User.phone` UNIQUE invariant preserved (not relaxed) | 🟢 closed | engineering | Existing DB constraint; required by 6+ critical paths. |
| G6 | Wallet creation = lazy with `INSERT … ON CONFLICT DO NOTHING` | 🟢 closed | engineering | Codebase precedent (source_metric); zero backfill. |
| G7 | `Listing.is_boosted` stays out of Block C scope | 🟢 closed | engineering + founder | Skeleton field; payment coupling is Phase-2. |
| G8 | Click/Payme adapters ship as stubs in C3; integration is Phase 2 | 🟢 closed | engineering + founder | Scope-creep prevention; zero new env vars with values. |
| G9 | C5 phone-collision signal respects C4 multi-phone aggregation | 🟢 closed | engineering | Forced ordering: C4 schema lands before C5 PR2. |
| G10 | `CacheKeys.otp` AttributeError hotfix ships standalone before C4 | 🟢 closed | engineering | Independent; one-line fix; unblocks claim-OTP fallback. |

**All 10 are 🟢 closed.** Block C is unblocked on architecture grounds.

## §2 Operational confirmations before specific PRs

These are infra/ops items that block specific PRs but not the block as a whole. They can be resolved in parallel with code work.

| # | Gate | Required before | Owner |
|---|---|---|---|
| O1 | `fuzzystrmatch` Postgres extension installed on production DB | C5 PR2 | infra team |
| O2 | Migration deploy window confirmed (low-traffic Tashkent time) | C3 PR1, C4 PR1, C5 PR1 | infra team |
| O3 | Redis backup verified before C3 schema deploy | C3 PR1 | infra team |
| O4 | Backup retention policy confirmed for production DB | All schema migrations | infra team |
| O5 | Native-speaker review of new `tariffs.*` and `phones.*` i18n keys | C1 PR2, C4 PR4 | operations |
| O6 | Support runbook entries for: (a) seller without Telegram, (b) primary-phone swap request, (c) wallet adjustment request | Pre-launch | operations |
| O7 | Bot rate-limit monitoring dashboard wired (existing infra) | Post-deploy of C4 PR2 | ops |

**These do not block code authoring.** Engineering can write PRs while ops resolves these in parallel.

## §3 Product confirmations recommended (not blocking)

These 7 questions remain 🟡 RECOMMENDED — engineering's best call, but the founder may want to override. **They do NOT block implementation; they block one merge each at most.**

| # | Question | Recommendation | Affects |
|---|---|---|---|
| P1 | Click vs Payme priority for Phase 2 | Click first | C3 stub PR (cosmetic only); Phase-2 ordering |
| P2 | Webhook signature algorithm — pin or per-adapter | Per-adapter (Protocol surface accepts raw signature) | C3 PR2 (adapter Protocol) |
| P3 | Drop `Seller.phone` in Phase 2? | Yes, after Phase-2 cleanup | Phase-2 cleanup migration only |
| P4 | Rename `Listing.phone` → `contact_phone`? | Defer (avoid churn) | C4 PR3 docstring only |
| P5 | Admin "swap primary phone" UI in C4 PR3? | Yes, ship a small endpoint | C4 PR3 |
| P6 | C5 user-side soft prompt to merge accounts? | Defer to post-launch (false-positive risk) | C5 PR5 (optional) |
| P7 | Preemptive Telegram rate-limit throttle? | Monitor; no preemption | C4 PR2 (no code change today) |

If founder doesn't override within ~2 weeks, engineering proceeds with the recommendations.

## §4 PR sequence — clear-to-author table

Once the §1 gates are confirmed (they all are 🟢), engineering may begin authoring PRs **in this order**. Each PR's prerequisites are listed.

| Order | PR | Prerequisites | Estimated effort |
|---|---|---|---|
| 1 | **Hotfix:** `CacheKeys.otp` + verify→create race | None (G10) | 0.5 day BE |
| 2 | **C1 PR1 (BE):** config knobs + `GET /tariffs/status` endpoint | None | 0.5 day BE |
| 3 | **C1 PR2 (FE):** tariff page + nav + i18n | C1 PR1 merged + native-speaker review (O5) | 1.5 days FE |
| 4 | **C1 PR3 (FE):** banners on My Listings + 3rd-create hint | C1 PR2 merged | 0.5 day FE |
| 5 | **C2 PR1 (BE):** `listing_quota.py` + dashboard extension + middleware | None (independent of C1) | 1.5 days BE |
| 6 | **C2 PR2 (FE):** header chip + info-toast | C2 PR1 merged | 0.5 day FE |
| 7 | **C3 PR1 (BE schema):** `prj_wallet_billing` migration + models | None | 0.5 day BE |
| 8 | **C3 PR2 (BE services):** `wallet.py` + adapter Protocol stubs + tests | C3 PR1 merged | 2 days BE |
| 9 | **C3 PR3 (BE admin):** balance-adjust endpoint + AuditLog wiring | C3 PR2 merged | 0.5 day BE |
| 10 | **C3 PR4 (config):** Click/Payme env-var slots + `.env.example` | None (parallel with above) | 0.25 day BE |
| 11 | **C4 PR1 (BE schema):** `user_phones` + `phone_verify_attempt` + backfill | Hotfix (PR1) merged | 1 day BE |
| 12 | **C4 PR2 (BE endpoints):** request-otp / verify-otp / list / delete | C4 PR1 merged | 2 days BE |
| 13 | **C4 PR3 (BE query expansion):** parser/A4 set-membership; admin swap-primary | C4 PR1 merged | 1 day BE |
| 14 | **C4 PR4 (FE):** "My Phones" page + listing-create phone-picker + post-claim hint | C4 PR2 + C4 PR3 merged + native-speaker review (O5) | 2 days FE |
| 15 | **C5 PR1 (BE schema):** `account_suspicion` + `account_link` + User device columns | C4 PR1 merged | 0.5 day BE |
| 16 | **C5 PR2 (BE signals):** five Celery tasks + beat schedule | C4 PR3 merged + O1 confirmed | 3 days BE |
| 17 | **C5 PR3 (BE admin):** `admin_suspicions.py` endpoints | C5 PR1 merged | 1 day BE |
| 18 | **C5 PR4 (FE):** admin queue page + drawer + actions + i18n | C5 PR3 merged | 1.5 days FE |
| 19 | **C5 PR5 (FE optional):** soft user-side merge-accounts prompt | C5 PR4 merged + 4-week observation | 0.5 day FE |

**Total: ~22 dev-days** for the full block at single-dev sequential. Parallel-3-dev ~10-12 days as documented in [`../EXECUTION_PLAN.md`](../EXECUTION_PLAN.md).

## §5 Implementation hard-rules (non-negotiable)

These are quality bars enforced at code review, derived from the decision pass:

1. **No hardcoded UZS amounts in TSX or Python.** Read from `settings.extra_listing_price_uzs` etc.
2. **No engineering vocabulary in user-facing strings** ("Phase 2", "feature flag", "migration"). Strings go through i18n.
3. **No `Decimal` in any wallet/transaction/subscription model.** BigInteger only.
4. **No production calls to `wallet.withdraw` or `wallet.deposit` during test period.** Verified via grep.
5. **Every Transaction state change writes an AuditLog row in the same DB transaction.** Pattern is mandatory.
6. **Every wallet-mutating service call holds `SELECT FOR UPDATE` on the wallet row.** No exceptions.
7. **Every Transaction has a unique `idempotency_key`.** Webhook re-delivery tested.
8. **Every PR title cites the decision IDs from `DECISION_MATRIX.md` it implements.** PR description includes the matrix line.
9. **`User.phone` UNIQUE constraint is preserved.** Any change touching `users.phone` requires re-validation.
10. **C5 signal tasks gated until C4 PR3 lands.** Beat schedule disabled in C5 PR2; manually enabled after C4 PR3 verified.

## §6 What stays out of Block C scope

These items are deliberately deferred. Block C's PRs MUST NOT include them.

| Out of scope | Reason | Re-introduce in |
|---|---|---|
| Click webhook integration | Real money, real ops | Phase 2 |
| Payme webhook integration | Same | Phase 2 |
| Seller-facing topup UI | No flow needed during test period | Phase 2 |
| Subscription auto-renewal beat task | No subscriptions billable yet | Phase 2 |
| Listing auto-archive on grace exhaustion | No paid listings yet | Phase 2 |
| Boost-purchase flow | Skeleton field only | Phase 2 / D-block |
| Multi-currency wallets | UZS-only MVP | Phase 2/3 |
| SMS (Eskiz) integration | Telegram-only MVP | Phase 2 (when support-ticket rate justifies) |
| Финальная цена сделки field | Spec V2.0 deferral | Phase 2 |
| C5 user-side merge prompt | False-positive risk pre-launch | Post-launch observation |
| Drop `Seller.phone` column | Risk-budget controlled | Phase 2 cleanup |
| Rename `Listing.phone` → `contact_phone` | Churn vs benefit mismatch | Phase 2 cleanup |
| WCAG AA contrast / tap-target sizing | B6 covers WCAG-A | Block-B follow-up |
| Wallet statement export | Phase-2 product surface | Phase 2 |

## §7 Production smoke tests (post-deploy)

After each PR ships to production:

| PR | Smoke test |
|---|---|
| Hotfix | Trigger a non-phone-match claim flow; verify no AttributeError; verify Redis key created at `otp:{phone}` |
| C1 PR1 | `curl /tariffs/status` returns expected JSON; cache invalidates after 1h |
| C1 PR2 | Load `/seller/tariffs` in 3 locales; no console errors; disabled-CTA modal opens |
| C1 PR3 | Banner visible on `/seller/listings`; 3rd-create info-toast visible on next-create |
| C2 PR1 | `/sellers/me/dashboard` returns `total_billable_listings` matching live count |
| C2 PR2 | Header chip + info-toast visible |
| C3 PR1 | `alembic current` shows `prj_*`; no rows in any new table |
| C3 PR2 | Unit tests pass with property-based concurrency tests; `wallet.withdraw` raises `InsufficientFunds` correctly |
| C3 PR3 | `POST /admin/wallets/{id}/adjust` succeeds with reason; AuditLog row visible |
| C3 PR4 | New env-var slots visible in `.env.example`; no values committed |
| C4 PR1 | `alembic current` shows `prk_*`; backfill produced one row per existing user with phone |
| C4 PR2 | Request OTP via `POST /sellers/me/phones/request-otp`; verify-otp; row added to `user_phones` |
| C4 PR3 | Synthetic test: a seller with two verified phones receives matched listings for both via /found |
| C4 PR4 | "My Phones" page renders; phone picker on listing-create works |
| C5 PR1 | `alembic current` shows `prl_*`; signal tasks not yet running (beat disabled) |
| C5 PR2 | Beat enabled; first day's run produces zero false positives in admin queue (manual review) |
| C5 PR3 | `POST /admin/suspicions/{id}` actions work; AuditLog row visible |
| C5 PR4 | Admin sees pending suspicions; can resolve/ignore/link/block |

## §8 Rollback plans (per PR)

| PR | Rollback |
|---|---|
| Hotfix | Revert PR; behaviour returns to broken-but-not-actually-running |
| C1 PR1 | Revert; endpoint returns 404 |
| C1 PR2-3 | Revert; UI hidden |
| C2 PR1 | Revert; existing buggy counter resumes |
| C2 PR2 | Revert; UI reverts |
| C3 PR1 | `alembic downgrade -1` drops empty tables |
| C3 PR2 | Revert; services exist as dead code (no callers) |
| C3 PR3 | Revert; admin endpoint disappears |
| C4 PR1 | `alembic downgrade -1`; backfill data preserved by NOT auto-deleting `user_phones` rows |
| C4 PR2 | Revert; new endpoints 404 |
| C4 PR3 | Revert; query expansion reverts to single-column. Existing users continue to work (their primary phone is still in user_phones; the single-column query falls back to `User.phone`). |
| C4 PR4 | Revert; UI reverts to single-phone form |
| C5 PR1-4 | Revert each; tables stay (additive); beat schedule paused |

**Rollback for C4 schema (PR1)** is the most-touched: the `user_phones` table has data after backfill. Don't auto-drop on rollback; manual drop after verification that no future PR depends on it.

## §9 Decision-pass index

For implementers, every PR description should reference:

- `DECISION_MATRIX.md` line(s) implemented
- `OTP_STRATEGY.md` / `WALLET_LIFECYCLE.md` / `GRANDFATHERING_POLICY.md` / `PHONE_IDENTITY_MODEL.md` / `MONEY_STORAGE_DECISION.md` / `INFRA_REQUIREMENTS.md` section(s)
- Original spec file (`../medium/Cn-*.md` or `../hard/Cn-*.md`)

## §10 Done condition

Block C is complete when:

- All 19 PRs in §4 have merged.
- Production smoke tests in §7 pass for every PR.
- The 10 implementation hard-rules in §5 hold true for every shipped piece of code.
- The truth-layer audit's open questions list is fully resolved (29 closed via decision pass; 7 ops-confirmed by §2).
- One full week of post-deploy observation shows no AuditLog gaps, no wallet-balance reconciliation alerts, no C5 false-positive flood.

At that point, Block C is **architecture-complete** and Phase 2 (the actual monetization activation) becomes the next planning surface.

## §11 Cross-spec links

- [`DECISION_MATRIX.md`](DECISION_MATRIX.md) — master matrix; this document operationalises it.
- [`OTP_STRATEGY.md`](OTP_STRATEGY.md) — gates G1, G10.
- [`WALLET_LIFECYCLE.md`](WALLET_LIFECYCLE.md) — gates G3, G6, G7, G8.
- [`GRANDFATHERING_POLICY.md`](GRANDFATHERING_POLICY.md) — gates G2, G4.
- [`PHONE_IDENTITY_MODEL.md`](PHONE_IDENTITY_MODEL.md) — gate G5, G9.
- [`MONEY_STORAGE_DECISION.md`](MONEY_STORAGE_DECISION.md) — gate G3.
- [`INFRA_REQUIREMENTS.md`](INFRA_REQUIREMENTS.md) — operational gates O1-O7.
- [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md) — production-state foundation.
- [`../README.md`](../README.md), [`../EXECUTION_PLAN.md`](../EXECUTION_PLAN.md), [`../READINESS_REPORT.md`](../READINESS_REPORT.md) — original Block C kit.
