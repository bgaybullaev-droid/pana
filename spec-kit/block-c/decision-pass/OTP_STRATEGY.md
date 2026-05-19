# OTP Strategy — Decision Pass

This document closes every OTP-related decision raised in [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md). Each decision is grounded in observed code and tied to specific decision IDs from [`DECISION_MATRIX.md`](DECISION_MATRIX.md).

## §0 Scope and constraints

The truth-layer audit established four facts that bound every decision below:

1. **Telegram bot is the only operational OTP delivery channel** (`auth.py:879`).
2. **No SMS infrastructure exists** anywhere in the repo. Eskiz is mentioned in `claims.py:157` as a TODO; that is not "partial integration", it's literally one comment.
3. **`User.phone` is UNIQUE-indexed** since the initial schema migration. The `prf_canonicalize_phone` migration (Block A) cleaned up duplicates so the constraint stays valid.
4. **`CacheKeys.otp()` is a live latent bug** — referenced by `claims.py:150,208,235`, but the staticmethod is not defined in `redis.py:39-83`. The fast path (auto-verify on phone match) hides it; the OTP fallback path will `AttributeError`.

These four facts force the seven decisions below.

---

## §1 Production OTP flows — full map

There are exactly two OTP flows live in production and two more that exist only as data fields:

| Flow | Endpoint | Trigger | Storage | Delivery | Status |
|---|---|---|---|---|---|
| Seller-login OTP | `POST /auth/seller-otp` (`auth.py:766`) → `POST /auth/verify-seller-otp` (`auth.py:909`) | Direct phone-login | Redis `seller_otp:{last9}` (TTL 600s) | Telegram bot DM | ✅ live |
| Listing-claim OTP (fallback) | `POST /claims/` → `POST /claims/{id}/verify` (`claims.py:35-244`) | Phone of seller ≠ phone of listing | Redis `otp:{listing.phone}` (TTL 600s, **broken — key fn missing**) + DB `ListingClaim.verification_otp` | Telegram bot DM (when reachable) | 🔴 broken (AttributeError) |
| Listing-claim phone-match (fast path) | same | Phone of seller == phone of listing | n/a | n/a | ✅ live, no OTP needed |
| Telegram-WebApp auth | `POST /auth/telegram` (`auth.py:291-428`) | TWA `initData` signature | n/a | n/a | ✅ live, **bypasses OTP** |

**Observable conclusion:** the OTP code path that actually runs OTP-with-delivery in production is exactly one — seller-login OTP. The claim OTP fallback is broken; production traffic doesn't exercise it because the phone-match fast path covers ~all real cases.

---

## §2 Decision #1 — C4 OTP delivery channel

🟢 **DECIDED: Telegram-bot only, MVP.**

### Rationale

- **Forced by code:** No SMS provider integration exists. Adding Eskiz means: API key + paid quota + new service module + new env vars + ops monitoring + retry/back-off logic. That is a Phase-2 investment, ~2-3 dev-days minimum, plus recurring ops cost.
- **Forced by user reality:** Every existing seller is already authenticated via Telegram-bot OTP today (`auth.py:766-906`). They demonstrably have a reachable Telegram chat. Adding a *secondary* phone via Telegram — using the same bot they already trust — is operationally identical to adding a primary phone. No new failure mode.
- **Edge case:** A seller wants to verify a phone whose owner does NOT have a Telegram account (e.g., a personal-line landline). Today, that seller cannot register at all because primary auth is Telegram. So the multi-phone case is strictly easier than the existing primary-auth case — it cannot regress operational reach.

### Architecture choice

C4 endpoint: `POST /sellers/me/phones/request-otp`. Body: `{ "phone": "+998XXXXXXXXX" }`. No `delivery_channel` parameter today. **The endpoint signature is forward-compatible** — when SMS lands in Phase 2, the param becomes `delivery_channel: "telegram" | "sms"` (default `telegram`). Today it's a no-op.

### Open implementation note

