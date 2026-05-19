# Block C — Decision Matrix

This is the master index for the decision-resolution pass. Every open question raised in [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md) §4 is closed here, either as a **DECIDED** architecture call grounded in real code, or as **PRODUCT-CALL** flagged for the founder. No silent assumptions.

Status legend:
- 🟢 **DECIDED** — derivable from code + production constraints; rationale documented in linked file.
- 🟡 **RECOMMENDED** — multiple defensible answers; one recommendation backed by codebase precedent; product approval needed if they pick the alternative.
- 🔴 **PRODUCT-CALL** — genuine product/business decision; engineering can ship either path equivalently. Decision required before code merge.
- ⚫ **INFRA** — depends on external infra availability; needs ops team verification.

---

## Master matrix

| # | Question | Status | Decision / Recommendation | File |
|---|---|---|---|---|
| **OTP / authentication** |||||
| 1 | C4 OTP delivery channel — Telegram-bot vs SMS (Eskiz)? | 🟢 **DECIDED** | Telegram-bot only for MVP. Forced by code: zero SMS infra exists; Eskiz is a comment in `claims.py:157`. Adding Eskiz is a Phase-2 investment outside Block C scope. | [OTP_STRATEGY.md](OTP_STRATEGY.md) §2 |
| 2 | Hotfix `CacheKeys.otp()` AttributeError? | 🟢 **DECIDED** | Yes, in scope — it's a 4-line fix that unblocks the broken claim-OTP fallback path. Ship as a standalone hotfix PR before any C4 code. | [OTP_STRATEGY.md](OTP_STRATEGY.md) §3 |
| 3 | Harden the verify→create race in login OTP? | 🟢 **DECIDED** | Yes, fold into the same hotfix PR. `INSERT … ON CONFLICT (phone) DO NOTHING` plus `User.phone` UNIQUE (already exists) handles it. | [OTP_STRATEGY.md](OTP_STRATEGY.md) §4 |
| 4 | C4 "add additional phone" verify endpoint — creates a User? | 🟢 **DECIDED** | NEVER. Add-phone is auth-required and operates on `current_user`. New endpoint at `/sellers/me/phones/*`. Login OTP path is read-only from this contract. | [OTP_STRATEGY.md](OTP_STRATEGY.md) §5 |
| 5 | Redis-key namespace for add-phone OTP? | 🟢 **DECIDED** | `add_phone_otp:{user_id}:{last9}` and `add_phone_otp_attempts:{user_id}:{last9}`. Strict separation from login OTP keys. | [OTP_STRATEGY.md](OTP_STRATEGY.md) §6 |
| **Wallet (C3)** |||||
| 6 | Eager vs lazy Wallet creation? | 🟢 **DECIDED** | **Lazy.** Created on first deposit/adjust/balance-read via `INSERT … ON CONFLICT (user_id) DO NOTHING`. Aligned with codebase convention (no eager-derived-row hooks in user-creation). | [WALLET_LIFECYCLE.md](WALLET_LIFECYCLE.md) §1 |
| 7 | Money storage — `BIGINT` vs `Numeric(18,2)`? | 🟢 **DECIDED** | **BIGINT, smallest-currency-unit (UZS = 1 UZS, USD = 1 cent).** Matches `Listing.price` Integer precedent; no float-rounding hazards; easier debugging. Document the unit explicitly per column. | [MONEY_STORAGE_DECISION.md](MONEY_STORAGE_DECISION.md) |
| 8 | Multi-currency wallets — one per (user, currency) or fixed? | 🟢 **DECIDED** | **One Wallet per User, fixed currency = UZS in MVP.** Currency enum already has UZS+USD; service layer rejects non-UZS for now. Multi-currency is Phase-2/3. | [WALLET_LIFECYCLE.md](WALLET_LIFECYCLE.md) §2 |
| 9 | `Subscription.object_id` — FK or polymorphic? | 🟢 **DECIDED** | **Polymorphic (no FK).** Typed by `subscription.type`. Listings get `object_id=listing.id` semantically; cabinet subscriptions leave it NULL. Avoids cascade pain. | [WALLET_LIFECYCLE.md](WALLET_LIFECYCLE.md) §3 |
| 10 | Refund semantics — mutate original or link separate row? | 🟢 **DECIDED** | **Both:** original transaction's status flips `completed→refunded`; a separate refund Transaction is also inserted with `metadata.refund_of=<original_id>`. Audit-log both transitions. | [WALLET_LIFECYCLE.md](WALLET_LIFECYCLE.md) §4 |
| 11 | Click vs Payme integration priority for Phase 2? | 🟡 **RECOMMENDED** | Doesn't gate C3. Both stubs ship. Recommend Click first (more market share in UZ realtor segment); needs founder confirmation before Phase 2. | [WALLET_LIFECYCLE.md](WALLET_LIFECYCLE.md) §5 |
| 12 | Webhook signature algorithm — pin at adapter? | 🟡 **RECOMMENDED** | Each provider uses its own; Click uses MD5 + secret, Payme uses HMAC. Adapter Protocol's `verify_callback(payload, signature)` accepts the raw signature; per-adapter implementation owns the algorithm. | [WALLET_LIFECYCLE.md](WALLET_LIFECYCLE.md) §6 |
| 13 | Admin balance-adjust endpoint — single or split? | 🟢 **DECIDED** | **Single endpoint** with `type` discriminator (`grant` / `correction`). Mandatory `reason` field. Audit-logged. Mirrors A8 admin pattern. | [WALLET_LIFECYCLE.md](WALLET_LIFECYCLE.md) §7 |
| 14 | `Listing.is_boosted` coupling to wallet — in C3? | 🟢 **DECIDED** | **NO.** `is_boosted` stays a skeleton field in Block C; payment coupling is Phase-2 (D-block or beyond). C3 doesn't touch it. | [WALLET_LIFECYCLE.md](WALLET_LIFECYCLE.md) §8 |
| **C2 listing-limit** |||||
| 15 | Option A (fix counter via hooks) vs Option B (kill counter, live-query)? | 🟢 **DECIDED** | **Option B.** Live-query eliminates drift, avoids backfill, simpler code path. The denormalised counter becomes dead code; reads switch to the new helper. | [GRANDFATHERING_POLICY.md](GRANDFATHERING_POLICY.md) §1 |
| 16 | Grandfathering on flip day — A (grandfather), B (hard-block), C (30-day grace)? | 🟢 **DECIDED** | **Option A (grandfather).** All sellers' currently-ACTIVE listings remain active; only NEW creates above `free_limit` require payment. Simplest, lowest churn. | [GRANDFATHERING_POLICY.md](GRANDFATHERING_POLICY.md) §3 |
| 17 | PENDING_GENERATION counts toward limit? | 🟢 **DECIDED** | **NO.** Only `ACTIVE` and `GENERATION_FAILED` count (visible in B2C). PENDING is a transient state; charging would be unfair. | [GRANDFATHERING_POLICY.md](GRANDFATHERING_POLICY.md) §4 |
| 18 | GENERATION_FAILED counts? | 🟢 **DECIDED** | **YES.** It's visible in B2C with template description (per A7). Equivalent to ACTIVE for billing purposes. | [GRANDFATHERING_POLICY.md](GRANDFATHERING_POLICY.md) §4 |
| 19 | First-2-free rule — `Listing.created_at` order or live? | 🟢 **DECIDED** | **Live "oldest 2 currently ACTIVE/GF by `created_at` are free".** Sellers can swap free slots by archiving older listings. Predictable + flexible. | [GRANDFATHERING_POLICY.md](GRANDFATHERING_POLICY.md) §5 |
| 20 | Status transition counter rules in paid phase | 🟢 **DECIDED** | Live-query strategy makes this trivial — transitions just flip status; the count auto-corrects. Full table in spec. | [GRANDFATHERING_POLICY.md](GRANDFATHERING_POLICY.md) §6 |
| **Phone identity (C4)** |||||
| 21 | `User.phone` future — keep or migrate? | 🟢 **DECIDED** | **Keep.** It's the auth identifier (UNIQUE indexed since initial schema). Add `user_phones` for additional phones; primary phone always equals `User.phone`. | [PHONE_IDENTITY_MODEL.md](PHONE_IDENTITY_MODEL.md) §1 |
| 22 | `Seller.phone` future — keep or drop? | 🟡 **RECOMMENDED** | **Drop in Phase 2** after all readers are switched to `User.phone`. Today, Seller.phone mirrors User.phone. C4 PR doesn't drop it; documents as deprecated. | [PHONE_IDENTITY_MODEL.md](PHONE_IDENTITY_MODEL.md) §2 |
| 23 | `Listing.phone` rename to `contact_phone`? | 🟡 **RECOMMENDED** | **Defer.** Renaming requires touching every reader; risk > reward. Keep `phone`, document semantic ("the contact phone for this listing, must be one of the seller's verified phones"). | [PHONE_IDENTITY_MODEL.md](PHONE_IDENTITY_MODEL.md) §3 |
| 24 | Per-phone listing limit? | 🟢 **DECIDED** | **NO.** Limit is per-account. C2 spec already has this. C4 doesn't change it. | [PHONE_IDENTITY_MODEL.md](PHONE_IDENTITY_MODEL.md) §4 |
| 25 | Phone-removal soft-delete vs hard-delete? | 🟢 **DECIDED** | **Hard-delete after listing migration.** A phone removed via UI: listings either transfer or archive (3 modal options); only after the chosen action completes does the `user_phones` row delete. | [PHONE_IDENTITY_MODEL.md](PHONE_IDENTITY_MODEL.md) §5 |
| 26 | OTP language — follow user locale or pin? | 🟢 **DECIDED** | **Follow `User.language`.** OTP delivery via Telegram bot already has access to User row → language column. Pin to `ru` for users without language preference. | [PHONE_IDENTITY_MODEL.md](PHONE_IDENTITY_MODEL.md) §6 |
| 27 | Admin "swap primary phone" UI in scope? | 🟡 **RECOMMENDED** | **Yes, ship a small admin endpoint in C4 PR3** with full AuditLog. Spec implied "ops handles via support" — but ops needs an interface; the endpoint is < 30 lines. | [PHONE_IDENTITY_MODEL.md](PHONE_IDENTITY_MODEL.md) §7 |
| **C5 multi-account detection** |||||
| 28 | Levenshtein threshold for similar-names signal? | 🟢 **DECIDED** | **Edit-distance ≤ 2 AND suffix-match (last 4 chars) AND time-window (registration within 7 days)** to reduce noise. Tunable from settings. | [PHONE_IDENTITY_MODEL.md](PHONE_IDENTITY_MODEL.md) §8 |
| 29 | Soft user-side "merge accounts?" prompt — MVP or later? | 🟡 **RECOMMENDED** | **Defer.** Ship signal-detection + admin queue first; add user-side prompt only if false-positive rate stays low for 4+ weeks. | [GRANDFATHERING_POLICY.md](GRANDFATHERING_POLICY.md) §7 (cross-ref) |
| 30 | Device fingerprint — User column or AuditLog? | 🟢 **DECIDED** | **`User.last_register_ip` + `User.last_register_user_agent_hash` columns.** Cheap, fast, no AuditLog scan. AuditLog stays as an audit-trail, not a query target. | [PHONE_IDENTITY_MODEL.md](PHONE_IDENTITY_MODEL.md) §9 |
| **Cross-cutting** |||||
| 31 | Operational reality of Telegram-only OTP — accept that some users can't register? | 🟢 **DECIDED** | **Accepted.** Documented in user-facing copy as "регистрация через Telegram-бот". Support handles edge cases manually until SMS lands. | [INFRA_REQUIREMENTS.md](INFRA_REQUIREMENTS.md) §1 |
| 32 | `fuzzystrmatch` Postgres extension availability for C5? | ⚫ **INFRA** | Verify with infra team before C5 PR2 (signal tasks). If not present, must be installed. Block A's deploy server is `192.168.0.187` — checkable via `SELECT * FROM pg_extension WHERE extname='fuzzystrmatch'`. | [INFRA_REQUIREMENTS.md](INFRA_REQUIREMENTS.md) §2 |
| 33 | Redis load increase from new OTP namespaces + wallet locks | ⚫ **INFRA** | Estimate: ~3× current OTP key count (login + claim + add-phone) at MVP scale = trivial. Wallet locks are short-lived `SELECT FOR UPDATE` — no Redis hit. **No new infra.** | [INFRA_REQUIREMENTS.md](INFRA_REQUIREMENTS.md) §3 |
| 34 | Migration lock duration for new tables (wallet, user_phones, suspicions) | 🟢 **DECIDED** | All migrations are **purely additive** (CREATE TABLE / CREATE INDEX). Postgres takes brief ACCESS EXCLUSIVE on the table catalog only. No long row locks. Backfills are single INSERT-from-SELECT, run in low-traffic window. | [INFRA_REQUIREMENTS.md](INFRA_REQUIREMENTS.md) §4 |
| 35 | Telegram bot rate-limit risk from add-phone OTP delivery | 🟡 **RECOMMENDED** | Telegram allows ~30 messages/sec/bot. OTP volume MVP-scale is < 10/min. Headroom > 100×. **Monitor; no preemptive throttle.** | [INFRA_REQUIREMENTS.md](INFRA_REQUIREMENTS.md) §5 |
| 36 | Future SMS (Eskiz) integration path | 🟢 **DECIDED** | Adapter pattern: add `OTPDeliveryProvider` Protocol with `telegram_bot` (default) and `eskiz` (Phase-2) implementations. C4 endpoint accepts `delivery_channel` param; defaults to `telegram_bot`. | [INFRA_REQUIREMENTS.md](INFRA_REQUIREMENTS.md) §6 |

