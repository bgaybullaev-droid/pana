# Block D — Decision Matrix (recommended defaults)

> Format: every OPEN QUESTION from D1–D5 specs + 5 cross-cutting
> decisions, each with **recommended answer**, **rationale**,
> **alternatives considered**, and **implementation impact**.
>
> User action: read the recommended column. Approve all or specify
> overrides per row. After this doc is signed off, PR-D1 starts the
> same day with zero remaining ambiguity.

---

## How to read this

| Status legend | Meaning |
|---|---|
| ✅ **Decided** | Recommended default stands; no expected override |
| ⚠️ **User input needed** | Either choice is defensible; product call |
| 🔵 **Confirm** | Recommended is strong; quick yes/no |

Each row's "Impact" column lists files / behavior that change if the
override is taken instead of the default. If a recommendation is
accepted, no change.

---

## Cross-cutting decisions (CC)

### CC1 — Block ordering of OPEN QUESTIONS for review

✅ **Decided.** Read top-to-bottom. The 9 critical decisions are
flagged 🚨 — they block PR-D1 start. The other 25 block their own
specific PR but not the kickoff.

### CC2 — Language storage canonical form

🚨 ✅ **Recommended**: `"uz_cyrl"` in backend (DB, bot Python, API
contracts); `"uz-cyrl"` in frontend i18n folder structure.

**Rationale**: Frontend already uses `uz-cyrl` directory; backend
follows Python `snake_case`; map at the API boundary (i.e. the
PATCH `/me/language` endpoint accepts either and writes the canonical
`uz_cyrl`).

**Alternative**: pick one. Renaming the frontend folder is a noisier
diff than mapping at the edge.

**Impact if overridden**: rename `frontend/src/shared/i18n/locales/uz-cyrl/`
→ `uz_cyrl/` + adjust loader.

### CC3 — Where the language-change side-effect happens

✅ **Recommended**: `PATCH /api/v1/me/language` is authoritative. Bot
`lang_*` callbacks also write to `User.language`. Frontend
`localStorage.i18nextLng` is a hot cache only.

**Rationale**: One source of truth. Frontend on app boot syncs from
User if logged in; offline / pre-auth uses localStorage.

**Impact if overridden**: not applicable — only this single design
keeps the invariant.

### CC4 — `User.language` initial value for new users via WebApp

🔵 **Recommended**: write the mapped initData.language_code on
**first** authenticated request where `User.language` is at default
(`"ru"`). Mapping: `ru→ru`, `uz→uz_cyrl`, anything else→ru.

**Rationale**: Smart default; the bot's `/start` picker happens later
if the user chooses to override.

**Alternative**: Never auto-set; force users through the picker. More
intrusive UX.

**Impact if overridden**: drop the auth-time sync code in
`api/v1/auth.py`; bot remains the only path to set language.

### CC5 — Behavioral-signal weighting

🔵 **Recommended**: D2 records events only. Weighting / decay /
vector update is owned by Ф-77/Ф-78 (personalization spec, not
Block D).

**Rationale**: Concerns separation. The recommender team can
consume `behavioral_signals` table any time.

**Impact if overridden**: D2 grows scope; not advised.

---

## D1 — Menu Button + language picker (5 questions)

### D1-Q1 — Menu Button text

🚨 ✅ **Recommended**: `"UcharMarket"` (the wordmark itself).

**Rationale**: Telegram doesn't accept localized variants for the
menu button — it's a single global string per bot. Pick something
all three audiences recognize: the brand. "Поиск" is shorter but
russocentric.

**Alternatives**:
- `"Поиск"` — short, action-oriented, but only Russian.
- `"Открыть"` — verb, but feels generic.
- Localized via `set_chat_menu_button` per user — requires per-chat
  call on every interaction; impractical at scale.

**Impact**: One string in `bot/setup.py`; trivial to change later.

### D1-Q2 — Fallback for `language_code = "uz"`

🚨 🔵 **Recommended**: `"uz"` → `"uz_cyrl"` (Cyrillic).

**Rationale**: Per spec, Cyrillic is the more common keyboard among
Uzbek Telegram users. We trust the spec here.

**Alternatives**: `uz → uz` (Latin) — minority preference.

**Impact**: `bot/i18n.py:64-70` mapping line.