The OTP delivery service is the obvious place for an adapter Protocol if future-multi-channel is anticipated. **Codebase precedent disagrees**: the search-backend toggle in `config.py:85` (`postgres | meili`) uses if/elif, not abstract Protocol. Recommend matching that style:

```python
# Future skeleton, not for MVP
def send_otp(user, phone, code):
    channel = settings.otp_delivery_channel  # "telegram" today
    if channel == "telegram":
        return _send_via_telegram(user, code)
    elif channel == "sms":
        return _send_via_sms(phone, code)  # Phase 2
    raise ValueError(f"Unknown OTP channel: {channel}")
```

This keeps the Phase-2 integration path open without front-loading the abstraction cost.

---

## §3 Decision #2 — Hotfix `CacheKeys.otp` AttributeError

🟢 **DECIDED: Yes, in scope. Standalone hotfix PR before any C4 code.**

### Evidence

```python
# claims.py:150
await redis.setex(CacheKeys.otp(listing.phone), 600, otp_code)

# claims.py:208
stored_otp = await redis.get(CacheKeys.otp(claim.otp_phone))

# claims.py:235
await redis.delete(CacheKeys.otp(claim.otp_phone))

# redis.py:39-83 — class CacheKeys defines:
#   listing(), listing_views(), user_session(), refresh_token(),
#   exchange_rate(), districts_list(), rate_limit(), seller_otp(...)
# … but NO `otp()` staticmethod.
```

`grep` confirms `CacheKeys.otp` has zero definitions and three callers.

### Fix scope

Two-line addition to `backend/app/db/redis.py`:

```python
@staticmethod
def otp(phone: str) -> str:
    """Key for legacy listing-claim OTP. See seller_otp() for login OTP."""
    return f"otp:{phone}"
```

