# Infrastructure Requirements — Decision Pass

This document closes the four ⚫ INFRA decisions from [`DECISION_MATRIX.md`](DECISION_MATRIX.md) and validates feasibility for everything Block C touches in the runtime environment. Anything that cannot be verified from the repository is explicitly marked **OPEN INFRA QUESTION** rather than guessed.

## §0 Inputs

The runtime environment, as observable from the repo:

- **Database:** Postgres at `192.168.0.187:5432/real_estate` (per `backend/.env`).
- **Redis:** localhost:6380, db 0 (settings) + db 1/2 for Celery broker/result.
- **Bot:** aiogram, token in `TELEGRAM_BOT_TOKEN`.
- **Background tasks:** Celery, beat schedule already populated by Block A.
- **Frontend:** Vite dev port 7878; Backend Uvicorn 7879; Meili 7700; Flower 5555.
- **Migrations head (post-Block A):** `pri_source_metric_notified`.

These are the inputs every section below validates against.

---

## §1 Decision #31 — Telegram-only OTP operational reality

🟢 **DECIDED: Accept that some users without Telegram cannot register, claim, or add phones.**

### What this means

The OTP delivery channel is exclusively Telegram bot DM (per [`OTP_STRATEGY.md`](OTP_STRATEGY.md)). For Block C:

- Login OTP: Telegram-only (existing).
- Add-phone OTP (C4): Telegram-only.
- Claim OTP fallback (post-hotfix): Telegram-only.

Users without an active Telegram account cannot complete any of these flows. **In Uzbekistan's realtor market, Telegram penetration is high but not 100%.**

### Operational mitigation

- **User-facing copy** explicitly says "регистрация через Telegram-бот" / "verification via Telegram bot". Do not advertise SMS where it doesn't exist.
- **Support runbook** entry: "If user reports they have no Telegram, route to manual ops escalation." A small minority; manual handling acceptable.
- **Post-launch monitoring:** track failed-OTP rate by failure mode (`TelegramForbiddenError`, no-response). If `TelegramForbiddenError` rate climbs, that's the signal SMS integration becomes a Phase-2 priority.

### When does this stop being acceptable?

- If support-ticket rate from "I have no Telegram" exceeds ~5% of new registrations.
- If a key business segment (e.g., older agencies) is structurally underserved.

Either trigger → SMS integration becomes a Phase-2 must.

---

## §2 Decision #32 — `fuzzystrmatch` Postgres extension

⚫ **OPEN INFRA QUESTION: Verify with infra team. Fallback path designed.**

### What needs verification

C5's "similar names" signal uses `levenshtein()` from the Postgres `fuzzystrmatch` extension.

```sql
-- This must succeed:
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
SELECT levenshtein('ivan', 'ivann');  -- expected: 1
```

### How to verify

```bash
# On the production DB host:
psql -U postgres -d real_estate -c \
  "SELECT * FROM pg_available_extensions WHERE name='fuzzystrmatch';"

# If installed_version is NULL but installed_version is non-NULL, run:
psql -U postgres -d real_estate -c "CREATE EXTENSION fuzzystrmatch;"
```

### Status today

Not verified by the audit. The repo doesn't include a migration creating the extension. C5's signal-tasks code can include `op.execute("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch")` in its first migration — but **only if the database role has the privilege**. RDS-style managed Postgres often requires admin access.

### Fallback if extension is unavailable

Implement Levenshtein in Python:

```python
# backend/app/services/text_similarity.py (fallback)
def levenshtein_distance(a: str, b: str) -> int:
    # Standard Wagner-Fischer; ~10 lines
    ...
```

Cost: O(N²) Python instead of O(N²) C extension. At MVP scale (signal task runs daily on a few thousand pairs), trivial. At scale, slower but bounded.

### Recommended action

- **Pre-flight check** in C5 PR1's migration: try `CREATE EXTENSION IF NOT EXISTS fuzzystrmatch`. If it fails (privilege error), the migration commits everything else and logs a warning. C5 signal-task implementation has both code paths (extension or Python fallback) and detects which is available at startup.

### When this becomes blocking

C5 PR2 (signal tasks). If the extension isn't available and the Python fallback isn't shipped, the similar-names signal can't run. **Schedule:** verify with infra **before C5 PR2 merge.**

---

## §3 Decision #33 — Redis load increase

🟢 **DECIDED: Trivial impact. No new infra.**

### Estimate

Block C adds these Redis key namespaces:

| Namespace | TTL | Read frequency | Write frequency |
|---|---|---|---|
| `add_phone_otp:{user_id}:{last9}` | 600s | per verify call (low) | per request-otp (low) |
| `add_phone_otp_attempts:{user_id}:{last9}` | 600s | per verify call | per failed attempt |
| `rate_limit:add_phone:{user_id}:{last9}` | 600s | per request-otp | per request-otp |
| `tariffs:status:v1` | 3600s | per page-load on `/seller/tariffs` | once per hour |

