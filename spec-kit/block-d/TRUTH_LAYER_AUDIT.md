# Block D V2.0 — Truth-Layer Audit

> Status of every Block D dependency in the current codebase as of 2026-05-13.
> EXISTS = production-ready and reusable as-is. PARTIAL = present but needs
> extension/migration. MISSING = no code today.

---

## Audit method

Four parallel agent sweeps covered: (1) bot handlers + i18n, (2) push
notifications + AI generation, (3) deep links + WebApp, (4) search + channels.
Then critical uncertainties were verified directly against the source tree
(`bot/keyboards.py`, `bot/i18n.py`, `db/models.py`, `app/router/Router.tsx`).

All path/line references below are absolute facts from the current `dev`
branch — not derived from memory.

---

## 1. D1 — Menu Button + first-/start language picker

### Already exists

- **Bot framework**: aiogram 3.x — `backend/app/bot/handlers.py` (1698 LOC).
  Production-grade router; CommandStart, FSM, CallbackQuery handlers all
  wired and shipping.
- **`User.language` persistent field**: `backend/app/db/models.py:174`
  `language: Mapped[str] = mapped_column(String(10), default="ru")`.
- **`/language` command**: `handlers.py:320-323` — re-runs the picker on
  demand.
- **Language picker on first `/start`**: `handlers.py:225-312` shows the
  picker for new users; `handlers.py:326-350` writes the choice to
  `User.language`.
- **Telegram `language_code` fallback**: `handlers.py:229,237`; mappings in
  `bot/i18n.py:64-70` (uk/be/kk/tj → ru).
- **WebApp `initData` HMAC verification**: `backend/app/core/security.py:78-146`.
  Extracts `language_code` at line 140 (currently unused downstream — see
  PARTIAL below).
- **Frontend i18n**: three locales present —
  `frontend/src/shared/i18n/locales/{ru,uz,uz-cyrl}/` — selector reads/writes
  `localStorage.i18nextLng` in `frontend/src/shared/i18n/index.ts:20,60`.

### Partial / mismatched

- **Bot supports only 2 languages, frontend supports 3.**
  `backend/app/bot/i18n.py:14` — `SUPPORTED_LANGUAGES = ("ru", "uz")`.
  Frontend has `uz-cyrl` directory with 4 translation namespaces. The bot
  language picker (`bot/keyboards.py:14-20`) only renders two buttons
  (`lang_ru`, `lang_uz`). **The third option "Ўзбекча" (uz-cyrl) does not
  exist on the bot side.** D1 must add it.
- **WebApp `initData.language_code` is parsed but never applied** to a new
  user's `User.language` during silent registration. Fallback only kicks in
  if the user later hits `/start` in the bot.

### Missing

- **No Menu Button configuration** anywhere in the repo — no
  `bot.set_chat_menu_button()` call, no BotFather setup script, no docs.
  This is the primary D1 deliverable.

---

## 2. D2 — Inline Keyboard in push notifications

### Already exists

- **Outbound bot messaging**: `backend/app/bot/notifications.py` —
  `send_approval_notification`, `send_rejection_notification`,
  `send_custom_notification`, `notify_admins_new_registration` (lines 17-157).
  Bot instance via `get_bot_instance()` (lines 171-181).
- **Push pipeline with `reply_markup` precedent**: `backend/app/workers/
  tasks/crawled_match.py:221-268` — `_send_push()` already attaches a 2-button
  `InlineKeyboardMarkup` (`✓ Это моё` / `✗ Не моё`) with callback_data
  `claim_crawled:{id}` / `reject_crawled:{id}`.
- **`callback_query` router**: `backend/app/bot/handlers.py:1541-1635`
  handles `claim_crawled:` and `reject_crawled:` callbacks end-to-end. New
  `favorite_add:` / `contact_seller:` callbacks plug into the same router.
- **AI description per locale**: `Listing.ai_description_ru / _uz / _uz_cyrl`
  — `backend/app/db/models.py:508-510`. F1 worker
  (`backend/app/workers/tasks/ai_generation.py:50,94`) emits all three locales
  in a single OpenAI call. Crawled-match push already renders the
  language-appropriate field.
- **Favorites endpoint, idempotent**: `backend/app/api/v1/favorites.py:244-265`
  `POST /favorites/{listing_id}` — double-tap-safe, returns "Already in
  favorites" without erroring.
- **Mini App deep link helper**: `backend/app/workers/tasks/notifications.py:
  138-141`
  `_listing_deep_link(listing_id) → https://t.me/{bot}?startapp=listing_{id}`.