### D1-Q3 — Canonical Cyrillic storage value

🚨 ✅ **Recommended**: backend `"uz_cyrl"`, frontend folder `"uz-cyrl"`
with alias mapping at the i18n loader.

**Rationale**: see CC2.

**Impact**: see CC2.

### D1-Q4 — Overwriting `User.language` with Telegram `language_code`

🚨 ✅ **Recommended**: **Never** overwrite an explicit user choice.
Only write when `User.language` is at default unset value, and only
on the FIRST authenticated request that has initData.

**Rationale**: User intent is sacred. Sticky preference must survive
SIM swap or device change.

**Impact**: guard in `api/v1/auth.py` — `if user.language_was_set:
skip`.

### D1-Q5 — Menu Button setup mechanism

🔵 **Recommended**: programmatic via `bot.set_chat_menu_button` at
app startup. Not BotFather.

**Rationale**: Idempotent (Telegram accepts repeats); survives bot
migration; self-documenting in code; works in test bots automatically.

**Alternative**: BotFather manual setup. Acceptable but creates drift
between production and dev.

**Impact**: `bot/setup.py` (new); called from `bot/main.py` after
dispatcher init.

---

## D2 — Push inline keyboard (6 questions)

### D2-Q1 — Toggle vs idempotent for "В избранное"

🚨 ✅ **Recommended**: toggle. First tap adds; second tap removes.

**Rationale**: per spec, natural behavior for this button kind.

**Alternative**: stay added; second tap inert. Less informative
mid-stream; rejected.

**Impact**: callback `fav_add:<id>` becomes `fav_remove:<id>` after
add; message edited to "✓ В избранном".

### D2-Q2 — Notification grouping ("5 new listings")

⚠️ **Recommended**: defer to A4 owner; D2 does not implement
grouping. The hook point is `workers/tasks/notifications.py` — when
grouping ships there, D2's reply_markup attaches per group too.

**Rationale**: A4 spec explicitly mentions a 5-min Redis batch
window; that's where the design lives. D2 is about per-notification
buttons, not aggregation.

**Alternative**: D2 implements grouping. Scope creep; rejected.

**Impact**: nothing in D2 PR; future A4 work picks this up.

### D2-Q3 — `tg://user?id=` prefill text support

🔵 **Recommended**: assume **not** supported. If `Seller.telegram_username`
is empty, use `tg://user?id=<id>` **without** `?text=`. Graceful
degradation.

**Rationale**: undocumented behavior across Telegram clients.

**Alternative**: try with text and hope. Risk: silent corruption on
some clients.

**Impact**: `services/seller_contact.py` returns URL with no text
param when handle is missing.

### D2-Q4 — "Подробнее" button always present?

🔵 **Recommended**: always present. Cheap; gives the user an out.

**Rationale**: spec calls it optional but recommends; we recommend
always.

**Impact**: keyboard factory unconditionally renders 3 buttons.

### D2-Q5 — Behavioral signal weighting (in scope?)

✅ **Recommended**: out of scope for D2. See CC5.

### D2-Q6 — Seller missing all contact methods

🔵 **Recommended**: impossible by current data model (phone is
required for sellers). Add an assert in `services/seller_contact.py`;
log + skip the "Написать" button if it ever happens.

**Rationale**: defensive but not over-engineered.

**Impact**: one branch in the factory.

---

## D3 — Deep links (7 questions)

### D3-Q1 — `obj_` vs `listing_` prefix

🚨 ✅ **Recommended**: accept **both** on inbound; emit only
`listing_` on outbound. Marketing materials may use `obj_` if they
prefer.

**Rationale**: existing `listing_` is live in `notifications.py:138`
and frontend `Router.tsx:28`. Renaming breaks existing share URLs.
Accepting both costs ~3 lines.

**Alternative A**: migrate to `obj_`. High risk; rejected.
**Alternative B**: only accept `listing_`. Spec mismatch.

**Impact**: registry handler aliases; frontend `StartParamHandler`
accepts either prefix.

### D3-Q2 — `claim_` payload entropy

🚨 ✅ **Recommended**: opaque 12-char IDs in `claim_invites` table.
Single-use, expiry (7 days default).

