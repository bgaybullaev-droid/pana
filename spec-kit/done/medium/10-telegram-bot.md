# 10 — Telegram Bot

**Status:** DONE
**Complexity:** MEDIUM — aiogram dispatcher + handler set + singleton lifecycle bridging FastAPI handlers via Redis.

## Summary

Long-polling aiogram bot in `backend/app/bot/`. Provides three concrete services:

1. **OTP delivery** — sends 6-digit codes for the seller-OTP login flow.
2. **Mini App contact-share cache** — when the Mini App calls `requestContact()`, the user shares the contact through the bot; the bot caches the phone in Redis under `contact_share:<telegram_id>` so the `/auth/telegram` endpoint can consume it.
3. **Notification delivery** — receives `send_telegram_notification` task results from Celery and forwards them to user chats.

It also serves as the deep-link entry point (`?start=link_<phone>`) for binding telegram_id to a phone-only user record.

## Process

`backend/app/bot/main.py`:

- `Bot(token=settings.telegram_bot_token)` + `Dispatcher`.
- `set_bot_instance(bot)` exposes a singleton via `get_bot_instance()` for non-bot contexts (FastAPI handlers calling `bot.send_message`).
- `dp.start_polling(bot)` runs the loop.

Run as a separate container/service from FastAPI (production: `demo-bot` Docker container; local: `python -m app.bot.main`).

## Handlers

`backend/app/bot/handlers.py` — single router carrying command, callback-query, and FSM-state handlers.

| Update | Handler (line) | Effect |
|---|---|---|
| `/start` (no payload) | `cmd_start` (~225) | Welcome + Open Mini App button. |
| `/start link_<phone>` | `cmd_start` deep-link branch | Parses `link_<phone>` and binds the issuing `telegram_id` to a phone-only user record. |
| `/profile` | `cmd_profile` (~420) plus `profile_*` callback handlers | Shows linked phone + role; opens edit / language / back. |
| `/language` | `cmd_language` (~320) + `lang_*` callbacks (~326) | ru / uz toggle (writes to `User.language`). |
| `/help` | `cmd_help` (~383) | Static help text. |
| `/cancel` | `cmd_cancel` (~394) + `cancel` callback (~409) | Resets FSM state. |
| Contact share (any context) | `F.contact` filter (~1507) | Caches phone in Redis under `contact_share:<telegram_id>` with TTL; logs `Cached Mini App shared contact for telegram_id=…` (~1533). One handler covers both Mini-App `requestContact()` and the inline reply-keyboard share button. |
| Seller registration FSM | `SellerRegistration.*` (~695+) | Multi-step register flow when a seller starts onboarding from the bot rather than the Mini App. |

## Keyboards

`backend/app/bot/keyboards.py`:

- `share_contact_kb()` — `request_contact=True` reply keyboard for OTP fallback.
- `open_app_kb(url)` — inline button opening the Mini App.
- `confirm_inline_kb(...)` — generic confirm/cancel inline keyboard used by claim OTP and other prompts.

## Translations

`backend/app/bot/translations/{ru,uz}.json` — flat key→string. Loaded once at startup. The B7 guardian rule checks both files have identical keys before commit.

## Notification delivery

`send_telegram_notification` Celery task (`backend/app/workers/tasks/notifications.py:303`):

```python
await Bot(token=settings.telegram_bot_token).send_message(
    chat_id=user_telegram_id, text=message, parse_mode="HTML"
)
```

Catches `TelegramForbiddenError` (user blocked the bot) and `TelegramBadRequest`, logs and returns; does not retry on those. Other errors retry up to 3× with 60 s backoff.

## Behaviour & invariants

- **Bot username** — driven by `settings.telegram_bot_username` (env: `TELEGRAM_BOT_USERNAME`). The frontend reads it via `/auth/seller-bot-info`. Production: `@TestUcharBot` (token `6109...`); local dev: `@testourbor_bot` (token `6282...`).
- **Singleton lifecycle** — `app.bot.notifications.set_bot_instance` is called in `main.py` before `start_polling`. FastAPI handlers `import` `get_bot_instance()` to reach the same `Bot` for OTPs / claim notifications.
- **Polling, not webhooks** — `TELEGRAM_WEBHOOK_SECRET` env exists but the bot uses long-polling; webhook config is reserved for future ops change.
- **Contact-share key TTL** — short (10 min) so a stale share can't silently link later. The `/auth/telegram` flow `redis.delete`s the key on consumption (one-shot semantics).

## References

- `backend/app/bot/main.py`
- `backend/app/bot/handlers.py`
- `backend/app/bot/keyboards.py`
- `backend/app/bot/notifications.py` — `set_bot_instance` / `get_bot_instance`.
- `backend/app/bot/translations/{ru,uz}.json`
- `backend/app/workers/tasks/notifications.py:303` — `send_telegram_notification`.

## Known gaps

- **Menu Button** — bot doesn't call `set_chat_menu_button` at startup. See `../../not-started/easy/bot-menu-button.md`.
- **Inline Mode** (`@bot query`) — no `inline_query` handler. See `../../not-started/medium/bot-inline-mode.md`.
- **Filter-prefill deep links** (`?start=chilanzar_2rooms`) — only `link_<phone>` is parsed today. See `../../not-started/easy/deep-links-filter-prefill.md`.
- **Channel autoposting** — no admin-rights flow / channel-id tracking yet. See `../../not-started/hard/bot-channel-autopost.md`.
