# Phone Identity Model — Decision Pass

This document closes every C4 / C5 phone-identity decision raised in [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md) and extends [`../hard/C4-multi-phone-connection.md`](../hard/C4-multi-phone-connection.md). Every decision is anchored to existing schema constraints.

## §0 Constraints from production

The truth-layer audit established:

- **`User.phone` is UNIQUE-indexed** since the initial schema migration (`20260115_011036dfb572_initial_schema.py:58`).
- **`Seller.phone` has a partial unique index** (`20260216_02_make_seller_phone_nullable.py:29` — `ix_sellers_phone_unique` WHERE phone IS NOT NULL).
- **`prf_canonicalize_phone` migration relies on these constraints staying valid** — its own docstring says: "the row with the most recent activity wins; the others lose their phone (set to NULL) so the unique index stays valid going forward".
- **Six phone columns total** across the schema (User, Seller, Listing, ListingClaim.otp_phone, TelegramListing.contact_phone, OLXListing.contact_phone). All `String(20)`, all nullable.
- **No `Listing.contact_phone` column distinct from `Listing.phone`** today.
- **OTP delivery is Telegram-bot only.**

These bind every decision below.

---

## §1 Decision #21 — `User.phone` future

🟢 **DECIDED: Keep. Stays the auth identifier and the "primary phone" anchor.**

### Rationale

`User.phone` is the **single, UNIQUE-indexed phone column** that authentication, claim phone-match, and A4 fanout all key off:

- `auth.py:957-1006` — verify-OTP looks up User by phone.
- `seller_crawled_listings.py:31` — claim search uses `func.right(contact_phone, 9) == User.phone[-9:]`.
- `crawled_match.py:137` — A4 fanout looks up users via the same suffix match.

**Removing or renaming `User.phone` would touch 6+ critical paths.** Adding `user_phones` as an additive layer leaves them all working unchanged.

### Contract

- `User.phone` remains the **primary phone**. Always equal to the one row in `user_phones` where `is_primary=true`.
- Maintenance: when the seller adds an additional phone, `User.phone` doesn't change.
- Maintenance: changing the primary phone (only via admin support, not user UI) updates **both** `User.phone` and the corresponding `user_phones` row's `is_primary` flag. Both writes happen in one DB transaction.

### Forbidden

- Treating `User.phone` and `user_phones.phone WHERE is_primary=true` as independent. They MUST stay in sync.
- Making `User.phone` nullable. It already is — but a User without `User.phone` cannot register. If a Seller loses their primary phone (telco issue), they go through ops support to swap it.

---

## §2 Decision #22 — `Seller.phone` future

🟡 **RECOMMENDED: Keep in C4; deprecate in Phase 2.**

### Current usage