**Rationale**: supports revocation, tracking, single-use, easy expiry.
HMAC-signed payloads are slimmer but no revocation.

**Alternative**: HMAC-signed user_id. Rejected — no revocation.

**Impact**: migration `prl_deep_link_payloads` includes `claim_invites`.

### D3-Q3 — `ref_` semantics for existing users

🔵 **Recommended**: silently ignore for already-registered users.
Only first-time registration records `referred_by_user_id`.

**Rationale**: prevents retroactive attribution abuse.

**Alternative**: allow attribution even for existing users. Abuse
vector; rejected.

**Impact**: handler guard `if user.exists: log_and_skip`.

### D3-Q4 — `filter_` URL TTL

🔵 **Recommended**: never expire. The `deep_link_payloads` row stays
indefinitely.

**Rationale**: cheap; shareable links should not rot.

**Alternative**: 90-day TTL. Doesn't add value, breaks bookmarks.

**Impact**: no `expires_at` column needed for `deep_link_payloads`.

### D3-Q5 — Aggregate analytics dashboard

🔵 **Recommended**: skip the UI for MVP. Raw `deep_link_events`
table is queryable.

**Rationale**: keep scope contained; product can SQL.

**Impact**: no admin UI; one extra index for likely queries.

### D3-Q6 — Migrate existing `link_<phone>` into new registry

🔵 **Recommended**: yes — single dispatch path.

**Rationale**: cleaner code; existing behavior preserved.

**Impact**: refactor `bot/handlers.py:232-268` into registry.

### D3-Q7 — `agent_<channel_id>` payload format

🔵 **Recommended**: channel username (e.g. `agent_realestate_tashkent`),
mapped to a row in `claim_invites` with `kind="agent"` and
`channel_username` populated.

**Rationale**: human-readable; matches B2B onboarding flow (E5)
where channel username is what we have on hand.

**Alternative**: numeric channel_id. Less readable; rejected for
marketing-material-friendly URLs.

**Impact**: `claim_invites.channel_username` column (already in
migration).

---

## D4 — Bot autoposting (8 questions)

### D4-Q1 — Phase-1 access policy

🚨 ✅ **Recommended**: open to all sellers during the test period.
`check_active_subscription(user, type=CABINET)` returns True
unconditionally if a `settings.autopost_test_period_until` future
date is set. After that date, real subscription check.

**Rationale**: per spec; aligns with C1 V2.0 test-period framing.

**Impact**: `services/subscriptions.py:check_active_subscription` —
a single branch driven by config flag.

### D4-Q2 — Per-listing default checkbox state

🚨 🔵 **Recommended**:
- For **manually-created** listings (`SourceType.MANUAL`): checkbox
  default `True` (if seller has channel connected).
- For **claimed-from-crawler** listings (`SourceType.CLAIMED`):
  checkbox default `False`.

**Rationale**: a seller claiming 50 crawled listings doesn't want
50 channel posts in one minute. Manual listings = explicit intent.

**Alternative**: always `True`. Risk of channel-flood and spam-flag.

**Impact**: `frontend/src/modules/seller/pages/create-listing/`
checkbox initial value derived from listing source.

### D4-Q3 — Multi-channel per seller

🔵 **Recommended**: single channel per seller in MVP, as spec.

**Impact**: schema reflects this (single columns on Seller table).

### D4-Q4 — Footer text

🔵 **Recommended**: `"Через @ucharmarket_bot"` (Russian) for ru locale,
`"@ucharmarket_bot orqali"` for uz Latin, `"@ucharmarket_bot орқали"`
for uz Cyrillic. Username from `settings.telegram_bot_username`.

**Rationale**: localized but compact.

**Impact**: 3 i18n keys: `autopost.footer`.

### D4-Q5 — Private channel support

🔵 **Recommended**: yes, if the bot is admin with post permission.
Connect endpoint requires public username for initial lookup; once
verified, the bot operates by `chat_id`.

**Rationale**: per spec.

**Impact**: connect endpoint resolves `@username` once, stores
`autopost_channel_id`; subsequent ops use id.

### D4-Q6 — Seller deletes a post manually from channel

🔵 **Recommended**: on next attempted edit/delete, Telegram returns
`MessageToEditNotFound` / `MessageToDeleteNotFound`. Mark
`bot_channel_posts.status = "deleted"`; **do not** auto-repost.

