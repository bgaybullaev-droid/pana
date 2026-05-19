# Block C — Tariff Infrastructure & Strategic Groundwork (V2.0)

Block C is five tasks. The product is **free for all** in the test period, but a tariff structure is visible from day 1, the listing-counter is correct, and the wallet/transaction/subscription tables are ready to receive real money once monetization is activated. C4 + C5 fix the multi-phone-realtor reality and the predictable bypass-via-multi-account incentive that the free-tier creates.

V2.0 changes (per source spec): "финальная цена сделки" moved to Phase 2; new C4 ("multi-phone connection") replaces it; C5 updated to recognise legitimate multi-phone aggregation.

## Folder structure

```
spec-kit/block-c/
├── README.md
├── EXECUTION_PLAN.md
├── READINESS_REPORT.md
├── easy/                    (empty — every C task is at least medium)
├── medium/
│   ├── C1-tariff-display.md
│   └── C2-free-limit-logic.md
└── hard/
    ├── C3-wallet-architecture.md
    ├── C4-multi-phone-connection.md
    └── C5-multi-account-detection.md
```

## Status snapshot at write-time (real code, not spec)

| Task | Complexity | Spec status | One-line essence |
|---|---|---|---|
| [C1 — Tariff display](medium/C1-tariff-display.md) | MEDIUM | NOT STARTED | New `/seller/tariffs` route + config knobs + `GET /tariffs/status` endpoint + i18n. UI-only. |
| [C2 — Free-limit logic](medium/C2-free-limit-logic.md) | MEDIUM | NOT STARTED | `Seller.listings_count` is broken (counts non-deleted, not active). Live-query helper + feature-flag-gated middleware. |
| [C3 — Wallet architecture](hard/C3-wallet-architecture.md) | HARD | NOT STARTED | Three new tables (Wallet/Transaction/Subscription) + idempotent withdraw service + Click/Payme stubs + admin balance-adjust. |
| [C4 — Multi-phone connection](hard/C4-multi-phone-connection.md) | HARD | NOT STARTED | New `user_phones` table + OTP verify + listing-create phone-picker + parser/A4 query expansion to set-membership. |
| [C5 — Multi-account detection](hard/C5-multi-account-detection.md) | HARD | NOT STARTED | Five signal tasks + admin queue. **Hard-blocked on C4** because phone-collision signal must respect legitimate aggregation. |

## Distribution

- **Easy: 0**
- **Medium: 2** (C1, C2)
- **Hard: 3** (C3, C4, C5)

## Real-code findings that shaped the specs

1. **`Seller.listings_count` is broken for billing purposes.** Block A wired increment hooks at every create/claim site (`listings.py:2849`, `claims.py:113, 232`, `crawler_service.py:608, 685`) but the field counts everything not-soft-deleted; status transitions don't update it. C2 either rewrites it or replaces with a live `count(*) WHERE status=ACTIVE` helper. **Recommendation: live-query.**
2. **`prf_canonicalize_phone` (Block A migration) collapsed phones to one-per-account.** That's a hard invariant in production today. C4's multi-phone story has to **layer on top** without breaking it: primary phone stays on `User.phone` for auth, additional phones go to a new `user_phones` table.
3. **OTP infra is Telegram-bot-only, not SMS.** `auth.py:767-906` uses the bot to deliver codes. Eskiz.uz is mentioned in `CLAUDE.md` but never integrated, no env vars, no client. **C4's "SMS verification" is an open product/infra question.**
4. **`Listing.is_boosted` is a skeleton field with no payment coupling.** Code comment explicitly says `"# Promotion (Phase 2)"`. C3 doesn't touch it.
5. **`AuditLog` is generic enough to be the audit trail for transactions, suspicions, and admin balance adjustments.** All three uses are wired the same way: `entity_type='transaction'|'user_suspicion'|'wallet'`, `old_values`/`new_values` JSONB.
6. **`signature_hash` is already on `TelegramListing` / `OLXListing`** and computed by Block A V2.0's updated `generate_signature` (phone + area + floor + price ±5%). C5 reuses it for cross-account collision detection.
7. **No payment-provider env vars in `config.py`.** No `CLICK_*`, `PAYME_*`, `MERCHANT_*`. C3 adds the slots blank.
8. **No system-wide listing-count endpoint.** `/sellers/me/dashboard` is per-seller. C1 needs a new public-but-cached `GET /tariffs/status` to expose aggregate data for the trigger-progress block.