---

## Decisions resolved by codebase evidence — no product call needed

29 of 36 decisions are 🟢 DECIDED based on real-code constraints. These do not require founder/product input:

| Constraint that forced the decision | Affected decisions |
|---|---|
| `User.phone` is UNIQUE-indexed (initial schema) | #21, #25 |
| `Listing.price` is Integer (no Decimal anywhere) | #7 |
| Telegram-bot is the only OTP channel that exists | #1, #4, #5, #31 |
| `CacheKeys.otp()` is a missing method | #2 |
| `auth.py:957-1006` race already exists | #3 |
| AuditLog pattern is established (Block A) | #10, #13 |
| Block A precedent for ON CONFLICT additive merge | #6 |
| Block A precedent for SELECT FOR UPDATE | wallet concurrency throughout |
| `Seller.listings_count` is observably broken | #15, #16 |
| Buyer feed gates on `(ACTIVE, GENERATION_FAILED)` (A7) | #17, #18 |
| Spec V2.0 explicit decisions | #14 (is_boosted out of C3), #19 |

## Decisions still requiring product/founder confirmation

7 of 36 are 🟡 RECOMMENDED (engineering's best call; alternative is defensible):

- **#11** Click vs Payme priority (Phase-2; doesn't block C3)
- **#12** Webhook signature algorithm — Phase-2; per-adapter
- **#22** Drop `Seller.phone` in Phase 2?
- **#23** Rename `Listing.phone` → `contact_phone`?
- **#27** Admin "swap primary phone" UI in C4 PR3?
- **#29** C5 soft user-side prompt — MVP or later?
- **#35** Preemptive Telegram rate-limit throttle?

## Infra team confirmations needed

4 of 36 are ⚫ INFRA:

- **#32** `fuzzystrmatch` Postgres extension installed?
- **#33** Redis load headroom (estimated trivial; verify in production)
- **#34** Migration window for additive schema work
- **#36** Future SMS integration ops cost (Phase-2 budget)

---

## How to use this matrix

Before any C-block PR is merged, the relevant decision IDs from this matrix MUST be referenced in the PR description. Example:

> **Decision-pass refs:** Implements #6 (lazy Wallet), #7 (BIGINT money), #13 (single admin balance-adjust). PR-1 of C3.

This forces every implementation choice to trace back to a documented rationale or an explicit product call.

## Next step

Read the per-topic files for full rationale. Then [`FINAL_IMPLEMENTATION_GATES.md`](FINAL_IMPLEMENTATION_GATES.md) for the merge-readiness checklist.