**Rationale**: seller chose to remove it.

**Impact**: handler in `services/autopost.py:update_post` catches
the error.

### D4-Q7 — Per-channel update queue pace

🚨 🔵 **Recommended**: 1 edit/sec serial per channel, Redis-backed
lock.

**Rationale**: Telegram channel-edit limit is stricter than
DM-message limit; 1/sec is conservative-safe.

**Alternative**: 5/sec. Risk of `RetryAfter`; rejected.

**Impact**: `services/autopost.py:update_post` acquires
`Redis SETNX autopost:channel:{channel_id}` with 1s TTL; retries
queued.

### D4-Q8 — Disconnect behavior for existing posts

🔵 **Recommended**: option (c) — stop tracking but leave posts in
the channel.

**Rationale**: respects seller agency; not destructive; recoverable
by reconnect.

**Alternative A**: leave posts and keep tracking (no — confuses staleness
logic).
**Alternative B**: delete all posts — destructive; rejected.

**Impact**: disconnect endpoint clears Seller columns; does not touch
`bot_channel_posts`.

---

## D5 — In-bot search + Inline Mode (8 questions)

### D5-Q1 — Query parser approach

🚨 ✅ **Recommended**: rule-based (regex + curated YAML dictionaries
of districts, deal types, property types, currencies, morphology
forms).

**Rationale**: latency budget for Inline Mode is ~1s end-to-end.
LLM adds 200–500ms and per-call cost; not justifiable at typical
query volumes.

**Alternative**: LLM-assisted. Reconsider only if rule-based shows
>10% mis-parse rate after a month of telemetry.

**Impact**: `services/query_parser.py` is pure Python; ships with
`query_parser_dict.yml` as a living asset.

### D5-Q2 — "Сохранить поиск" from bot

🔵 **Recommended**: do not show the button in bot results. Show a
one-line hint linking to TWA.

**Rationale**: spec preference; less duplication; less code.

**Impact**: bot result formatter omits the button; appends a hint.

### D5-Q3 — Result language for anonymous Inline Mode users

🔵 **Recommended**: fallback to `query.from.language_code` from
Telegram. For unknown / empty values → ru.

**Rationale**: matches D1's fallback policy.

**Impact**: result formatter uses Telegram-provided value when
`User.language` is not available.

### D5-Q4 — Heuristic for "is this a search query?"

🔵 **Recommended**: conservative. Trigger if **any** of:
- a known district name appears (after fuzzy match)
- `\d+\s*(комн|комнат|xona|hona)` matches
- "продажа", "аренда", "купить", "снять", "sotiladi", "ijara"
  appears
