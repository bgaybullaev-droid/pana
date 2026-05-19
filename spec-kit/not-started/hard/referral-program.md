# 14 — Referral Program

**Status:** NOT STARTED
**Complexity:** HARD — multi-table attribution + qualification + redemption + monthly windowing + cap + decay + fraud surface.
**Vision-doc refs:** §5.4
**Why now:** Phase 2. Activates with monetisation. Designed to monetise the existing social fabric of the Tashkent realtor community.

## Mechanic (from vision doc)

- Each seller has a unique referral code → deep link `t.me/<bot>?start=ref_<id>`.
- A referee who signs up via that link is **attributed** to the referrer.
- Referrer earns reward when the referee makes their **first paid action** (buys a listing slot or activates a Cabinet subscription).
- Reward = 3 free listing slots in the *following* month.
- Cap: max 10 free reward-slots accumulated per month; unused slots evaporate at month roll-over.

## Proposed data model

Add to `User`:

| Column | Notes |
|---|---|
| `referral_code` | VARCHAR(16), unique, nullable. Auto-generated on first cabinet open (e.g. random 8-char alphanumeric). |
| `referred_by_user_id` | UUID FK to User, nullable. Set during signup deep-link. Immutable after first set. |

`ReferralEvent`:

| Column | Notes |
|---|---|
| `id` | UUID. |
| `referrer_id` | FK to User. |
| `referee_id` | FK to User, unique (each referee can be attributed once). |
| `attributed_at` | When deep-link was consumed. |
| `qualified_at` | Nullable. Set when referee makes first paid action. |
| `qualifying_payment_id` | Nullable FK to a payments table (depends on [`F113-wallet`](F113-wallet.md)). |

`ReferralReward`:

| Column | Notes |
|---|---|
| `id` | UUID. |
| `user_id` | FK to User (the referrer being rewarded). |
| `referral_event_id` | FK. Each event yields exactly one reward row. |
| `granted_at` | Timestamp. |
| `slots_granted` | Int (= 3). |
| `month` | DATE truncated to first-of-month — the month the slots are usable in. |
| `slots_consumed` | Int, default 0. Increments when reward slots are used. |

## Proposed flow

### A. Code generation

Lazily on cabinet first open:

```python
if not user.referral_code:
    user.referral_code = secrets.token_urlsafe(6)[:8].upper()
```

### B. Deep-link attribution

`?start=ref_<code>` is intercepted by the bot's `/start` handler **before** the Mini App loads. The bot stores the attribution in Redis: `referred_by:<from_user_id>` = `<code>` with TTL 7 days.

When the user later authenticates and a `User` row is created (in `/auth/telegram` or `/auth/seller-otp/verify`), the auth code:

```python
referred_by_code = await redis.get(f"referred_by:{telegram_id}")
if referred_by_code and not user.referred_by_user_id:
    referrer = await find_user_by_referral_code(db, referred_by_code)
    if referrer and referrer.id != user.id:
        user.referred_by_user_id = referrer.id
        db.add(ReferralEvent(referrer_id=referrer.id, referee_id=user.id, ...))
        await redis.delete(f"referred_by:{telegram_id}")
```

### C. Qualification

When the referee makes a qualifying payment (Phase 2's payment hook), update the corresponding `ReferralEvent.qualified_at` and create a `ReferralReward` for the referrer in the **next** calendar month, capped at the 10-slot ceiling.

### D. Reward redemption

When the referrer publishes a listing in the reward month, the listing-publish flow checks `ReferralReward.slots_consumed < slots_granted` for the current month and decrements. The seller's bill skips that listing's monthly fee.

## API surface

| Verb | Path | Purpose |
|---|---|---|
| GET | `/seller/referrals` | Returns code + counts: `{code, total_referred, qualified, pending, current_month_reward_slots: {granted, consumed}}`. Drives the Cabinet → Referrals page. |
| GET | `/seller/referrals/share-link` | Returns `t.me/<bot>?start=ref_<code>` ready to copy. |

## Behaviour & invariants

- **Self-referral blocked** — code holder ≠ referee.
- **One attribution per referee, ever** — `unique` constraint on `ReferralEvent.referee_id`.
- **Multi-account fraud** — see §7.6 in the vision doc; the same phone-number guarantee from [`F089-phone-uniqueness`](../../partial/easy/F089-phone-uniqueness.md) is the primary defence. Reward only triggers on **paid action**, so creating fake accounts costs more than the reward.
- **Caps** — max 10 reward-slots in any one month; excess events are recorded but produce 0-slot rewards (still useful for analytics).
- **Decay** — unused reward slots expire at month roll-over. No carry-over.

## Frontend

Cabinet → "Реферальная программа" page:

- Big copy-link button with the share URL.
- Stats: invited / qualified / earned slots.
- Help text explaining the mechanic.

## Acceptance criteria

- Each seller has a unique referral code on first cabinet open.
- Sharing a `?start=ref_<code>` link and signing up via it attributes the new user.
- The qualifying payment grants 3 reward-slots to the referrer for the next month.
- Reward slots are consumed on listing publish (skipping monthly fees).
- Cap and decay enforced.
