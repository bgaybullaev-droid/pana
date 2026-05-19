# C5 — Base multi-account detection (admin alerts only)

**Status:** NOT STARTED — no detection code, no admin queue, no suspicion table, no device-fingerprint persistence on `User`. `AuditLog` exists and could record alerts; `signature_hash` exists on source listings (Block A V2.0 added the floor + price bucket).
**Complexity:** HARD — five distinct signal types, multi-source data, cross-account correlation, admin queue UI, mandatory C4-aware false-positive suppression. Detection is by nature noise-prone and the spec is explicit that alerts must NEVER auto-block.
**Block-C V2.0 ref:** C5.
**Why now:** the free-listing-limit (C2) creates an obvious bypass incentive; a baseline detector keeps that visible to admin without overreaching. Has to land *after* C4 because C4's legitimate-aggregation logic is the primary false-positive suppressor.

## What's done

- **Per-listing signature** — `crawler_service.generate_signature(...)` (post-A7) computes `phone + area + floor + price_bucket` hash, stored as `signature_hash` on `TelegramListing` and `OLXListing`. Used for within-source dedup today; **available** for cross-source/cross-account correlation.
- **`AuditLog` model** at `backend/app/db/models.py:1316-1345` — captures `entity_type`, `entity_id`, `action`, `old_values`/`new_values`, `ip_address`, `user_agent`. Could record alert events.
- **Admin endpoint pattern** — A8's `admin_sources.py` is the template for a new `admin_suspicions.py` (list + actions + per-row metrics).
- **Admin queues precedent** — `backend/app/api/v1/admin.py:482-565` (listing approve/reject) and `:273-326` (user approve/reject) show the moderation-queue pattern.
- **Notification model** — `Notification` exists with types, but no admin-alert variant. New variant addable.

## What's missing

1. **No persistence of registration metadata on User.** `auth.py` doesn't store `ip_address`, `user_agent`, Telegram `init_data` hash, or session fingerprint on `User`. AuditLog has them only on the row that recorded the registration action (if any).
2. **No suspicion table.** No way to persist "these N accounts are under review", "marked legit", "ignore", "flagged", "linked".
3. **No signal collection.** Five spec'd signals — none are computed today.
4. **No admin queue UI.** No `/admin/suspicions` page.
5. **No "marked as legitimately related" mechanism.** Today there's no concept of "linked accounts" — but C5 needs it to suppress signals once an admin says "yes, these belong together".
6. **No C4 awareness.** Phone-collision signal must NOT fire when both listings are owned by the same User via the multi-phone aggregation. C5 cannot be implemented before C4's `user_phones` table exists.
7. **No abuse-rate-limiting on phone verification.** Spec mentions "suspicious verify patterns" (one phone tried by multiple accounts within a day). C4 needs to log verification attempts somewhere C5 can read.
8. **No name-similarity infra.** No fuzzy-match library, no normalised-name column. (Acceptable for MVP — keep it simple substring/Levenshtein.)
9. **No alerts-to-admin notification path.** Today's `Notification` is user-facing; there's no admin-side digest.

## Path to DONE

### Step 1 — schema

Migration `prl_account_suspicions.py`:

```python
op.create_table(
    "account_suspicion",
    sa.Column("id", UUID, primary_key=True, default=uuid4),
    sa.Column("user_a_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"),
              nullable=False, index=True),
    sa.Column("user_b_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"),
              nullable=False, index=True),
    sa.Column("signal_types", ARRAY(sa.String), nullable=False),  # multi-signal aggregate
    sa.Column("first_detected_at", sa.DateTime, server_default=sa.func.now()),
    sa.Column("last_detected_at", sa.DateTime, server_default=sa.func.now(),
              onupdate=sa.func.now()),
    sa.Column("status", sa.Enum("open", "ignored", "linked_legitimate", "blocked",
              name="suspicion_status"), nullable=False, server_default="open"),
    sa.Column("evidence", JSONB, nullable=False, server_default="{}"),
    sa.Column("reviewed_by_user_id", UUID,
              sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    sa.Column("reviewed_at", sa.DateTime, nullable=True),
    sa.Column("review_notes", sa.Text, nullable=True),
)
op.create_index("uq_suspicion_pair", "account_suspicion",
                ["user_a_id", "user_b_id"], unique=True)
# Ensure ordering of pair (user_a_id < user_b_id) at write time, not at DB level
```

A second table for "linked legitimate":

