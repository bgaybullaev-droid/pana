# 01 — Authentication & Accounts

**Status:** DONE
**Complexity:** HARD — multiple auth providers (Telegram WebApp, OTP, buyer-phone, admin, OLX, channel), JWT lifecycle with Redis-backed refresh, and multi-table phone uniqueness across active / soft-deleted users + sellers.
**Vision-doc refs:** Ф-89 (phone-one-account, partially enforced)

## Summary

Multi-provider auth backed by JWT (HS256). One `User` table holds every persona (buyer / seller / admin) and is keyed by an optional `telegram_id` and an optional `phone`. Sessions are issued as access + refresh tokens; refresh tokens are stored in Redis and also as httpOnly cookies. The Telegram Mini App is the production happy path; OTP / phone / admin flows exist for dev, web fallback, and back-office.

## Data model

`backend/app/db/models.py` — class `User` (line ~135).

| Column | Notes |
|---|---|
| `id` | UUID PK |
| `telegram_id` | BigInt, unique, nullable. Bound when user authenticates via Telegram. |
| `phone` | VARCHAR, unique (DB index `ix_users_phone`). Set via Telegram contact share, OTP, or buyer phone login. |
| `first_name`, `last_name`, `username`, `avatar_url`, `language` | Profile. |
| `role` | `USER` / `SELLER` / `ADMIN`. |
| `approval_status` | `PENDING` / `APPROVED` / `REJECTED`. |
| `auth_source` | `telegram_webapp` / `seller_otp` / `buyer_phone` / `admin_login` / `olx_phone` / `tg_channel` / `bot`. |
| `onboarding_completed`, `last_login_at`, `deleted_at`, `deletion_reason` | Lifecycle. |

`Seller` (`backend/app/db/models.py:234`) is a 1:1 satellite for sellers. Has its own `phone` column with **its own** unique index `ix_sellers_phone_unique`.

## API surface

All endpoints under `/api/v1/auth/*` — `backend/app/api/v1/auth.py`.

| Verb | Path | Purpose |
|---|---|---|
| GET | `/me` | Session check via Authorization header or `access_token` cookie. |
| PATCH | `/me` | Partial profile update. |
| POST | `/telegram` | **Production seller entry**. Validates Mini App `initData`, consumes `contact_share:<tid>` Redis key for the phone, links/creates user. |
| POST | `/seller-otp` | Send OTP via the bot to a phone-registered seller. |
| POST | `/seller-otp/verify` | Verify OTP, issue tokens, create user on first verify. |
| POST | `/buyer-phone` | Buyer login by phone (no SMS — Mini App context). |
| POST | `/admin-login` | Username + password against config. |
| POST | `/olx-phone` | Seller-by-phone if crawled OLX listings exist for that phone. |
| POST | `/telegram-channel` | Seller-by-channel if crawled Telegram listings exist for that channel. |
| POST | `/refresh` | Rotate tokens via cookie or body. |
| POST | `/logout` | Clears auth cookies with attribute-matched delete. |
| POST | `/dev-login` | Non-prod fixed-id dev shortcut. |

## Behaviour & invariants

- **JWT** — `app.core.security.create_access_token` / `create_refresh_token`, HS256. Refresh tokens persisted under `CacheKeys.refresh_token(user_id, jti)` in Redis with TTL = `refresh_token_expire_days * 86400`.
- **Cookies** — `_set_auth_cookies` sets `access_token` + `refresh_token` httpOnly, `secure=true` in prod, `samesite=lax`. Logout uses identical attributes (mobile WebView is strict).
- **Telegram initData verification** — `verify_telegram_init_data(init_data, bot_token)`; rejects on invalid HMAC.
- **Phone uniqueness** — `users.phone` and `sellers.phone` both have unique indexes. The `/telegram` flow:
  - hard-stops if another **active** user owns the incoming phone (clear `contact_share` key, raise);
  - frees `users.phone` on **soft-deleted** rows that hold the same phone;
  - frees `sellers.phone` on any seller row holding it (recent fix — was the source of the duplicate-key 500 in production).
- **Soft-delete + telegram_id collisions** — when creating a new user with a `telegram_id` that already exists on a soft-deleted row, we null out the old row's `telegram_id` first to avoid a unique-violation.
- **Account linking** — `app.services.account_linking.get_account_linking_service()` finds a user by any of (telegram_id, phone, username). Used to merge legacy `USER` records into `SELLER`s on first Telegram seller login.
- **OTP delivery** — done in-process by the bot (`get_bot_instance()` singleton), not via a separate worker.
- **`PhoneRequiredException`** — distinct error so the Mini App can drive `Telegram.WebApp.requestContact()` instead of reporting auth failure.

## References

- `backend/app/api/v1/auth.py` — entire router.
- `backend/app/core/security.py` — token creation / verification.
- `backend/app/db/redis.py` — `CacheKeys.refresh_token`, `seller_otp`, `seller_otp_attempts`.
- `backend/app/services/account_linking.py` — identity resolution.
- `frontend/src/shared/state/auth/model/effects/index.ts` — `authenticateWithTelegram`, `loginWithBuyerPhoneFx`, `verifySellerOTPFx`.
- `frontend/src/app/providers/TelegramProvider.tsx` — Mini App detection (treats stub as "not in Telegram" when `initData` empty AND `platform=unknown`).

## Known gaps

- **Ф-89 strict uniqueness** — enforced at DB level for `users.phone`, but no centralised "one phone = one user" guarantee that survives across crawler-imported buyers (those don't use this flow). See `../../partial/easy/F089-phone-uniqueness.md`.
