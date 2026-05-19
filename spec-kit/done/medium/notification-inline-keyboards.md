# 11 — Notification Inline Keyboards

**Status:** DONE
**Complexity:** MEDIUM — callback handlers for fav / contact, keyboard schema in send_telegram_notification, deep-link integration.
**Vision-doc refs:** §4.2
**Why now:** Phase 1 polish. ~1 day. Multiplies the value of every push notification.

## Goal

Telegram notifications about new listings include inline buttons:

- 🔍 **Открыть** — opens the listing detail in the Mini App (deep-link).
- ❤️ **В избранное** — adds to favorites without leaving Telegram.
- 💬 **Связаться** — reveals the seller's contact (counts as a contact event).

## Current state

`send_telegram_notification` (`backend/app/workers/tasks/notifications.py:303`) sends plain text via `bot.send_message(chat_id, text, parse_mode="HTML")`. No `reply_markup`.

## Proposed change

Extend the task signature:

```python
@celery_app.task
def send_telegram_notification(
    user_telegram_id: int,
    message: str,
    parse_mode: str = "HTML",
    inline_buttons: list[dict] | None = None,
) -> dict:
    ...
    reply_markup = _build_keyboard(inline_buttons) if inline_buttons else None
    await bot.send_message(chat_id=..., text=message, parse_mode=..., reply_markup=reply_markup)
```

`_build_keyboard` translates `[{"text": "Открыть", "url": "https://t.me/<bot>?startapp=listing_<uuid>"}, ...]` into an `InlineKeyboardMarkup`.

For the favorite / contact buttons, use **callback_data** rather than URL — handled by a bot callback handler:

```python
@dp.callback_query(F.data.startswith("fav:"))
async def handle_fav_callback(cb: CallbackQuery):
    listing_id = cb.data.split(":")[1]
    user = await user_by_telegram_id(cb.from_user.id)
    await favorite_listing(user.id, listing_id)
    await cb.answer("Добавлено в избранное ❤️")
```

### Producer side

`_match_saved_searches` and `_match_and_notify` build `inline_buttons` per match:

```python
buttons = [
    {"text": "🔍 Открыть", "url": f"https://t.me/{bot_username}?startapp=listing_{listing_id}"},
    {"text": "❤️ В избранное", "callback_data": f"fav:{listing_id}"},
    {"text": "💬 Связаться", "callback_data": f"contact:{listing_id}"},
]
send_telegram_notification.delay(user.telegram_id, text, "HTML", buttons)
```

The "Открыть" deep link uses `?startapp=...` (the Mini App equivalent of `?start=`) and is handled by the deep-link router in [`deep-links-filter-prefill`](../easy/deep-links-filter-prefill.md).

## Behaviour & invariants

- **Authorisation in callbacks** — callback handlers must look up the user by `from_user.id`, never trust client state. Reject if no user.
- **Rate limit** — Telegram allows ~30 cb/sec per bot; not an issue at our scale.
- **Edge case: legacy notifications** — only newly-sent notifications get keyboards; in-app history continues to render plain text.

## Acceptance criteria

- New-listing Telegram notifications arrive with three inline buttons.
- Tapping ❤️ adds to favorites and shows a green toast inside Telegram (`callback_query.answer`).
- Tapping 💬 reveals seller phone (or opens a chat) and increments `contacts_count`.
- Tapping 🔍 opens the listing in the Mini App.
- Saved-search and preferences notifications both get the same set.