- **Seller contact storage**:
  - `Seller.telegram_username` — `db/models.py:285`
  - `Seller.phone` — `db/models.py:269`
  - `User.telegram_id` — `db/models.py:158`
  - `UserPhone` (Block C) — multi-phone with per-listing contact choice.

### Partial

- **Generic `send_telegram_notification()`** in
  `backend/app/workers/tasks/notifications.py:366-401` is text-only
  (no `reply_markup` parameter). The crawled-match precedent is a one-off.
  D2 will either generalize this sender or duplicate the pattern.
- **Saved-search push** currently emits one notification per match — no
  batching of "5 new listings". Spec calls for grouping.

### Missing

- **Prefilled-text deep link (`?text=...`)** — no code today uses the
  `t.me/<user>?text=...` pattern. Frontend
  `frontend/src/modules/buyer/pages/listing-detail/ui/page/Page.tsx`
  calls `webApp?.openTelegramLink(getListingShareUrl(...))` to share listings,
  but never prefills a message to a seller.
- **Behavioral-signal table for inline-button presses**. The spec wants
  taps on "В избранное" / "Написать продавцу" to feed the personalization
  vector (Ф-77/Ф-78). No such write path or aggregate column exists; we
  only have `Favorite` rows and `Listing.view_count`.
- **Notification grouping / debounce window** — A4 mentions a 5-min Redis
  batch window but the spec is planned, not coded.

---

## 3. D3 — Deep Links for marketing

### Already exists

- **`/start` payload parsing**: `backend/app/bot/handlers.py:232-268` —
  one prefix wired today (`link_<phone>`) for phone↔Telegram account
  linking after OTP. Pattern is reusable for additional prefixes.
- **`start_param` consumption on frontend**: `frontend/src/app/router/
  Router.tsx:19-36` — `StartParamHandler` reads `webApp.initDataUnsafe.
  start_param`, currently handles **`listing_<uuid>`** only (note: spec
  says `obj_<id>` — see decision needed below).
- **Listing detail entry**: `/listings/:id` route lazy-loaded in
  `frontend/src/modules/buyer/app/router/Router.tsx` — deep entry works.
- **`Telegram.WebApp.BackButton`** wiring:
  `frontend/src/app/router/Router.tsx:39-73` (`TelegramBackButtonManager`).
- **Bot username config**: `backend/app/core/config.py:99-100`
  (`telegram_bot_token`, `telegram_bot_username`); frontend
  `frontend/src/shared/lib/constants.ts:1-12`
  (`SELLER_BOT_USERNAME`, `BUYER_BOT_USERNAME`, `getListingShareUrl()`).
- **`ListingClaim` model** (Ф-106/107): `backend/app/api/v1/claims.py:35-80`
  — claim flow with OTP exists; not yet wired to `/start claim_<user_id>`.

### Partial

- **Prefix mismatch**: spec uses `obj_<id>` and `filter_<string>`;
  code uses `listing_<uuid>`. We must either (a) accept `listing_` as the
  established prefix and update the spec, or (b) add `obj_` alongside
  `listing_` and migrate over time. Recommend (a) — minimal disruption and
  the code is already live in production.
- **`claim_` payload** — claim infra exists in `claims.py` and recent
  migration `prd_crawled_claim_reject.py`, but the `/start claim_<id>`
  → "show Found section" handoff is not wired. E5 (manual B2B onboarding)
  was planned to depend on this.

### Missing

- **Filter URL serialization compatible with Telegram's 64-char limit**.
  Current filter query string in
  `frontend/src/shared/api/buyerListings.ts:43-60` (`RegionLocation`,
  `MinPrice`, `MaxPrice`, `SortingName`) commonly exceeds 64 chars.
  D3 needs either a slug registry (server-stored short IDs → full filter)
  or a compact encoding (district key + 2-3 numeric params).
- **Referral source tracking**. No `User.referral_source` or
  `referred_by_user_id` column. `User.auth_source` only tracks login
  channel (telegram / olx_phone / tg_channel / dev). D3 `ref_<id>` has
  no backing.
- **`agent_<channel_id>` payload** — no infra for B2B agent identification
  via channel.
- **Server-side deep-link builder**: only the frontend `getListingShareUrl`
  exists. Bot/worker code that needs to send links currently
  hand-constructs URLs (e.g. `notifications.py:138-141`).
- **Aggregate analytics for Deep Link entries** — no event table or
  counter records "user came in via payload X on date Y".

---

## 4. D4 — Bot autoposting to seller's channel

### Already exists