## Cross-task dependency graph

```
                               ┌─────────────────┐
                               │ A6 i18n base    │← done
                               │ A7 ListingStatus│
                               │ AuditLog        │
                               └───────┬─────────┘
                                       │
            ┌──────────────┬───────────┴───────────┬──────────────┐
            ▼              ▼                       ▼              ▼
        C1 (display)  C2 (counter)             C3 (wallet)    C4 (phones)
            │              │                       │              │
            │              │                       │              │
            ├──── reads ──→ test_period_active     │              │
            │              flag (C1's responsibility)             │
            │              │                       │              │
            │              └────── consults ──────→C3 (paid phase│ ▲
            │                                       only)         │ │
            │                                                     │ │
            └─→ disabled CTAs eventually call C3                  │ │
                                                                  ▼ │
                                                              C5 (detection)
                                                              hard-blocked on C4
```

## Dependency facts

| Task | Hard upstream deps | Soft upstream | Blocks |
|---|---|---|---|
| **C1** | A6 (done) | C2 (counter copy) | — |
| **C2** | A7 (done), C1 (`test_period_active` flag) | — | C3's paid-phase activation reads from C2 |
| **C3** | AuditLog (done), Currency enum (done) | — | Phase-2 monetization activation |
| **C4** | A1, A4 (done), `prf_canonicalize_phone` (done) | A8 admin pattern (done) | C5 (false-positive suppression) |
| **C5** | C4 schema must ship first | A7 signature_hash (done), AuditLog (done), A8 pattern (done) | — |

## V2.0 invariants the specs assume

1. **"Тестовый период" in UI; "Phase 1/2" in code.** Two vocabularies, never mixed in the same artifact.
2. **No price hardcoded in TSX.** All UZS amounts come from `backend/app/core/config.py` via `GET /tariffs/status`.
3. **Pay buttons are visually present from day 1**, but disabled with an info-modal that explains the test period.
4. **Counter is status-aware.** `status=ACTIVE AND deleted_at IS NULL` is the only definition of "active listing".
5. **Quota enforcement is feature-flag-gated.** `check_can_create_listing` always returns true when `test_period_active=true`.
6. **One `Wallet` per `User`.** Multi-currency wallets are out of MVP.
7. **All money in `Numeric(18,2)`.** No floats, ever.
8. **Phone verification is OTP-based.** Whether SMS (Eskiz) or Telegram-bot — open question; default Telegram-bot for MVP.
9. **`User.phone` remains the auth primary**; `user_phones` is the source of truth for "all my verified phones".
10. **No automatic blocks in C5.** Every status change is admin-driven.
11. **C4-aware false-positive suppression in C5** — phone-collision never fires when both phones aggregate under the same user via `user_phones`.

## Suggested execution order

See [EXECUTION_PLAN.md](EXECUTION_PLAN.md) for full phasing. High-level:

1. **C1 + C2** in parallel (UI + counter cleanup; both light).
2. **C3** (wallet schema + services; foundation, no UI).
3. **C4** (multi-phone + parser/A4 expansion).
4. **C5** (detection; depends on C4).

## Open questions tracked in specs

- **C1:** A/B price segmentation architecture today vs later? `test_period_started_at` source of truth (config vs DB)?
- **C2:** Live-query (recommended) vs denormalised counter? What happens when test-period flag flips and seller has 5 active? (grandfather all)
- **C3:** Lazy vs eager Wallet creation? Multi-currency wallets? Refund chain handling? Click vs Payme priority?
- **C4:** **SMS (Eskiz) vs Telegram-bot OTP?** Listing.phone column rename? `Seller.phone` future?
- **C5:** Levenshtein threshold for similar names? Soft user-side prompt — ship in MVP or wait?

## Conventions

- File paths repo-root-relative.
- Line numbers reflect state at write-time (May 2026); treat as starting points.
- Cross-spec links use relative paths.
- Every spec independently readable.
- Open questions explicit; no silent product assumptions.
