# 09 — Bot Menu Button

**Status:** DONE
**Complexity:** EASY — a single set_chat_menu_button call at bot startup; a few lines.
**Vision-doc refs:** §4.2
**Why now:** Phase 1 polish. Half a day of work, removes an entire onboarding step (`/start` → tap the link).

## Goal

When the bot starts, set a Menu Button (Telegram's official "primary action" button visible in any chat with the bot) that opens the Mini App in one tap.

## Implementation outline

`backend/app/bot/main.py` — at startup, after `Dispatcher` and before `start_polling`:

```python
from aiogram.types import MenuButtonWebApp, WebAppInfo

await bot.set_chat_menu_button(
    menu_button=MenuButtonWebApp(
        text="Открыть UcharMarket",  # i18n: localised per user not supported here; use RU
        web_app=WebAppInfo(url=settings.miniapp_url),  # already exists in env: https://ucharmarket.uz/
    ),
)
```

Per-user menu buttons (different label by language) are not supported by the global `set_chat_menu_button` — Telegram only supports a single global button. Use a neutral RU label that's broadly understood; UZ speakers in Tashkent are bilingual by default.

## Behaviour & invariants

- **Idempotent** — `set_chat_menu_button` overwrites; safe to call on every startup.
- **Per-chat overrides** — possible via `chat_id` param; not needed today.
- **Failure** — log and continue; bot keeps polling.

## Acceptance criteria

- After bot restart, every chat with the bot shows a "Открыть UcharMarket" button to the left of the message field.
- Tapping it opens the Mini App without a `/start` round-trip.