Total new keys per day at 50 active sellers: ~50 × 3 OTP types + 1 tariffs = **151 key-events per day**, mostly very-short-lived.

Postgres + Redis are already deployed; their workloads at MVP scale are < 1% of capacity. The new keys are < 1% of existing.

### Long-term concerns

- If add-phone usage exceeds expectation (e.g., 1 OTP/sec), Redis load rises but stays bounded.
- The wallet's `SELECT FOR UPDATE` operations don't touch Redis — they're DB-level locks.

### Action

None. Monitor; no preemptive scaling.

---

## §4 Decision #34 — Migration lock duration

🟢 **DECIDED: All Block C migrations are additive; lock duration is minimal.**

### Migrations to ship in Block C

| Migration | Type | Lock |
|---|---|---|
| `prj_wallet_billing` (C3) | `CREATE TABLE wallets, transactions, subscriptions` + new enums | brief ACCESS EXCLUSIVE on table catalog only |
| `prk_user_phone` (C4) | `CREATE TABLE user_phones` + INSERT-from-SELECT backfill | ms-scale; backfill is read-only on `users` |
| `prk2_phone_verify_attempt` (folded into prk) | `CREATE TABLE phone_verify_attempt` | brief ACCESS EXCLUSIVE on catalog |
| `prl_account_suspicion` (C5) | `CREATE TABLE account_suspicion, account_link` | brief ACCESS EXCLUSIVE on catalog |
| (Optional) `User.last_register_ip`, `User.last_register_user_agent_hash` columns | `ALTER TABLE users ADD COLUMN` | brief ACCESS EXCLUSIVE on `users` |

### Postgres lock semantics

- `CREATE TABLE` requires `ACCESS EXCLUSIVE` on `pg_class` for the new entry. Lock duration is microseconds.
- `ALTER TABLE … ADD COLUMN` (non-defaulted) is fast: it doesn't rewrite the table.
- `ALTER TABLE … ADD COLUMN … DEFAULT non-volatile-value` is fast since Postgres 11.
- `INSERT … SELECT` for backfill takes a **share lock** on `users` — concurrent reads succeed; concurrent writes serialize.

### Estimated wall-clock impact

At MVP scale (~thousands of users, low writes/sec):
- C3 migration: < 100 ms.
- C4 migration including backfill: < 1 second.
- C5 migration: < 100 ms.

### Operational window

