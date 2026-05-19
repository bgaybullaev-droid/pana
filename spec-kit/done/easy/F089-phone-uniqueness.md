# 04 — Phone Uniqueness — Global Guarantee (Ф-89)

**Status:** DONE
**Complexity:** EASY — extract one helper from existing /auth/telegram code, apply it at four other login callsites; tests cover four cases.
**Vision-doc refs:** Section 7.6 (defence against multi-accounts)
**Why now:** Phase 1 hardening. The `/auth/telegram` flow handles the common cases (active clash, soft-deleted clash, seller-side clash — all addressed in the recent fix). Other auth entry points have weaker enforcement.

## What's done — exact map

- **DB indexes**: `ix_users_phone` (initial schema migration) and `ix_sellers_phone_unique` (`20260216_02_make_seller_phone_nullable.py`).
- **`/auth/telegram`** (`backend/app/api/v1/auth.py:299-500`): hard-stops on active clash (line 380-386), frees stale `users.phone` (line 390-395), frees `sellers.phone` for stale users (line 399-405). The complete pattern.
- **`/auth/seller-otp` (request)**: clears `telegram_id` from any other user before binding.

## What's missing — exact map

| Endpoint | File:line | Stale-row freeing? |
|---|---|---|
| `/auth/buyer-phone` (`login_buyer_phone`) | `auth.py:1074-1120` | ❌ none — would 500 on `UniqueViolationError` if a soft-deleted user owns the phone. |
| `/auth/olx-phone` (`login_olx_phone`) | `auth.py:622-695` | ❌ none. |
| `/auth/telegram-channel` (`login_telegram_channel`) | `auth.py:698-780` | ❌ none. |
| `/auth/seller-otp/verify` (`verify_seller_otp`) | `auth.py:934-1010` | ⚠️ partial — clears `telegram_id` from other users (line 987-993) but does NOT free `users.phone` or `sellers.phone` from stale rows. The `User` insert at the bottom can therefore hit `UniqueViolationError` on the unique index. |

The `verify_seller_otp` gap is the most surprising — it's adjacent to the working seller-otp request handler and it's the path that *creates* the user record where the violation would trigger.

There is no `reserve_phone_for_user` helper today — every site re-implements (or omits) the freeing logic.

## Goal

Single contract: **at most one active `User` row per (last 9 digits of phone)**, enforced consistently across every auth entry point. Existing soft-deleted rows holding a phone are auto-released.

## Proposed change

Extract the freeing logic from `/auth/telegram` into a helper:

```python
async def reserve_phone_for_user(
    db: AsyncSession,
    *,
    incoming_phone: str,
    target_user_id: UUID | None,
) -> None:
    """Hard-stop on active clash (other than target_user_id), free stale rows.
    Same semantics as /auth/telegram — call from every login flow that may
    set User.phone.
    """
```

Then call it from `login_buyer_phone`, `login_olx_phone`, `login_telegram_channel`, and `verify_seller_otp` before the `db.commit()`.

## Decisions (formerly open questions)

- **Normalisation on write** is the chosen path. Centralise via `app.utils.phone.normalize_phone(...)` (already used by OTP / claim suffix-matching) and persist the normalised form to `User.phone` from every login flow. The unique index on `User.phone` then naturally enforces "one user per phone" without a partial functional index migration. Sellers with leading `+` will get rewritten on their next successful auth.
- **SIM resale** edge case: today's behaviour is "first-come, first-served until soft-deleted" — fine; the freeing logic only runs for soft-deleted rows. No spec change needed.

## Acceptance criteria

- `reserve_phone_for_user` helper added; all four flows call it.
- Unit tests cover: (a) free phone → success; (b) active-other clash → 400; (c) soft-deleted-other clash → frees + success; (d) seller-row clash → frees + success.
- No `UniqueViolationError` reachable from any login endpoint with realistic input.