That alone unbreaks the claim-OTP path. **Out-of-scope (don't fix yet):** the SMS TODO in `claims.py:157` — that comment becomes accurate-as-aspirational once the method exists.

### Why standalone, not folded into C4

- The hotfix is one method addition; C4 is ~7 dev-days of multi-table migration + endpoint + UI work. Coupling them slows down the hotfix and adds review surface to C4.
- The hotfix has zero schema impact and can ship to production within hours of merge.
- C4's add-phone OTP uses a **different key namespace** (decision #5 below), so the bugfix and the new feature don't share Redis state.

### Recommended PR title

`hotfix(claims): add missing CacheKeys.otp() staticmethod`

---

## §4 Decision #3 — Harden the verify→create race

🟢 **DECIDED: Yes, fold into the same hotfix PR.**

### Evidence

`auth.py:957-1006` — `verify_seller_otp` end of flow:

```python
# Look up existing user by phone
user = (await db.execute(
    select(User).where(User.phone == phone)
)).scalar_one_or_none()
if user is None:
    # CREATE new user
    user = User(phone=phone, telegram_id=tg_id, ...)
    db.add(user)
    # ... set role, approval, etc.
    await db.flush()
```

There is **no row-level lock**. Two concurrent verify requests for the same phone (e.g., user clicks "verify" twice while the first request is in flight) can both pass the "is None" check and both attempt INSERT. The second INSERT hits the `users.phone` UNIQUE index and raises `IntegrityError`.

### Fix scope

Either:

- **Option α:** wrap the INSERT in `INSERT … ON CONFLICT (phone) DO NOTHING`-style upsert via SQLAlchemy's `pg_insert` + `on_conflict_do_nothing`, then re-SELECT.
- **Option β:** acquire an advisory lock on `(hash('user_phone:' + phone))` for the duration of the check-and-insert.

Recommend **option α** — matches Block A's idempotency precedent (`source_metric` upsert), avoids advisory-lock complexity. ~10 lines of code.

### Why same PR as #2

- Both bugs are in adjacent OTP code.
- Both are AttributeError / IntegrityError silent failures that we want fixed before C4 layers complexity.
- Same PR keeps the "fix the broken auth seam" theme together for review.

---

## §5 Decision #4 — C4 add-phone verify endpoint contract

🟢 **DECIDED: Auth-required, never-creating, attaches to `current_user`.**

### Required endpoint contract

```
POST /sellers/me/phones/request-otp
  Auth: required (logged-in seller)
  Body: { "phone": "+998XXXXXXXXX" }
  Pre-checks:
    - phone format E.164
    - phone not already attached to ANY user (UNIQUE on user_phones.phone)
    - user has < 3 additional phones already
    - rate-limit: 3 requests per 10 min per (user_id, phone)
  Effect:
    - Generate OTP, store in Redis under `add_phone_otp:{user_id}:{last9}`
    - Send via Telegram bot to `current_user.telegram_id`
  Response: 200 { "expires_in": 600 } | 4xx error codes

POST /sellers/me/phones/verify-otp
  Auth: required (same seller as request)
  Body: { "phone": "+998XXXXXXXXX", "code": "123456" }
  Effect:
    - Verify code, decrement attempts
    - On success: INSERT INTO user_phones (user_id, phone, is_primary=false, verification_method='tg_otp', verified_at=NOW())
    - Run synchronous re-search via seller_crawled_listings_for_user
    - Return matched-listings count
  Response: 200 { "matched_listings_count": N } | 4xx
```

### Forbidden: this endpoint MUST NOT

- Create a User row. (Login OTP is the only path that does that.)
- Bypass authentication.
- Allow attaching a phone that's the auth-primary of another User. (`UNIQUE(user_phones.phone)` enforces this.)
- Run the same Redis key as login OTP (`seller_otp:` namespace is reserved).

### Why the contract is this strict

If an unauthenticated caller could "verify" a phone, they could attach an arbitrary phone to whichever user_id they specify — a takeover vector. By requiring `current_user` and ignoring the body's user_id, the endpoint is structurally incapable of taking over another account.

---

## §6 Decision #5 — Redis key namespace separation

🟢 **DECIDED: Strict per-flow namespaces; never share a key across flows.**

| Flow | Code key (CacheKeys) | Redis pattern | TTL |
|---|---|---|---|
| Login OTP | `seller_otp(phone)` | `seller_otp:{last9}` | 600s |
| Login OTP attempts | `seller_otp_attempts(phone)` | `seller_otp_attempts:{last9}` | 600s |
| Login OTP TG-pin | `seller_otp_tg(phone)` | `seller_otp_tg:{last9}` | 600s |
| Login rate-limit | `rate_limit('seller_otp:' + last9)` | `rate_limit:seller_otp:{last9}` | 600s |
| Claim OTP (after hotfix #2) | `otp(phone)` | `otp:{phone}` | 600s |
| **Add-phone OTP (new — C4)** | `add_phone_otp(user_id, phone)` | `add_phone_otp:{user_id}:{last9}` | 600s |
| Add-phone OTP attempts (new) | `add_phone_otp_attempts(user_id, phone)` | `add_phone_otp_attempts:{user_id}:{last9}` | 600s |
| Add-phone rate-limit (new) | `rate_limit('add_phone:' + user_id + ':' + last9)` | `rate_limit:add_phone:{user_id}:{last9}` | 600s |

### Why the user_id prefix on add-phone

Two different users could legitimately attempt to verify the same phone at the same time (one is the rightful owner, one is mistaken / malicious). With `add_phone_otp:{last9}` only, the second user's request would clobber the first's code. With `add_phone_otp:{user_id}:{last9}`, the codes are isolated. Each user has their own attempt counter.

### Why login OTP doesn't need user_id prefix

Login is anonymous (the user IS NOT auth'd yet); the phone IS the identity. Two concurrent login attempts for the same phone are pathological — a race condition is acceptable to lose (one of them retries).

### Helper additions to `CacheKeys`

```python
# In backend/app/db/redis.py — add to class CacheKeys:
@staticmethod
def add_phone_otp(user_id: str, phone: str) -> str:
    return f"add_phone_otp:{user_id}:{_last9(phone)}"

@staticmethod
def add_phone_otp_attempts(user_id: str, phone: str) -> str:
    return f"add_phone_otp_attempts:{user_id}:{_last9(phone)}"

@staticmethod
def add_phone_rate_limit(user_id: str, phone: str) -> str:
    return f"rate_limit:add_phone:{user_id}:{_last9(phone)}"
```

(`_last9` is a small helper that strips non-digits and returns the last 9 chars; matches the existing pattern in `auth.py`.)

---

## §7 Anti-spam protections

The login OTP already implements:

- Max 3 attempts per (phone) per 600s — `auth.py:931`.
- Max 3 OTP requests per (phone) per 600s — `auth.py:787`.
- 6-digit code, 600s TTL.

Add-phone OTP MUST mirror these limits **per (user_id, phone)** — not per phone alone. If we limit per phone, an attacker knowing a victim's phone could exhaust the victim's OTP request rate from their own account.

- Max 3 attempts per (user_id, phone) per 600s.
- Max 3 OTP requests per (user_id, phone) per 600s.
- 6-digit code, 600s TTL.

C5's "suspicious phone-verify patterns" signal reads from a separate `phone_verify_attempt` log table (designed in [`../hard/C5-multi-account-detection.md`](../hard/C5-multi-account-detection.md)) populated by the verify endpoint — that's the cross-user pattern detector, not a Redis rate-limit.

---

## §8 Architectural questions answered

The phase brief asked seven specific questions. Each is answered below with code-grounded reasoning.

### Q1: Can multi-phone identity be safely layered onto the current auth architecture?

**YES.** Three reasons:

1. **`User.phone` UNIQUE constraint is preserved.** The primary phone stays in `User.phone` exactly as today. Auth flows that key off `User.phone` (login OTP, claim phone-match) continue to work without modification.
2. **Add-phone is a parallel surface, not a replacement.** `user_phones` is a new join table. No existing auth path needs to change.
3. **Phone-suffix matching for claim/A4** can be expanded from single-column to set-membership (`func.right(UserPhone.phone, 9).in_(...)`) without breaking the existing query.

### Q2: What exact schema changes are minimally invasive?

**One new table:** `user_phones` with columns `id`, `user_id`, `phone`, `is_primary`, `verification_method`, `verified_at`, `created_at`, `updated_at`. Two indexes:
- `UNIQUE(phone)` — globally unique; one phone, one owner.
- `UNIQUE(user_id) WHERE is_primary=true` (partial unique) — one primary per user.

**One backfill:** `INSERT INTO user_phones (user_id, phone, is_primary, …) SELECT id, phone, true, … FROM users WHERE phone IS NOT NULL`. Idempotent (use `ON CONFLICT DO NOTHING`).

**No changes to `User`, `Seller`, `Listing` schemas.** `User.phone` remains the auth identifier; `Seller.phone` mirrors it (deprecated but kept); `Listing.phone` is the contact phone for the listing (unchanged semantic).

**Optional schema change (Phase 2, not C4):** drop `Seller.phone` after switching all readers to `User.phone`. Out of decision-pass scope.

### Q3: Which flows break if `User.phone` stops being globally unique?

Six known consumers depend on `User.phone` UNIQUE:

1. **Login OTP user-creation** at `auth.py:957-1006`. Without UNIQUE, two users could exist with the same phone; verify would non-deterministically pick one.
2. **Claim phone-match** at `seller_crawled_listings.py:31`. Uses `func.right(User.phone, 9)` to find "the" seller for a phone. Without UNIQUE, returns multiple users.
3. **A4 fanout** at `crawled_match.py:137`. Same query pattern; same multi-hit risk.
4. **`prf_canonicalize_phone` migration** explicitly relies on UNIQUE staying valid: "the row with the most recent activity wins; the others lose their phone (set to NULL) so the unique index stays valid going forward".
5. **Public seller profile lookups** by phone (if any — verify before C4 lands).
6. **Any future "find user by phone" admin tool.**

**Decision: `User.phone` UNIQUE constraint is preserved as part of Block C.** C4 does not relax it.

### Q4: What assumptions exist inside JWT/session generation?

`auth.py:1035` issues JWT after verify. The token claims include `user_id` and (per Block A's "phone-gated WebApp" commits) implicit phone-binding via the `User` row.

**Assumption:** the user has exactly one canonical phone (`User.phone`). C4 does not change this. The token's identity is the `User`, not the phone. Adding additional phones does NOT issue new tokens and does NOT change existing claims.

**Implication for C4:** no changes to JWT logic. The add-phone endpoints are auth-protected; the auth dep already gives them `current_user`.

### Q5: What assumptions exist inside seller claims?

Two flows in `claims.py`:

1. **Phone-match auto-verify** (fast path): compares `seller.phone == listing.phone`. Block A's claim-flow uses `Seller.phone` (or sometimes `User.phone`; verify) for this.
2. **OTP fallback** (slow path): the broken path; sends a code to `listing.phone` and asks the seller to enter it.

**Assumption today:** "the seller has one phone, and that phone is what they receive OTPs on."

**Implication for C4:** the phone-match fast path needs to expand from `seller.phone == listing.phone` to `listing.phone IN (user_phones for current seller)`. This is a one-query change matching the broader parser/A4 query expansion. Slow-path OTP is still single-phone — the OTP goes to the listing's phone (which is already supposed to be the seller's), not to all of the seller's phones. Semantic: "prove you control this listing's phone".

### Q6: Which flows require a "primary phone" invariant?

Three:

1. **Login OTP / direct phone auth** — primary is the auth identifier.
2. **Bot DM delivery** — `current_user.telegram_id` is set when the user verified via Telegram-WebApp or the primary-phone OTP. Additional phones may not have an associated Telegram chat.
3. **Default contact phone on create-listing** — defaults to primary unless seller explicitly picks an additional phone.

**Implication:** `user_phones.is_primary` partial-unique constraint is non-negotiable. Exactly one primary per user, always.

### Q7: Can Telegram-only OTP support secondary-phone verification safely?

**YES, with caveats.**

The OTP code is delivered to `current_user.telegram_id` — i.e., to the user's existing authenticated Telegram chat. The user **claims** the new phone is theirs by being able to receive the code via their existing TG channel. This is a weaker proof than receiving an SMS on the new phone — it proves "this user added this phone to their account", not "this user owns this phone number".

For MVP, this trade-off is acceptable because:

- The same user could already own multiple phones via the canonicalize-phone migration's relaxed semantics; we're just exposing the capability in UI.
- The C5 detection layer flags suspicious aggregation patterns; the security perimeter is admin-side, not crypto-side.
- The bypass-cost (impersonating a phone you don't own) is high relative to the benefit (extra free listings).

When Eskiz lands (Phase 2), the verification gets stronger: SMS to the new phone proves number-ownership directly. The endpoint contract doesn't change; only the delivery channel does. Forward-compatible.

---

## Implementation gates (OTP-related)

| Gate | Owner | Done before |
|---|---|---|
| Hotfix `CacheKeys.otp` + auth.py race | Backend dev | C4 PR1 |
| `add_phone_otp_*` Redis helpers in `CacheKeys` | Backend dev | C4 PR2 |
| `phone_verify_attempt` log table (forward-compat for C5) | Backend dev | C4 PR1 schema |
| Bot DM template for add-phone OTP (i18n) | Backend + i18n | C4 PR2 |
| Native-speaker review of add-phone OTP message | Operations | Pre-launch |

---

## Cross-spec links

- [`DECISION_MATRIX.md`](DECISION_MATRIX.md) — master matrix.
- [`PHONE_IDENTITY_MODEL.md`](PHONE_IDENTITY_MODEL.md) — multi-phone schema and migration.
- [`../hard/C4-multi-phone-connection.md`](../hard/C4-multi-phone-connection.md) — full C4 spec.
- [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md) §1 — OTP audit.
