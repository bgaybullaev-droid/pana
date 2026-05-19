# D1 — Menu Button + trilingual language picker on first /start

**Difficulty**: medium-easy (1–1.5 days)
**Spec source**: Block D V2.0, §D1
**Dependencies**: A6 (i18n strings) — already satisfied
**Blocks**: D2, D3, D4, D5 (everything sends text on the user's language)

---

## Goal

One-tap entry to TWA from the bot chat (Menu Button), and a trilingual
language picker on first `/start` so all downstream Block D surfaces have
a reliable `User.language` to honour.

---

## Existing infrastructure to reuse

(see TRUTH_LAYER_AUDIT.md §1 for citations)

- `User.language` column — `db/models.py:174`
- `/language` command — `bot/handlers.py:320-323`
- Language picker on /start for new users — `bot/handlers.py:225-312`
- Language callback handler — `bot/handlers.py:326-350`
- aiogram Bot framework — `backend/app/bot/`
- Frontend i18n with 3 locales (ru, uz, uz-cyrl) —
  `frontend/src/shared/i18n/locales/`

---

## What changes

### Backend

1. **Menu Button**: ship a one-shot script (or call once at app
   startup) that runs `bot.set_chat_menu_button(menu_button=
   MenuButtonWebApp(text=..., web_app=WebAppInfo(url=settings.twa_url)))`.
   Suggested location: `backend/app/bot/setup.py` (new module),
   called from `backend/app/bot/main.py` at startup.

2. **Bot i18n trilingual upgrade**:
   - `backend/app/bot/i18n.py:14` — change
     `SUPPORTED_LANGUAGES = ("ru", "uz")` to
     `("ru", "uz", "uz_cyrl")`.
   - Add new translation file `backend/app/bot/translations/uz_cyrl.yml`
     (or whatever loader format `_translations` uses — check at
     `bot/i18n.py:28`).
   - Update `language_code` fallback (`bot/i18n.py:64-70`):
     - `ru` → `ru`
     - `uz` → **`uz_cyrl`** (more common keyboard in UZ per spec)
     - anything else → `ru`

3. **Trilingual picker keyboard**: `bot/keyboards.py:14-20`
   `get_language_kb()` — add a third button:
   ```python
   InlineKeyboardButton(text="🇺🇿 Ўзбекча", callback_data="lang_uz_cyrl")
   ```

4. **Welcome message** in `bot/handlers.py:225-312` — replace single-locale
   greeting with the trilingual block from the spec:
   ```
   Добро пожаловать в UcharMarket!
   Xush kelibsiz UcharMarket'ga!
   Хуш келибсиз UcharMarket'га!

   Выберите язык / Tilni tanlang / Тилни танланг:
   ```

5. **WebApp init-data language sync** (closes the bot/TWA language
   inconsistency): on first authenticated WebApp request where
   `User.language` is null/default and `initData.user.language_code` is
   present, write the mapped value (ru/uz/uz_cyrl) to `User.language`.
   Location: wherever WebApp auth completes — likely
   `backend/app/api/v1/auth.py` after `verify_init_data` succeeds.

### Frontend

1. **"Settings → Язык" picker** in TWA. Today the only language toggle
   lives inside the seller `/profile` flow via bot inline keyboard.
   Need a buyer-facing UI on `/settings` (or `/profile` for non-seller).
   New component reads/writes through a new endpoint
   `PATCH /api/v1/me/language` (body: `{"language": "ru"|"uz"|"uz_cyrl"}`).

2. **Sync localStorage from backend** on app boot if `User.language` is
   set — currently `frontend/src/shared/i18n/index.ts:20` only reads
   `localStorage.i18nextLng`. If the user changed language in the bot,
   the TWA should pick it up. Pattern: on auth success, write
   `localStorage.i18nextLng = user.language` and call
   `i18n.changeLanguage(user.language)`.

3. **Sync backend from localStorage** when the user changes language in
   TWA — call `PATCH /api/v1/me/language` on selector change. This
   guarantees the bot also receives messages in the new language.

---

## OPEN QUESTIONS (resolve in decision-pass)

1. **Menu Button text**: spec offers "Открыть UcharMarket" vs shorter
   "Поиск". Recommend short verb-form per Telegram convention; in user's
   language? But the menu button text is **single-string per bot** —
   Telegram doesn't accept localized variants. Pick one (suggested: a
   neutral wordmark or a universally understood word like "UcharMarket"
   / "Поиск").

2. **Fallback for `language_code = "uz"`**: spec says uz-cyrl is the
   "more common keyboard." Verify with stakeholder. If wrong, change
   D1.2 mapping above.

3. **language storage value**: code currently uses string `"ru"` /
   `"uz"`. Adding the third → either `"uz_cyrl"` (Pythonic) or `"uz-cyrl"`
   (matches frontend locale folder name). Frontend uses `"uz-cyrl"` per
   directory; backend uses `_` per convention. Pick one canonical form
   and write a Vite/loader alias if needed. Recommend `"uz_cyrl"`
   server-side, mapped to `"uz-cyrl"` frontend (i18n loader can be
   configured).

4. **Whether to overwrite an existing `User.language` from Telegram's
   `language_code`**: the spec says fallback applies "до явного выбора"
   (until explicit choice). Recommend: **never overwrite** an explicit
   user choice with Telegram's `language_code` — only use the latter as
   fallback for new users with no value yet.

5. **Menu Button setup**: BotFather one-time setting, or programmatic
   via `set_chat_menu_button` on app startup? Programmatic survives bot
   migration and is self-documenting; BotFather is simpler. Recommend
   programmatic (idempotent — Telegram accepts repeated identical calls).

---

## Acceptance criteria

- `/start` for a new user shows 3-language welcome with 3 buttons
  (Русский / O'zbekcha / Ўзбекча).
- Each button writes the chosen language to `User.language` and confirms
  in the chosen language.
- `/language` re-triggers the picker for existing users.
- Menu Button is configured and opens TWA in one tap on iOS, Android,
  Telegram Desktop.
- Language chosen in bot is reflected in TWA on next open and vice-versa
  (one source of truth: `User.language`).
- TWA Settings has a Язык / Til / Тил picker that writes through to
  `User.language`.
- Telegram `language_code` is used as fallback only when `User.language`
  is unset; never overrides explicit choice.
- All bot strings used in Block D have ru, uz, uz_cyrl entries.

---

## Risks

- Adding uz_cyrl to `SUPPORTED_LANGUAGES` without translations exists ⇒
  fallback to ru, but logged as warning (`bot/i18n.py:99`). All new
  Block D strings must ship all 3 locales.
- Telegram clients with very old versions don't support Menu Button with
  `web_app` type — graceful degradation, those users still use `/start`.
- Existing users with `User.language="uz"` may have meant Cyrillic but
  were forced into Latin. Migration step: leave as-is, let users
  switch via `/language` if they want.
