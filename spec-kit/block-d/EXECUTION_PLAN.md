# Block D — Execution Plan

> Order driven by real code dependencies, not by spec section number.
> The principle from Block C: never start implementation until
> every upstream dependency is satisfied. No mid-stream "oh I need
> X" surprises.

---

## Dependency graph

```
D1 (Menu Button + lang picker)
  │
  ├──→ D2 (push inline keyboard — needs user.language to render text)
  │       │
  │       └──→ D3 callback URL ("Подробнее" → listing_<id>)
  │
  ├──→ D3 (deep links — language picker must run before payload applies)
  │       │
  │       ├──→ D4 (channel post "Подробнее" button uses D3 builder)
  │       │
  │       └──→ D5 ("Open all in app" button uses filter_<id>)
  │
  ├──→ D4 (channel posts on user language)
  │
  └──→ D5 (result text on user language)
```

The critical path is **D1 → D3 → everything else**. D2/D4/D5 are
parallelisable after D1 and D3 land.

---

## Suggested PR sequence

### PR-D1 — Menu Button & trilingual language picker (1.5 days)

**Backend**
1. Add `uz_cyrl` to `bot/i18n.py` `SUPPORTED_LANGUAGES`. Create
   `bot/translations/uz_cyrl.yml` with all keys present in `ru.yml`.
2. Add third button to `bot/keyboards.py:get_language_kb()`.
3. Replace `/start` welcome with trilingual block; add
   `lang_uz_cyrl` callback handler (already trivial — just extend the
   `lang_*` dispatcher).
4. Mapping change in `language_code` fallback: `uz → uz_cyrl`.
5. New: `bot/setup.py` calling `bot.set_chat_menu_button(...)` on
   startup. Idempotent.
6. New endpoint: `PATCH /api/v1/me/language` writing to `User.language`.

**Frontend**
1. New "Язык / Til / Тил" picker UI on `/settings`. Calls the new
   PATCH endpoint and writes `localStorage.i18nextLng` + calls
   `i18n.changeLanguage`.
2. On auth success, sync `localStorage.i18nextLng` from
   `User.language` if present.

**Migration**
- None (User.language column already exists).

**Sign-off**
- Manually verify 3-language picker on /start in real bot.
- Verify Menu Button on iOS/Android/Desktop opens TWA in one tap.
- Verify changing language in bot updates TWA on next open, and
  vice-versa.

---

### PR-D3a — Deep-link plumbing (foundation) (2 days)

Do D3 **before** D2/D4 because both need the deep-link builder.

**Backend**
1. Migration: `prl_deep_link_payloads` — `deep_link_payloads`,
   `deep_link_events`, `claim_invites` tables; `users.referred_by_user_id`
   + `users.referral_source` columns.
2. `backend/app/services/deeplink.py` — `build_listing_link`,
   `build_filter_link`, `build_claim_link`.
3. `bot/handlers.py` payload dispatcher — registry pattern; wire
   `listing`/`obj`, `link` (existing migrated), `inv` stub.
4. `claim_invites` lifecycle endpoint + handler for `claim_` /
   `agent_` payloads.
5. `ref_<user_id>` handler — writes `referred_by_user_id` on first-time
   user only.
6. Event-log row on every `/start <payload>`.

**Frontend**
1. Extend `StartParamHandler` to handle `obj_` (alias to `listing_`)
   and `filter_<id>` (calls `GET /deep-links/<id>` and applies).
2. Buyer filter store: hydrate from deep-link payload.

**Migration**
- New tables; no destructive changes.

---

### PR-D2 — Push inline keyboard + behavioral signals (3 days)

**Backend**
1. Migration: `prm_behavioral_signals` — single table for all signal
   sources.
2. `send_telegram_notification` gains an optional `reply_markup`.
3. `_listing_action_kb(listing, lang)` factory.
4. `services/seller_contact.py` — prefilled `?text=` URL builder per
   sender language.
5. New callback handlers `fav_add:` / `fav_remove:` toggling
   message + writing behavioral signal.
6. Saved-search push code path passes the new keyboard.

**Frontend**
- None primary. Validate that the listing-detail page handles
  `start_param=listing_<id>` correctly when landed-on via "Подробнее"
  push button (already wired by D3).

---

### PR-D4 — Bot autoposting (6–8 days, optionally split)

**Backend**
1. Migration: `prn_autopost` — Seller columns +
   `bot_channel_posts` table; `Listing.version` integer.
2. `services/autopost.py` — connect/verify, autopost on ACTIVE,
   update, mark_sold, delete.
3. `services/subscriptions.py:active_subscription_check` (Phase-1:
   open to all sellers).
4. New endpoints under `api/v1/autopost.py`.
5. Listing-status transition hooks (in `services/listings.py` or
   wherever status writes happen — verify).
6. Retry-queue via Celery with backoff.
7. Bot-kicked / channel-deleted detection paths.

**Frontend**
1. New `/seller/autoposting` page (FSD module).
2. Listing-create form: "Опубликовать в моём канале" checkbox.
3. "Pôst stale" badge on listing cards.
4. "Update post" button.
5. 48h cutoff modal with 3 options.

**Optional split**
- PR-D4a: connect/verify + first publish only.
- PR-D4b: update/delete + 48h modal + history view.

---

### PR-D5 — In-bot search + Inline Mode (5–7 days)

**Backend**
1. `services/query_parser.py` + `query_parser_dict.yml`.
2. `services/bot_search.py`.
3. Bot command `/search` + free-text fallback in router.
4. New `bot/inline.py` with `InlineQueryHandler`.
5. Register `inline_router` in `bot/main.py`.
6. Redis rate-limit per user.

**Frontend**
- None.

---

## Total timeline

| PR | Days | Cumulative |
|----|------|-----------|
| D1 | 1.5 | 1.5 |
| D3a | 2 | 3.5 |
| D2 | 3 | 6.5 |
| D4 | 6–8 | 12.5–14.5 |
| D5 | 5–7 | 17.5–21.5 |

**~3 calendar weeks** with serial work; ~2 weeks if D2 / D4 / D5
parallelised after D3a.

---

## What can ship independently

If we need partial wins:

- **D1 alone** is shippable — significant UX win for any session.
- **D1 + D2** ships a coherent "rich notifications" story.
- **D1 + D3a + D5** ships a Telegram-search story without channel
  autoposting.
- **D4** is the longest single PR; defer if Cabinet subscription
  monetisation is not yet enforced.

---

## Cross-cutting must-do BEFORE PR-D2 ships

1. D1's `uz_cyrl` translations must include every new key used by
   D2/D3/D4/D5. Otherwise users land in fallback ru in bot but uz-cyrl
   in TWA — exactly the inconsistency the spec forbids.
2. The deep-link builder from D3 must be used everywhere notifications
   reference listings — don't let D2 hand-build URLs that later need
   rewriting.

---

## Out of scope (explicitly)

- Internal chat in TWA (spec defers — "Phase 1 не делаем")
- Multi-channel per seller (1 channel/account in MVP)
- Real-time autopost-update (manual trigger only in Phase 1)
- Aggregate analytics dashboard for deep-link events (raw table only,
  product can SQL)
- LLM-based query parsing (rule-based in Phase 1)
- Referral payouts (Phase 2)
- Invoice deep-links `inv_` (Phase 2 stub only)