- a price token appears (digits + optional unit like тыс, k, у.е.,
  usd, сум, so'm)

Otherwise: tooltip "Не понял запрос…" with "Поиск" Reply Keyboard.

**Rationale**: false-positives are confusing ("Привет" parsed as a
search would feel broken).

**Impact**: `bot/handlers.py` heuristic function on free-text.

### D5-Q5 — Inline Mode placeholder

🔵 **Recommended**: "Район, комнаты, цена" (Russian). Set via
BotFather. Telegram does not support localized placeholders.

**Rationale**: short, action-oriented; matches the spec.

**Impact**: one BotFather setting; document in `bot/setup.py`
comments.

### D5-Q6 — Pagination in bot search

🔵 **Recommended**: no in-bot pagination. 5–10 results + "Open all
in app" button.

**Rationale**: paginating in chat is messy; "Open all" punts to TWA
which has proper pagination.

**Impact**: result formatter caps at 10.

### D5-Q7 — Cache invalidation

🔵 **Recommended**: 60s Redis cache + Telegram's `cache_time=60`.
Accept brief staleness per spec.

**Rationale**: spec explicitly says brief stale results in Inline
Mode is normal Telegram behavior.

**Impact**: Redis `setex(query_hash, 60, results)` in
`services/bot_search.py`.

### D5-Q8 — Currency default

🚨 🔵 **Recommended**: UZS default. Switch to USD if "у.е.", "y.e.",
"usd", "$" appears anywhere in the query.

**Rationale**: Tashkent buyers think in UZS unless they explicitly
say otherwise; ambiguous tokens like "30000" without unit are
much more likely UZS.

**Impact**: `query_parser.py` price-extraction sets `price_currency`
default `"UZS"`, overrides if matcher hits USD keywords.

---

## Summary table — 9 critical 🚨 + 25 non-critical

| # | Topic | Recommended | Status |
|---|---|---|---|
| 1 | D1-Q1 Menu Button text | `"UcharMarket"` | 🚨 |
| 2 | D1-Q2 `language_code=uz` fallback | `uz_cyrl` | 🚨 |
| 3 | D1-Q3 Canonical Cyrillic value | `uz_cyrl` backend, `uz-cyrl` frontend | 🚨 |
| 4 | D1-Q4 Overwrite explicit lang? | Never | 🚨 |
| 5 | D2-Q1 Toggle vs idempotent | Toggle | 🚨 |
| 6 | D3-Q1 `obj_` vs `listing_` | Accept both; emit `listing_` | 🚨 |
| 7 | D3-Q2 `claim_` entropy | Opaque IDs in `claim_invites` | 🚨 |
| 8 | D4-Q1 Phase-1 access | Open to all in test period | 🚨 |
| 9 | D4-Q2 Default checkbox state | True (manual) / False (claimed) | 🚨 |
| 10 | D4-Q7 Per-channel pace | 1 edit/sec | 🚨 |
| 11 | D5-Q1 Parser approach | Rule-based | 🚨 |
| 12 | D5-Q8 Currency default | UZS | 🚨 |
| 13 | D1-Q5 Menu Button setup | Programmatic | 🔵 |
| 14 | D2-Q2 Notification grouping | Defer to A4 | ⚠️ |
| 15 | D2-Q3 `tg://user?id=` prefill | No text param | 🔵 |
| 16 | D2-Q4 "Подробнее" presence | Always | 🔵 |
| 17 | D2-Q5 Signal weighting | Out of scope | ✅ |
| 18 | D2-Q6 Seller no-contact case | Assert + skip | 🔵 |
| 19 | D3-Q3 `ref_` for existing | Ignore | 🔵 |
| 20 | D3-Q4 `filter_` TTL | Never expire | 🔵 |
| 21 | D3-Q5 Analytics dashboard | Skip; SQL | 🔵 |
| 22 | D3-Q6 Migrate `link_` | Yes | 🔵 |
| 23 | D3-Q7 `agent_` format | Channel username | 🔵 |
| 24 | D4-Q3 Multi-channel | One per seller | 🔵 |
| 25 | D4-Q4 Footer text | Localized 3-way | 🔵 |
| 26 | D4-Q5 Private channels | Yes | 🔵 |
| 27 | D4-Q6 Manual delete from channel | Mark deleted; no repost | 🔵 |
| 28 | D4-Q8 Disconnect cleanup | Stop tracking; leave posts | 🔵 |
| 29 | D5-Q2 Save-search from bot | Hint only; no button | 🔵 |
| 30 | D5-Q3 Lang for anon Inline | Telegram `language_code` | 🔵 |
| 31 | D5-Q4 Is-query heuristic | Conservative | 🔵 |
| 32 | D5-Q5 Inline placeholder | "Район, комнаты, цена" (ru) | 🔵 |
| 33 | D5-Q6 Pagination in bot | No | 🔵 |
| 34 | D5-Q7 Cache invalidation | 60s | 🔵 |
| CC2 | Canonical Cyrillic value | see D1-Q3 | ✅ |
| CC3 | Language-change side-effect | PATCH `/me/language` authoritative | ✅ |
| CC4 | Auto-set language on first auth | Yes if default | 🔵 |
| CC5 | Signal weighting ownership | Ф-77/78 | 🔵 |

🚨 = blocks PR-D1 start. 12 critical items.

---

## Approval format

Sign off in one of these forms:

- **"Approve all defaults"** → all 34 decisions stand; PR-D1 starts.
- **"Approve all except: D4-Q1, D5-Q1"** (etc.) → list overrides;
  state your preferred value for each. I update this file with
  ratified rows.

The implementation roadmap (`IMPLEMENTATION_ROADMAP.md`) is built
against the recommended defaults. Overrides may shift specific PR
details (called out in each row's "Impact").