Run migrations during low-traffic window (e.g., 4-5 am Tashkent — already used by Block A's beat tasks). Risk is bounded; rollback is `alembic downgrade -1` (drops the empty tables).

### Dangerous migration to flag

**Phase-2 cleanup migration:** `DROP COLUMN sellers.phone`. This is `ACCESS EXCLUSIVE` for the duration of the operation. Trivial at MVP scale (drops one column from a table with thousands of rows in milliseconds), but if the table grows large, schedule off-peak. Out of Block C scope.

---

## §5 Decision #35 — Telegram bot rate limits

🟡 **RECOMMENDED: Monitor; no preemptive throttle.**

### Telegram API limits (per bot)

- ~30 messages per second to different users.
- ~1 message per second to the same chat.

### Block C OTP load estimate

At MVP scale, peak OTP rate during seller-onboarding surge:
- 10 sellers/day register → 10 login OTPs.
- Of those, ~30% add 1-2 additional phones → 3-6 add-phone OTPs.
- Plus ~5 claim OTPs (rare due to phone-match fast path).

**Total: ~20-25 bot messages/day** related to OTP. Far below Telegram's per-second ceiling.

### Spike scenarios

- A marketing campaign causing 50 simultaneous registrations: 50 OTPs in a minute. Still 1 message/sec average per chat (since each chat is unique). Headroom > 100×.
- Group-batched A4 fanout (up to 5 listings per seller per batch): one batched message; not 5 individual messages. Already optimised in A4.

### Action

None preemptive. Bot's `send_message` calls already handle `TelegramForbiddenError` (per `notifications.py:119-120` audit). Monitor rate-limit responses (HTTP 429) post-launch; if they appear, add a token-bucket throttle.

---

## §6 Decision #36 — Future SMS (Eskiz) integration path

🟢 **DECIDED: Adapter pattern. C4 ships with Telegram-only; SMS slot reserved.**

### Architecture

The OTP-delivery service can be made channel-pluggable without committing to SMS today:

```python
# backend/app/services/otp_delivery.py (sketch, NOT for MVP)
async def deliver_otp(user: User, phone: str, code: str, channel: str = "telegram") -> bool:
    if channel == "telegram":
        return await _deliver_via_telegram(user, code)
    elif channel == "sms":  # Phase 2
        return await _deliver_via_eskiz(phone, code)
    raise ValueError(f"Unknown OTP channel: {channel}")
```

In MVP, every callsite passes `channel="telegram"` (or omits, defaulting). Phase 2 introduces `channel="sms"` paths.

### Why not Protocol/ABC?

The codebase prefers config-driven if/elif (search-backend toggle). Aligning with that style avoids over-abstraction.

### What Phase 2 would require

- **Eskiz (or chosen SMS provider) account** + API key.
- **Recurring SMS quota cost.** Estimate: ~50 SMS/day at < $0.01 each = ~$15/month. Trivial.
- **`SMS_PROVIDER`, `SMS_API_KEY`, `SMS_API_URL` env vars** added to settings + `.env.example`.
- **`backend/app/services/payment_providers/eskiz.py`** (analog of Click/Payme adapters).
- **Webhook for delivery receipt** (optional; provides ops visibility).
- **i18n SMS templates** in 3 locales (different format vs Telegram).
- **Frontend channel selector** (if user is given a choice).

Estimated work: 2-3 dev-days BE + 0.5 day FE + ops setup.

### When to ship

When the support-ticket rate from "I can't register, no Telegram" passes ~5% of new registrations.

---

## §7 OPEN INFRA QUESTIONS

These items the audit could not resolve from the repo alone. Each requires confirmation from the infra team or operator before merging the relevant Block C PR.

| # | Question | Required for | Severity |
|---|---|---|---|
| OQ-1 | Is `fuzzystrmatch` Postgres extension installable on the production DB? | C5 PR2 | MEDIUM |
| OQ-2 | What's the production Postgres version? `levenshtein()` exists since fuzzystrmatch 1.0 (very old). | C5 PR2 | LOW |
| OQ-3 | Is the production DB on a managed Postgres service (RDS, Cloud SQL, self-hosted)? Determines admin-privilege availability. | C5 PR2 + Phase-2 migrations | LOW |
| OQ-4 | Postgres connection-pool size during migrations? Backfill on `users` (C4) needs at least one available connection. | C4 PR1 | LOW |
| OQ-5 | Bot rate-limit headroom in production: any current rate-limit incidents? | C4 PR2 | LOW |
| OQ-6 | Wallet/transaction tables: estimated row count over Phase-2 timeline? Drives index-strategy review. | C3 (post-Phase-2) | LOW |
| OQ-7 | Audit-log retention policy: does any cleanup task purge old AuditLog rows? Impacts forensic capability. | C5 (signal evidence storage) | LOW |
| OQ-8 | Backup frequency / RTO for the production DB. Drives rollback strategy for any data-touching migration. | All migrations | MEDIUM |
| OQ-9 | Secret-manager target (Vault, AWS Secrets, encrypted env file)? Click/Payme keys live there in Phase 2. | C3 (Phase-2 activation) | MEDIUM |
| OQ-10 | Click/Payme webhook IP allowlist requirements? Both providers send from fixed IPs; firewall rules needed. | C3 (Phase-2 activation) | MEDIUM |

**These do not block C3, C4, or C2 PR1.** They become relevant at the listed gates.

---

## §8 Pre-merge infra checklist

Before any Block C PR merges to main:

- [ ] Confirmed deploy window for migrations (off-peak Tashkent time).
- [ ] Confirmed alembic-rollback rehearsal succeeded on staging.
- [ ] Confirmed Redis is reachable from worker processes (Celery beat will use new tariffs:status cache).
- [ ] Confirmed bot is reachable for OTP delivery (smoke test with one synthetic OTP).
- [ ] OQ-1, OQ-3 resolved if C5 PR2 is in this release.
- [ ] OQ-8 (backup status) confirmed before any data-touching migration.
- [ ] `.env.example` updated for new env vars (no live values committed).

---

## §9 Operational checkpoints during rollout

| Phase | Checkpoint | Owner |
|---|---|---|
| Pre-merge | Migration rehearsal on staging | DBA / Backend |
| At merge | CI green; `alembic upgrade head` succeeds locally | Reviewer |
| Post-deploy (T+0) | Smoke test all new endpoints (admin balance-adjust, add-phone, etc.) | QA |
| T+1 hour | Monitor error rate; spot-check 5 sellers' counts via admin tool | Ops |
| T+24 hours | Review C5 admin queue for anomalous signals; verify wallet operations clean | Ops + Backend |
| T+7 days | Review subscription rate, support ticket volume, OTP delivery success rate | Ops + Founder |

---

## §10 Cross-spec links

- [`DECISION_MATRIX.md`](DECISION_MATRIX.md) — master matrix.
- [`OTP_STRATEGY.md`](OTP_STRATEGY.md) — OTP delivery + rate-limit design.
- [`WALLET_LIFECYCLE.md`](WALLET_LIFECYCLE.md) — wallet locking + concurrency.
- [`PHONE_IDENTITY_MODEL.md`](PHONE_IDENTITY_MODEL.md) — phone-touchpoint inventory.
- [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md) — production-state evidence.