```python
op.create_table(
    "account_link",
    sa.Column("id", UUID, primary_key=True, default=uuid4),
    sa.Column("user_a_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"),
              nullable=False),
    sa.Column("user_b_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"),
              nullable=False),
    sa.Column("linked_by_user_id", UUID, sa.ForeignKey("users.id"),
              nullable=False),  # admin who marked
    sa.Column("reason", sa.Text, nullable=True),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
)
op.create_index("uq_account_link_pair", "account_link",
                ["user_a_id", "user_b_id"], unique=True)
```

Always store with `user_a_id < user_b_id` so each pair appears once.

Optionally extend `User` with `last_register_ip` (nullable varchar) and `last_register_user_agent_hash` (nullable varchar(64)) for the same-device signal. Or — read from AuditLog, accepting that older rows may not have device data. Recommend column on User: cheap, fast.

### Step 2 — signal collectors (Celery tasks, scheduled)

`backend/app/workers/tasks/suspicions.py`:

Five signals, each as its own task; Celery beat runs them daily.

#### 5.1 — Cross-account phone collision

```python
@celery_app.task
def detect_phone_collision():
    # For each phone in TelegramListing/OLXListing/Listing.phone,
    # find the user(s) it belongs to via user_phones.
    # Flag if listings on the same phone resolve to MORE THAN ONE user.
    # Exclude pairs already in account_link.
```

**Critical:** the lookup uses `user_phones` (introduced by C4). Two listings whose contact_phone belongs to the *same* user via multi-phone aggregation do NOT fire this signal.

#### 5.2 — Shared object signature

```python
@celery_app.task
def detect_shared_object_signature():
    # Group by signature_hash; if two converted_listing_id values
    # belong to listings owned by different sellers, flag.
```

`signature_hash` already lives on `TelegramListing` / `OLXListing`. After conversion, `Listing.signature_hash` (if added) or join through the source table.

#### 5.3 — Same-device registration

```python
@celery_app.task
def detect_same_device_registration():
    # Query users where last_register_ip matches AND last_register_at is within
    # 1 hour. Or read AuditLog rows action='register' grouped by ip+UA.
```

Tradeoff: column-on-User is faster; AuditLog is generic but slower. Recommend column.

#### 5.4 — Similar names

```python
@celery_app.task
def detect_similar_names():
    # For each pair of users registered within a 7-day window,
    # compute Levenshtein on first_name + last_name.
    # Threshold: edit-distance ≤ 2 OR same-prefix ≥ 4 chars + matching last names.
```

`Levenshtein` library is small (`pip install python-Levenshtein`), or use a SQL-only approach with `levenshtein()` function (Postgres has `fuzzystrmatch` extension).

#### 5.5 — Suspicious phone-verify patterns

Reads a new `phone_verify_attempt` log table populated by C4's verify endpoint. Flag when one phone has been verify-requested by ≥ 3 different `user_id` values within 24 hours.

```python
op.create_table(
    "phone_verify_attempt",
    sa.Column("id", UUID, primary_key=True, default=uuid4),
    sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"),
              nullable=False, index=True),
    sa.Column("phone", sa.String(20), nullable=False, index=True),
    sa.Column("succeeded", sa.Boolean, nullable=False, server_default="false"),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), index=True),
)
```

Populated by C4. C5 reads. **Coupled migration** between C4 and C5 — recommend including this table in C4's PR1 schema as a forward-compat hook.

### Step 3 — admin queue API