- **Multi-locale AI text** (see §2 above) — ready for posting in the
  seller's language.
- **Subscription model** (Block C): `Subscription` rows with
  `SubscriptionType.CABINET` and lifecycle states (ACTIVE / PAUSED /
  CANCELLED / EXPIRED / GRACE) — `backend/app/db/models.py:865-920`.
- **aiogram supports** `bot.edit_message_text`, `bot.edit_message_media`,
  `bot.delete_message` natively (library facts, not codebase facts).

### Partial

- **`Seller.source_channel`** field exists (`db/models.py:274,1731`) but
  semantically it is **inbound** — i.e., the channel where the seller's
  listings were originally crawled from. **Not** the seller's own channel
  to post into. D4 needs a new field (suggested:
  `Seller.autopost_channel_username`) or a new `SellerChannelLink` table.
- **Subscription gate**: model exists, but no
  `check_active_subscription(user_id, type=CABINET)` helper. D4 requires
  this (spec says "Phase 1 — open to all sellers; later — subscribers
  only").

### Missing

- **All outbound channel-post infrastructure**:
  - No code anywhere calls `bot.send_message(chat_id=<channel>, ...)`
  - No "Add bot as admin → ping channel → verify" flow
  - No `BotChannelPost` table storing `(listing_id, channel_id,
    bot_message_id, posted_at, last_edited_at)` for the 48h edit rule
  - No retry queue for transient Telegram API failures
- **`telegram_channel` field for seller's own channel** (vs the inbound
  `source_channel` above).
- **48-hour edit cutoff awareness**: need `posted_at` so we know which
  channel posts can have media edited vs only text.
- **Toggle on listing form** ("Опубликовать в моём канале") — frontend.
- **"Update post in channel" UI** — frontend, both listing card and
  Autoposting section.
- **48h modal with 3 options** — frontend.
- **Sold/Rented edit-in-place vs Paused/Archive delete** — server logic.

---

## 5. D5 — In-bot search + Inline Mode

### Already exists

- **Meilisearch index** with ~80 filterable attributes including
  `district`, `region`, `city`, `microdistrict`, `metro_station` —
  `backend/app/services/search_index.py:35-79`. Index name: `listings`.
- **Search backend router** with env toggle (postgres ↔ meili) —
  `backend/app/api/v1/search_router.py`; `config.py:86`.
- **District dictionary** (canonical, underscore-delimited keys):
  - Backend: `backend/app/core/regions.py:215-227` (REGIONS),
    246-258 (RUSSIAN_TO_KEY), 263-334 (_DISTRICT_ALIASES — includes
    Cyrillic and Latin variants, `infer_region()` at line 376 does
    fuzzy/alias lookup).
  - Frontend: `frontend/src/shared/constants/regions.ts:8-12` (mirror).