`Seller.phone` is read at `sellers.py:131-149, 177, 218, 458` (returned in seller-profile responses) but **its origin** is unclear from the audit. Likely a duplicate of `User.phone` for historical reasons (Block A's seller-OTP migration).

### Why keep in C4

- Removing it would touch all the public-profile endpoints. C4's scope is multi-phone management, not Seller-model cleanup.
- Other code paths might read it directly (search returned ~5 read sites; no obvious mutation site). Audit before drop.

### Why deprecate in Phase 2

- It's redundant — every read can be replaced with `User.phone` (since Seller is 1:1 to User).
- Two sources of truth for "the seller's phone" invite drift if anyone introduces a write.

### Contract for C4

- C4 **does not modify `Seller.phone` reads or writes.**
- C4 docstrings reference "primary phone via User" instead of "Seller.phone".
- Phase-2 cleanup migration: `ALTER TABLE sellers DROP COLUMN phone;` + replace all reads with `seller.user.phone`.

---

## §3 Decision #23 — `Listing.phone` rename

🟡 **RECOMMENDED: Defer the rename. Keep `Listing.phone`; document the new semantic.**

### Current semantic

`Listing.phone` is the contact phone shown on the listing — the number a buyer sees when they tap "позвонить". Today it's typically equal to the seller's primary phone but not constrained to be.

### After C4

- Listing's contact phone may be ANY of the seller's verified phones (one of `user_phones.phone` rows).
- Constraint: at create / update time, the value must be in `user_phones WHERE user_id = seller.user_id`.

### Why defer the rename

- Renaming `Listing.phone` → `Listing.contact_phone` requires updating ~15 read sites (frontend types, schemas, API responses, admin pages).
- The semantic change is small: it's still "the phone for this listing"; it can now be different from the seller's primary.
- Risk > reward for the migration churn.

### What to document instead

In `models.py`, update the column docstring:

```python
# Listing.phone — contact phone shown to buyers for this listing.
# Per C4 (multi-phone realtor support), this MUST be one of the seller's
# verified phones in user_phones; service layer enforces this at write time.
# Defaults to user.phone (primary) when unspecified.
phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
```

That's the entire change for now. Future rename remains a Phase-2 cleanup if it becomes necessary.

---

## §4 Decision #24 — Per-phone listing limit

🟢 **DECIDED: NO. Limit is per-account.**

### Rationale

Spec V2.0 is explicit. The free-2-listings rule applies to the seller's account. A seller with 3 verified phones doesn't get 6 free listings — they get 2.

This is also the architecturally simpler answer: the live-query helper in [`GRANDFATHERING_POLICY.md`](GRANDFATHERING_POLICY.md) §1 doesn't filter by phone; it filters by `seller_id`. All listings under any of the seller's phones aggregate under one seller_id.

### Implication for C5 detection

The motivation for multi-account abuse is "5 phones × 2 free = 10 listings". C4 closes that incentive: legitimate sellers attach all their phones to ONE account, where the limit is still 2. C5 detects when phones are spread across multiple accounts (the bypass pattern).

---

## §5 Decision #25 — Phone-removal flow

🟢 **DECIDED: Hard-delete the `user_phones` row, but only AFTER listings have been transferred or archived.**

### Rationale

A user_phones row is a verification artifact. Soft-deleting it would create a question: "is this phone verified or not?". Hard-delete is cleaner.

But we cannot delete a phone that's the contact_phone of an active listing — the listing would point to a now-dangling phone. So: deletion is gated on resolving the listings.

### Three-option modal (already in C4 spec)

When the seller hits "remove phone" on a phone with N active listings:

1. **"Перенести на основной"** — bulk-update listings' `contact_phone` to `User.phone`. Then delete the user_phones row.
2. **"Перенести на другой номер"** — show a picker of remaining verified phones. Bulk-update. Then delete.
3. **"Удалить объявления"** — bulk soft-delete the listings (`status=DELETED`, `deleted_at=now()`). Then delete the user_phones row.

### Atomicity

All three options run as a single DB transaction:
- Update listings + delete user_phones → commit; OR
- Soft-delete listings + delete user_phones → commit.

If the listing-update / soft-delete fails (concurrent write?), the user_phones row stays and the seller retries.

### What about pending listings (status=PENDING_GENERATION)?

Same rules. If a pending listing's contact_phone is the one being removed, it gets transferred or archived along with the others.

### What about claimed-but-not-yet-conversion-complete state?

Block A's claim flow is atomic; by the time a Listing exists, conversion is complete. So this state is impossible at the C4 deletion moment.

---

## §6 Decision #26 — OTP language

🟢 **DECIDED: Follow `User.language`. Pin `ru` as fallback.**

### Rationale

The Telegram bot already has `User.language` (the Block A i18n integration). The OTP message is bot-side; pulling `User.language` and rendering the localised message is one extra DB read.

### Templates (3 locales)

```
ru:    🔐 Код для подтверждения номера: {{code}}
       Срок действия: 10 минут.

uz:    🔐 Raqamni tasdiqlash kodi: {{code}}
       Amal qilish muddati: 10 daqiqa.

uz-cyrl: 🔐 Рақамни тасдиқлаш коди: {{code}}
         Амал қилиш муддати: 10 дақиқа.
```

i18n keys:
- `bot.add_phone_otp.title` — "🔐 Код для подтверждения номера" / "🔐 Raqamni tasdiqlash kodi" / "🔐 Рақамни тасдиқлаш коди"
- `bot.add_phone_otp.expiry` — TTL line

Native-speaker review before launch.

### What if `User.language` is NULL

Use `'ru'`. Documented behaviour.

---

## §7 Decision #27 — Admin "swap primary phone" UI

🟡 **RECOMMENDED: Yes, ship a small admin endpoint in C4 PR3.**

### Rationale

Spec implied "ops handles primary phone changes via support". Without a dedicated endpoint:
- Admin manually issues SQL: error-prone.
- No audit trail.
- Inconsistent state risk (User.phone vs user_phones.is_primary out of sync).

A small endpoint codifies the operation:

```
POST /admin/users/{user_id}/swap-primary-phone
Auth: admin only
Body: { "new_primary_phone": "+998XXXXXXXXX", "reason": "<required>" }
Effect:
  1. Verify new_primary_phone is in user_phones for this user.
  2. SELECT FOR UPDATE on User row + relevant user_phones rows.
  3. Update user_phones.is_primary: clear from old, set on new.
  4. Update User.phone = new value.
  5. AuditLog entry (entity_type='user', action='primary_phone_swap',
     old_values={phone: <old>}, new_values={phone: <new>, reason: ...}).
  6. Commit.
Response: 200 with new primary.
```

### Why not a user-side endpoint

A user-initiated primary-phone swap is operationally fraught: what if the new primary is unreachable (Telegram blocked, phone lost)? The user could lock themselves out. Ops review (read: friction) is the safety net.

### Cost

~30 lines of code. Same admin-auth dep as A8 endpoints.

---

## §8 Decision #28 — Levenshtein threshold for similar names

🟢 **DECIDED: Edit-distance ≤ 2 AND last-4-character suffix match AND registration within 7-day window. Tunable from settings.**

### Rationale

Single-distance threshold (≤ 2) over names produces noise on common names ("Алишер Каримов" / "Алишер Каримов Каримович" are edit-distance > 2 but obviously similar; "Иван" / "Юра" are edit-distance > 2 but unrelated).

Combining with:
- **Last-4 char suffix match** filters out unrelated short names.
- **7-day registration window** filters out long-term users with similar names.

Together, the false-positive rate is acceptable for an admin-review queue.

### Tunability

```python
# backend/app/core/config.py
similar_name_edit_distance_threshold: int = 2
similar_name_suffix_chars: int = 4
similar_name_registration_window_days: int = 7
```

Admin can tune these post-launch based on observed false-positive rate.

### Implementation depends on `fuzzystrmatch`

This is the Postgres extension dependency flagged in [`INFRA_REQUIREMENTS.md`](INFRA_REQUIREMENTS.md) §2. The `levenshtein()` function is provided by it.

If the extension is unavailable, fallback: implement Levenshtein in Python and run via Celery task on a paginated cursor. Slower but works. Not the recommended path.

---

## §9 Decision #30 — Device fingerprint storage

🟢 **DECIDED: `User.last_register_ip` (varchar 45) + `User.last_register_user_agent_hash` (varchar 64) columns.**

### Rationale

C5's "same-device registration" signal needs to compare devices across users. Reading from `AuditLog` for "register" action rows works but is slow (full table scan or index-on-action-then-filter).

Two columns on `User`:
- O(1) read at signal time.
- O(1) write at register time (one extra column update).
- ~20 bytes per User. At 10,000 users = 200 KB; trivial.

### Why hash the user-agent

Raw user-agent strings are up to 200+ chars and hyper-specific (browser version, OS patch level). Hashing to a stable 64-char SHA-256 (or shorter blake2 hash) gives a comparable identity without storing the full string. Privacy-friendlier.

### Implementation note

Backfill on existing users from AuditLog rows where `action='register'` (Block A's audit log records these). Idempotent script.

### What this rules out

- **Storing raw user-agent strings** beyond the time of registration. If we need them for forensic analysis, AuditLog already has them.
- **IP geolocation** at signal time. Defer to Phase-2 if signals need geo-context.

---

## §10 Phone-touchpoint inventory

Every place phone identity is assumed today, with Block C status:

| Code path | What it assumes | Block C action |
|---|---|---|
| `auth.py:957` (verify-OTP user lookup) | `User.phone` is unique | No change. Continues to work. |
| `auth.py:991` (new user creation) | `User.phone` is the new user's identity | No change. New users get `user_phones` row backfilled at C4 deploy. |
| `seller_crawled_listings.py:31` (claim phone-match) | `func.right(contact_phone, 9) == seller.phone[-9:]` | **CHANGE in C4 PR3**: replace `seller.phone` with set of seller's verified phones via `user_phones`. |
| `crawled_match.py:137` (A4 fanout) | `func.right(User.phone, 9) == listing.phone[-9:]` | **CHANGE in C4 PR3**: same expansion. Look up user where any of their `user_phones` matches. |
| `claims.py:OTP path` (broken) | OTP delivers to `listing.phone` | No change in C4 (it's broken anyway). Hotfix per [`OTP_STRATEGY.md`](OTP_STRATEGY.md) §3. |
| `bot/handlers.py` — bot DM delivery | `current_user.telegram_id` resolved from User row | No change. Add-phone OTP delivers to current user's TG, not to the new phone. |
| `Listing.phone` (write) | Set at create-listing or claim-conversion | **CHANGE in C4 PR3**: validate against `user_phones`. |
| `sellers.py:148, 177, 218, 458` (public profile reads) | Reads `Seller.phone` | No change in C4. Phase-2 cleanup. |
| Frontend listing-create form | Phone field defaults to seller's profile phone | **CHANGE in C4 PR4**: replace text input with select-from-verified-phones. |

---

## §11 Migration strategy

### Phase 1 (C4 PR1): schema additive

```sql
CREATE TABLE user_phones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  phone VARCHAR(20) NOT NULL,
  is_primary BOOLEAN NOT NULL DEFAULT false,
  verification_method VARCHAR(16) NOT NULL,  -- 'tg_otp' | 'sms_otp' | 'legacy'
  verified_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX uq_user_phones_phone ON user_phones (phone);
CREATE UNIQUE INDEX uq_user_phones_primary ON user_phones (user_id) WHERE is_primary = true;
CREATE INDEX idx_user_phones_user ON user_phones (user_id);
```

Backfill in same migration, idempotent:

```sql
INSERT INTO user_phones (user_id, phone, is_primary, verification_method, verified_at)
SELECT id, phone, true, 'legacy', last_login_at
FROM users
WHERE phone IS NOT NULL
ON CONFLICT (phone) DO NOTHING;
```

`ON CONFLICT (phone) DO NOTHING` handles the (impossible-by-canonicalize-migration) edge case where two users somehow share a phone.

### Phase 1 (C4 PR1, same migration): forward-compat C5

```sql
CREATE TABLE phone_verify_attempt (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  phone VARCHAR(20) NOT NULL,
  succeeded BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_phone_verify_attempt_user ON phone_verify_attempt (user_id);
CREATE INDEX idx_phone_verify_attempt_phone_time ON phone_verify_attempt (phone, created_at DESC);
```

C4 PR2 writes to this table on every verify attempt; C5 PR2 reads it for the suspicious-pattern signal.

### Phase 1 (C4 PR3): query expansion

`backend/app/services/seller_crawled_listings.py` — replace single-column suffix match with set-membership query.

`backend/app/workers/tasks/crawled_match.py:137` — same expansion.

No schema change.

### Phase 1 (C4 PR4): frontend phone picker

No backend impact. Existing `POST /listings` accepts `phone` field; service-layer validation accepts any `user_phones.phone`.

### Phase 2 (deferred): cleanup

- Drop `Seller.phone` column.
- Migrate every `seller.phone` read to `seller.user.phone`.
- Optional: rename `Listing.phone` → `Listing.contact_phone`.

---

## §12 Backward compatibility strategy

### Existing claim flow

Block A's claim flow today:
1. Seller goes to /found.
2. Backend queries: `seller_crawled_listings_for_user` matches by `seller.phone`.
3. Seller clicks "это моё" → backend converts the listing.

After C4 PR3:
1. Seller goes to /found.
2. Backend queries: `seller_crawled_listings_for_user` matches by ANY phone in `user_phones`.
3. Result: more listings show in /found (the ones from secondary phones).
4. Seller clicks "это моё" → backend converts. Same code path.

**Backward compatibility:** every existing seller's claim continues to work because their primary phone is in `user_phones` (backfilled). The expansion is purely additive.

### Existing A4 fanout

Block A's A4:
1. New listing imported via parser.
2. `notify_sellers_of_crawled_listing` task: SELECT users where phone matches.
3. Send Telegram push to each.

After C4 PR3:
1. Same as above, but the SELECT now joins user_phones.
2. Same push behaviour per matched user.

**Backward compatibility:** preserved. Users with one phone continue to receive pushes; users with multiple phones now also receive pushes for listings under their secondary phones.

### Saved searches

Saved searches don't reference phones; no impact.

### Buyer-side feed

Buyer-side queries don't reference seller phones; no impact.

### Frontend listing detail

Listing detail shows `listing.phone` (the contact phone). After C4, this could be the seller's secondary phone. UI doesn't care which phone of the seller's it is — just shows it.

---

## §13 Rollback strategy

### C4 PR1 schema rollback

`alembic downgrade -1` drops `user_phones` and `phone_verify_attempt`. **Safe** because:
- No code reads from these tables until PR3.
- Backfill is reversible (old `User.phone` column unchanged).

### C4 PR3 query-expansion rollback

If the set-membership query fails in production, revert the PR. Old single-phone matching behaviour returns. No data lost.

### C4 PR4 frontend rollback

Revert frontend; backend stays. Listing creation still works (phone is just a string in the body); the picker UI is reverted.

### Full block C4 rollback

- Disable `multi_phone_enabled` feature flag → frontend hides the phone management page.
- Schema stays (additive).
- Backfilled rows stay (each User has their primary in `user_phones`; doesn't hurt anything).

---

## §14 Invariants list

| # | Invariant | Enforcement |
|---|---|---|
| P1 | `User.phone` is globally unique | Existing UNIQUE index on `users.phone` |
| P2 | `user_phones.phone` is globally unique | New UNIQUE index on `user_phones.phone` |
| P3 | Exactly one primary phone per user | New PARTIAL UNIQUE INDEX (user_id) WHERE is_primary=true |
| P4 | `User.phone == user_phones.phone WHERE is_primary=true` for the same user_id | App-layer (no DB constraint can express this cross-table identity) |
| P5 | `user_phones.phone` matches E.164 format `+998XXXXXXXXX` | App-layer validation; also enforced by `prf_canonicalize_phone` for backfill rows |
| P6 | Maximum 4 phones per user (1 primary + 3 additional) | App-layer check at "add phone" endpoint |
| P7 | `Listing.phone` MUST be one of the seller's verified phones at write time | App-layer check at POST/PATCH listing |
| P8 | Cannot delete the primary phone via user UI | Endpoint rejects with 400 if phone.is_primary |
| P9 | Cannot delete a phone with active listings without resolution | 3-option modal; deletion gated on resolution |
| P10 | Phone-verify OTP code never delivered to a non-Telegram channel | Telegram-bot only in MVP; Phase-2 if SMS lands |

---

## §15 Edge-case matrix

| Edge case | Expected behaviour | Code site |
|---|---|---|
| Verify OTP for a phone that's already attached to me | 400 `phone_already_yours` | request-otp endpoint, pre-check |
| Verify OTP for a phone that's attached to someone else | 409 `phone_in_use` (don't disclose owner) | request-otp endpoint, pre-check |
| Try to add 4th additional phone (lim 3) | 409 `quota_exceeded`; with link to settings | request-otp endpoint, pre-check |
| OTP arrives but user closes the modal | OTP expires in 10 min; re-request available after 1 min cooldown | Redis TTL + rate-limit |
| User verifies one phone, immediately tries another | Allowed; each (user_id, phone) gets its own OTP namespace | Redis key namespace per §6 in OTP_STRATEGY |
| User verifies a phone that's already in `user_phones` for them | 400 `phone_already_yours` (idempotent: don't re-add row) | verify endpoint, pre-check |
| Telegram blocked the bot mid-flight | OTP sent fails; user sees "не удалось доставить — обратитесь в поддержку" | bot.send_message handles `TelegramForbiddenError` (already in `notifications.py`) |
| User deletes a phone with claim-pending listings (PENDING_GENERATION) | Same 3-option modal; affected pendings count as "active" for resolution purposes | listing transfer / archive |
| User has 3 additional phones; primary phone gets banned by Telegram for spam | User can still log in via WebApp signature; cannot use OTP login. Ops handles. | No code change |
| Race: two devices verify the same phone for two users simultaneously | Second insert fails on `uq_user_phones_phone`; clean 409 to second user | DB constraint |
| C4 backfill on a user with no phone | Skipped by `WHERE phone IS NOT NULL` | Migration |
| C4 backfill on a user whose phone was nulled by canonicalize migration | Skipped (no phone to backfill); user can re-add via OTP later | Migration |
| Admin swaps primary phone | Old primary's `is_primary=false`, new primary's `is_primary=true`, `User.phone` updated, AuditLog row | Admin endpoint per §7 |

---

## §16 High-lock / dangerous migrations

| Migration | Lock duration | Risk | Mitigation |
|---|---|---|---|
| `CREATE TABLE user_phones` | ms-scale (no data) | Negligible | Run any time |
| `INSERT … SELECT … FROM users` (backfill) | seconds (~thousands of users) | Negligible at MVP scale | Single transaction; could batch if scale grows |
| `CREATE TABLE phone_verify_attempt` | ms-scale | Negligible | Same |
| Phase-2 `DROP COLUMN sellers.phone` | brief ACCESS EXCLUSIVE | Lock contention if running during traffic | Off-peak deploy; script confirms zero readers first |
| Phase-2 `RENAME COLUMN listings.phone → contact_phone` | brief ACCESS EXCLUSIVE | Same | Off-peak; coordinate with frontend deploy |

---

## §17 Crawler implications

C4 changes one thing in the parser-side query expansion (PR3). Beyond that:

- Crawler still writes `TelegramListing.contact_phone` and `OLXListing.contact_phone` from scraped data (no change).
- Crawler doesn't know about `user_phones`; it stays user-agnostic. Only the backend's matching layer reads `user_phones`.
- The `crawled_match.notify_sellers_of_crawled_listing` Celery task (Block A) now resolves more sellers per listing (multi-phone aggregation) but doesn't change its dispatch logic.

**No crawler code changes** in C4.

---

## §18 Bot implications

- Bot delivers add-phone OTP via the same `bot.send_message` path used for login OTP. **No new bot handlers needed.**
- Bot's `claim_crawled` callback (Block A's A4) keeps working — it now resolves more listings per phone match, but the user-facing flow is unchanged.
- Bot's `/start` flow doesn't reference phones; no impact.

**Minimal bot code changes** in C4 (just the new i18n template for the add-phone OTP message).

---

## §19 Cross-spec links

- [`DECISION_MATRIX.md`](DECISION_MATRIX.md) — master matrix.
- [`OTP_STRATEGY.md`](OTP_STRATEGY.md) — OTP delivery + Redis namespacing.
- [`../hard/C4-multi-phone-connection.md`](../hard/C4-multi-phone-connection.md) — full C4 spec.
- [`../hard/C5-multi-account-detection.md`](../hard/C5-multi-account-detection.md) — multi-account-detection consumer of `user_phones`.
- [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md) §1, §3 — phone audit.