`backend/app/api/v1/admin_suspicions.py` (mirror A8's pattern):

- `GET /admin/suspicions` — list, filter by status, sort by last_detected_at.
- `GET /admin/suspicions/{id}` — full evidence + linked-listings + audit trail.
- `PATCH /admin/suspicions/{id}` — `{ "status": "ignored" | "linked_legitimate", "notes": "..." }`. On `linked_legitimate`, also insert into `account_link`.
- `POST /admin/suspicions/{id}/block` — soft-block one of the accounts (sets `User.deleted_at` + AuditLog row). **Reversible.**

### Step 4 — admin queue UI

`frontend/src/modules/admin/pages/suspicions/` (mirror `sources/` from A8). Table with: pair, signals (list of badges), first/last detected, status, action buttons.

Click a row → drawer with full evidence, listings owned by each side, action buttons.

### Step 5 — false-positive suppression

Before any signal task writes to `account_suspicion`, check:
1. Is the pair in `account_link` with `linked_legitimate`? Skip.
2. Is the pair in `account_suspicion` with `status='ignored'`? Skip.
3. Same user via C4 phone-aggregation? Skip.

This is the single most important correctness rule — false positives during MVP would erode admin's confidence in the queue.

### Step 6 — soft user-side prompt (optional, low priority)

When a `phone_collision` signal fires, *one* of the two accounts (the older one, presumably the legitimate primary) gets a non-blocking in-app prompt: "Похоже, у вас есть другой аккаунт с пересекающимися объявлениями. Хотите объединить аккаунты?" with link to a support flow.

This is a soft mitigation — no alarm, no shame. Implement only if admin queue volume is unmanageable; otherwise skip for MVP.

### Step 7 — C4 coordination

C5 cannot land before:
- C4's `user_phones` table exists (so phone-collision can resolve through it).
- C4's `phone_verify_attempt` table exists (so verify-pattern signal works).

Phase the deploy: C4 ships first, C5 ships in the next release.

## Behaviour & invariants

- **No automatic blocks.** Every state change is human-driven via admin endpoints.
- **No user-visible alerts on suspicion trigger.** (Soft prompt in Step 6 is opt-in.)
- **Signals are advisory.** A pair with one weak signal isn't escalated; the admin queue groups all signals per pair.
- **Pair ordering is deterministic** (`user_a_id < user_b_id`) so the unique constraint catches duplicates.
- **`account_link` is the override.** Once admin marks a pair as legitimate, no future signal re-flags it.
- **Audit every state change.** Each PATCH/POST writes to `AuditLog`.
- **Signal tasks are idempotent.** Running twice produces the same `account_suspicion` row (deduplicated by pair).
- **C4-aware.** Phone-collision signal NEVER fires when both phones belong to the same user via `user_phones`.

## Architecture notes

- One `account_suspicion` row per pair, regardless of how many signals fire. The `signal_types` array accumulates.
- `evidence` JSONB stores per-signal context (phone numbers, listing IDs, IP addresses, name-edit-distance score).
- Soft block via `User.deleted_at` is reversible (clear the timestamp).
- The signal tasks are simple SQL queries — no ML, no fingerprinting beyond IP+UA strings.

## Upstream dependencies

- **C4 schema** (`user_phones`, `phone_verify_attempt`) — **MUST land first**. Without `user_phones` the phone-collision signal mis-fires on multi-phone aggregations.
- **A7 signature_hash** — done; reused.
- **AuditLog** — done; reused.
- **A8 admin pattern** — done; mirrored.

## Downstream dependencies

- **None direct.** C5 sits at the end of Block C; no other task depends on it.

## Migration / schema implications

- Two new tables: `account_suspicion`, `account_link`. Optionally `phone_verify_attempt` (folded into C4).
- Optional `User.last_register_ip` + `User.last_register_user_agent_hash` columns.
- Backfill: scan existing AuditLog rows for `action='register'` to populate the User columns; or accept that pre-C5 users have null device fingerprints.

## API implications

- New admin endpoint set under `/admin/suspicions/*`.
- No change to user-facing APIs (apart from the optional Step 6 prompt).

## Crawler / bot implications

- **None.** Detection runs in worker process; no bot or crawler change.

## AI / F-block implications

- **None.**

## SEO implications

- **None.**

## Localization implications

- Admin UI strings (~15 keys × 3 locales). New `admin.suspicions.*` namespace.
- Review-notes / reasons are free-text and stored as-is; no localisation needed.

## Infra / deploy implications

- **Celery beat schedule additions** for the five signal tasks. Run daily off-peak (3-4 am Tashkent).
- **fuzzystrmatch Postgres extension** required for similar-names signal. Confirm DB has it; if not, install.
- **No external API keys.** No rate-limited services.

## Edge cases

- **Spouses/family with shared contact phone** — admins mark the pair as `linked_legitimate`. C5 respects from then on. C4's "merge accounts via support" flow is the recommended user resolution.
- **Re-registration after losing access to old account** — same phone, different user, looks like a phone-collision. Admin sees it, can either merge (operational) or mark linked.
- **Massive abuse pattern** (50 registrations in 1 hour, all similar names) — daily cron is too slow. Out of MVP scope; document as Phase-2 risk.
- **False positive on common names** — "Алишер Каримов" in Uzbekistan is like "John Smith" elsewhere. Edit-distance threshold needs to consider name frequency. MVP: simple threshold + admin manual review.
- **Removed phone re-registered to another account.** If user A had phone P1, removed it, user B now adds P1 — phone-collision signal could mis-fire on historical Listing rows. Mitigate: signal compares `current` phone ownership only.
- **C4 backfill creates `user_phones` rows for legacy users.** Phone-collision signal only fires on differences AFTER C4 backfill — historical data is consistent.
- **One user, two phone-verify failures, then success.** Not a suspicion. The signal counts attempts where the same phone was tried by *different users*.

## Operational risks

- **False positive rate at MVP scale.** Few users → most signals are real or actionable manually. Once user base grows, the queue will balloon. Plan for review SLA.
- **Admin emotional fatigue.** Reviewing pairs that turn out to be wedge cases is tiring. Soft Step 6 prompt may help.
- **Privacy.** Storing `last_register_ip` is GDPR-adjacent. For Uzbekistan MVP it's fine; document the data category.
- **Performance of signal tasks** — daily cron on a few thousand users is trivial. At scale, push to per-event detection or sampling.
- **Locality of signal evaluation** — running cross-pair queries on millions of users is O(n²) naive; ensure DB-side filtering (recently-registered, or signal-relevant) before pair generation.

## Rollout strategy

1. Schema migration (PR1). Tables empty; safe.
2. Signal tasks (PR2). Ship as Celery beat-disabled tasks; manual run for QA.
3. Admin UI (PR3). Display only; actions disabled.
4. Enable signals in production, run for one week, manually triage.
5. Enable admin actions (PATCH / block).
6. Monitor false-positive rate weekly.

**Rollback:** disable beat schedule; tables remain. No user-visible effect.

## Acceptance criteria

- All five signal tasks run; produce `account_suspicion` rows when conditions met.
- Phone-collision task does NOT flag when both phones are aggregated under one user via C4.
- Admin can list, view, and act on suspicions via `/admin/suspicions`.
- "Linked legitimate" suppresses future signals for the pair.
- No automatic blocks anywhere in the codebase (`grep -nE "User\.deleted_at\s*=" backend/app/workers` returns no auto-block calls).
- AuditLog row written for every status change on `account_suspicion`.
- No user-side notification fires on suspicion creation.
- Admin queue UI mirrors A8 sources page conventions.

## Recommended PR split

- **PR1 (BE)** — schema (`account_suspicion`, `account_link`, `User` device columns, optional `phone_verify_attempt` if not in C4) + tests.
- **PR2 (BE)** — five signal tasks + Celery beat + tests + AuditLog hooks.
- **PR3 (BE)** — `admin_suspicions.py` endpoints + tests.
- **PR4 (FE)** — admin queue page + drawer + actions + i18n.
- **PR5 (FE, optional)** — soft "merge accounts?" prompt for the higher-risk side of a phone-collision pair.

## Estimated complexity

- Schema + models: ~0.5 day.
- Five signal tasks: ~3 days (each has unique SQL + tests).
- Admin endpoints: ~1 day.
- Admin UI: ~1.5 days.
- Soft prompt: ~0.5 day (optional).

Total **~6 dev-days**, BE-heavy. Expect another ~1 day for tuning false-positive thresholds in production.

## Open questions

1. **Does admin have to act on every signal?** Or can `status='open'` rows accumulate? Recommendation: accumulate; review weekly. Confirm.
2. **Where does device-fingerprint data come from?** AuditLog (existing) or new `User.last_register_ip` columns? Recommendation: column on User for speed; AuditLog as historical fallback.
3. **Levenshtein threshold for similar-names** — edit-distance 2 catches typos and obvious variants but also collides on common names. Recommendation: combine with same-suffix(last 4 chars) for noise reduction.
4. **Soft prompt enablement** — ship with signal-detection + admin queue (no user prompt) for the first month? Recommend yes.
5. **Phone-verify-attempt log table** — owned by C4 or C5? Owned by C5 (the only consumer is C5's signal). C4 writes to it; C5 reads. **Recommend folding the migration into C4's PR1 to avoid migration ordering pain.**
6. **Cross-source vs cross-account signature** — should signature-collision signal fire when same listing appears on TelegramListing AND OLXListing for *one* seller? No (that's expected; A7 dedups). Only flag when the converted Listings sit on different sellers.

## References

- `backend/app/db/models.py:1316-1345` — `AuditLog` (audit hooks reuse).
- `backend/app/db/models.py:1433-1437` — `signature_hash` field on source tables.
- `backend/app/services/crawler_service.py:108` — `generate_signature` (signal source).
- `backend/app/api/v1/admin.py:482-565, 273-326` — admin moderation queue patterns.
- `backend/app/api/v1/admin_sources.py` — A8's queue pattern (best mirror for C5's UI/API).
- [C4](./C4-multi-phone-connection.md) — provides `user_phones`, `phone_verify_attempt` (folded into C4 PR1 per Step 7).
- [A1](../../block-a/medium/A1-claim-reject-v2.md), [A7](../../block-a/hard/A7-parser-f1-trigger.md), [A8](../../block-a/medium/A8-channels-management.md).