- **Crawler LLM extractor** at `telegram-ai/crawler/llm_extractor.py` —
  proves that structured filter extraction from free text is feasible
  (but it's for ingest, not for live query parsing).

### Partial

- **District dictionary** has Russian + Latin + Cyrillic spellings of
  district names in `_DISTRICT_ALIASES`, but **no automated transliteration**
  (Chilanzar ↔ Чиланзар is a pre-baked alias, not a runtime converter).
  For D5 this is fine for districts (closed set) but unhelpful for
  out-of-vocabulary terms (street names, landmarks).
- **Meilisearch typoTolerance** uses defaults (Meilisearch turns it on
  automatically); no explicit `typoTolerance` block in the create-index
  call (`search_index.py:152`). Defaults give typo-1 for short words,
  typo-2 for longer. Probably good enough for D5 fuzzy needs without
  changes.

### Missing

- **Natural-language query parser** that turns "2-комн Чиланзар до 35тыс"
  into a filter dict. No `parse_query()` / `extract_filters()` in backend
  code today. D5 needs either a rule-based parser (regex + dictionary
  lookup) or LLM-assisted parsing (cost concern at scale).
- **`InlineQueryHandler` registration**. aiogram supports it
  (`aiogram.handlers.inline_query`), but zero handlers are registered.
  D5 needs a new handler routing `@bot inline_query` to a search executor.
- **Bot-side search executor** that hits Meilisearch and renders compact
  results. Today the search endpoint is `POST /api/v1/listings` (API,
  not bot). The bot will need either (a) to call the API internally,
  or (b) to import the search service directly.
- **Reply Keyboard with "Поиск" button** — no Reply Keyboard infra
  beyond inline keyboards anywhere in the bot.
- **Levenshtein / fuzzy library**. Python stdlib has `difflib`; we
  could add `rapidfuzz` if needed. Nothing currently imported.

---

## Cross-cutting: language consistency

The spec mandates a sweeping rule: every outbound communication
(push, channel post, bot message, prefilled chat text, inline result)
uses the user's stored `User.language`. Status of this principle:

| Surface | Today | Required by Block D |
|---|---|---|
| `User.language` exists | ✓ | reused |
| Crawled-match push reads user lang | ✓ | reused (template) |
| Generic push (`send_telegram_notification`) | accepts text already-translated | OK |
| Bot replies use `t(lang, key)` | ✓ (`bot/i18n.py`) | extend to uz-cyrl |
| Frontend reads lang from localStorage | ✓ | also write from User.language on first WebApp entry — TODO |
| Settings → Language UI in TWA | not found in /settings page | D1 must add |
| Bot/frontend lang in sync | mostly | D1 must guarantee bot writes propagate to TWA and vice-versa |

---

## Block D dependency satisfaction matrix

| ID | Description | Status |
|----|---|---|
| **D1** | Menu Button via BotFather/`set_chat_menu_button` | MISSING |
| D1 | Trilingual language picker on /start (3 buttons) | PARTIAL — only 2 today |
| D1 | `/language` command | EXISTS |
| D1 | `User.language` field | EXISTS |
| D1 | Telegram `language_code` fallback | EXISTS |
| D1 | "Settings → Language" in TWA | MISSING |
| **D2** | Push sender with `reply_markup` | PARTIAL |
| D2 | `callback_query` router | EXISTS |
| D2 | Seller TG handle for prefilled-chat | EXISTS |
| D2 | Prefilled-text `?text=` deep link | MISSING |
| D2 | AI description in user language | EXISTS |
| D2 | Behavioral-signal store | MISSING |
| D2 | Notification grouping/debounce | MISSING |
| **D3** | /start payload parser | PARTIAL |
| D3 | Frontend `start_param` consumer | EXISTS (`listing_` prefix; spec wants `obj_` — decision needed) |
| D3 | Listing-detail deep entry | EXISTS |
| D3 | Filter URL serialization within 64 char | MISSING |
| D3 | Referral source tracking | MISSING |
| D3 | claim_/agent_ payload handling | PARTIAL |
| D3 | Server-side deep-link builder | MISSING |
| D3 | Deep Link analytics | MISSING |
| **D4** | Outbound channel posting | MISSING |
| D4 | Seller→channel binding | PARTIAL (wrong direction) |
| D4 | Multi-locale AI text | EXISTS |
| D4 | Subscription gate helper | PARTIAL |
| D4 | 48h edit-cutoff metadata | MISSING |
| D4 | Channel-post update/delete flow | MISSING |
| D4 | "Update post" frontend UI | MISSING |
| **D5** | Meilisearch index | EXISTS |
| D5 | District dictionary (3 scripts) | PARTIAL (Cyrillic aliases pre-baked, no live transliteration) |
| D5 | Natural-language query parser | MISSING |
| D5 | aiogram InlineQueryHandler registration | MISSING |
| D5 | Bot-side search executor | MISSING |
| D5 | Fuzzy / Levenshtein helper | MISSING |
| D5 | Reply Keyboard with "Поиск" | MISSING |

---

## Hard constraints discovered (not in spec)

1. **Telegram 64-char `start_param` limit** is hard. Filter encoding for D3
   must respect it — likely via a `DeepLinkPayload` table keyed by short
   random ID.
2. **Telegram 48-hour media-edit cutoff** is real and unmovable. D4 must
   gracefully degrade (text-only edit) or rewrite (delete + repost) past
   that window.
3. **aiogram 3.x is the only bot framework on the backend.** D5 Inline
   Mode and D4 channel posting both go through it. Telethon is used only
   by `telegram-ai/crawler/` and is read-only on channels — not reusable
   for outbound posting.
4. **Bot i18n today has 2 languages, frontend has 3.** D1 must reconcile
   before any other Block D task ships text to users (otherwise an
   uz-cyrl user receives ru fallback in bot but uz-cyrl in TWA — the
   exact inconsistency the spec forbids).

---

## Confidence

- §1 (D1), §2 (D2), §3 (D3) — verified directly against source. High confidence.
- §4 (D4) — high confidence on what's missing; medium on the cleanest model
  shape (a few legitimate design alternatives).
- §5 (D5) — high confidence on infrastructure; medium on the right query-parser
  architecture (rule-based vs LLM-assisted is a real choice with cost
  implications).
