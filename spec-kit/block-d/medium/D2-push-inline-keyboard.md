# D2 — Inline keyboard in push notifications

**Difficulty**: medium (3–4 days)
**Spec source**: Block D V2.0, §D2
**Dependencies**: D1 (user language ready), D3 (Deep Link for "Подробнее"
button), A4 (push pipeline)
**Blocks**: nothing structurally, but feeds personalization signals

---

## Goal

Push notifications about new listings get two inline buttons —
"В избранное" and "Написать продавцу" — so users can act without
opening the TWA. Each press also feeds a behavioral signal for the
personalization vector.

---

## Existing infrastructure to reuse

(see TRUTH_LAYER_AUDIT.md §2 for citations)

- aiogram `InlineKeyboardMarkup` precedent — `crawled_match.py:221-268`
  shows `_send_push()` with 2-button keyboard.
- `callback_query` router — `bot/handlers.py:1541-1635` (claim_crawled
  / reject_crawled). New handlers plug in here.
- `Listing.ai_description_{ru,uz,uz_cyrl}` — already populated by F1.
- Favorites POST is idempotent — `favorites.py:244-265`.
- Seller contact: `Seller.telegram_username`, `User.telegram_id`,
  `UserPhone`.
- Mini App deep link helper for "Подробнее" button:
  `_listing_deep_link(id)` in `notifications.py:138`.

---

## What changes

### Backend

1. **Generalize push sender to accept `reply_markup`**:
   `backend/app/workers/tasks/notifications.py:366-401`
   `send_telegram_notification()` adds an optional `reply_markup:
   Optional[InlineKeyboardMarkup]` parameter. All existing callers
   pass `None`.

2. **Build the inline keyboard for new-listing push**: factor out
   `_listing_action_kb(listing, user_lang)` returning
   ```
   [
     [InlineKeyboardButton("⭐ В избранное", callback_data="fav_add:<id>")],
     [InlineKeyboardButton("✉️ Написать продавцу", url="<prefilled_tg_url>")],
     [InlineKeyboardButton("Подробнее →", url="<mini_app_link>")]
   ]
   ```
   - "Подробнее" uses **URL** kind (not callback) and points to the
     deep link `obj_<id>` / `listing_<id>` (see D3 prefix decision).
   - "Написать продавцу" also URL kind. URL is built by
     `_seller_chat_url(listing, user_lang)` — see step 4.
   - "В избранное" is the **only** `callback_data`-driven button, so
     we can toggle and edit the message in place.
   - Localize labels via `t(lang, "push.fav_add" | "push.contact" |
     "push.details")`.

3. **Wire callbacks** in `bot/handlers.py`:
   - `@router.callback_query(F.data.startswith("fav_add:"))`
   - On hit: look up user (by `from_user.id`), call existing
     idempotent `POST /favorites/{id}` service function directly
     (not HTTP — avoid round-trip; see `favorites.py:244-265` flow).
   - **Toggle behaviour**: if already favorited, remove. Edit the
     callback button to read "✓ В избранном" / "В избранное" and
     update `callback_data` to `fav_remove:<id>` / `fav_add:<id>`.
   - Record a `BehavioralSignal` row (see step 5) BEFORE editing the
     message.
   - `answer_callback_query` with a short tooltip (no toast spam).
   - Edge case: listing taken down between push and tap → answer
     "Это объявление уже неактуально", remove buttons via
     `edit_message_reply_markup(reply_markup=None)`.

4. **Prefilled-chat URL builder** — new helper
   `backend/app/services/seller_contact.py` (new file):
   ```python
   def build_seller_chat_url(
       listing: Listing,
       sender_lang: str,
   ) -> Optional[str]:
       # decide handle: prefer Seller.telegram_username,
       # else tg://user?id=<User.telegram_id>,
       # else None → return None and caller swaps to "Позвонить" button
       handle_or_id = _resolve_handle(listing)
       if handle_or_id is None:
           return None
       intro = render_seller_intro(listing, sender_lang)
       text = quote_plus(intro)
       if handle_or_id.startswith("id:"):
           return f"tg://user?id={handle_or_id[3:]}&text={text}"  # see note
       return f"https://t.me/{handle_or_id}?text={text}"
   ```
   The intro template is translated:
   - `ru`: "Здравствуйте! Увидел в UcharMarket ваше объявление:
     {краткое описание}. Хочу узнать подробнее."
   - `uz`: "Salom! UcharMarket'da e'loningizni ko'rdim:
     {qisqacha tavsif}. Batafsil bilmoqchiman."
   - `uz_cyrl`: "Салом! UcharMarket'да эълонингизни кўрдим:
     {қисқача тавсиф}. Батафсил билмоқчиман."

   `{краткое описание}` = "3-комн в Чиланзаре, 65 м², 35 000 у.е." —
   built from listing structured fields, on the sender's language.

   **Note on `tg://user?id=<id>&text=...`**: Telegram supports the
   `?text=` parameter on `t.me/<username>` but **not** on
   `tg://user?id=`. So if the seller has no `telegram_username` and
   we only have `telegram_id`, we can't prefill text. In that case:
   show the button label as "Написать продавцу" but the URL is the
   plain `tg://user?id=...` without prefill. (Acceptable graceful
   degradation.)

5. **`BehavioralSignal` table** — new migration:
   ```sql
   CREATE TABLE behavioral_signals (
     id UUID PRIMARY KEY,
     user_id UUID REFERENCES users(id),
     listing_id UUID,           -- nullable (e.g. search-result clicks)
     event_type VARCHAR(32),    -- FAV_ADD / FAV_REMOVE / CONTACT_TAP / VIEW
     source VARCHAR(32),        -- PUSH_INLINE / IN_APP / BOT_SEARCH
     created_at TIMESTAMPTZ DEFAULT NOW()
   );
   CREATE INDEX ON behavioral_signals (user_id, created_at DESC);
   CREATE INDEX ON behavioral_signals (listing_id, event_type);
   ```
   - Single table for both push-inline taps **and** in-app actions
     (one stream feeding the recommender per spec §D2 "Behavioral
     signals"). In-app code calls the same writer.

6. **Saved-search push enrichment**:
   `backend/app/workers/tasks/notifications.py` — wherever
   `send_telegram_notification` is called from a saved-search match,
   pass the new `reply_markup` built by `_listing_action_kb`.

7. **Crawler-match push**: keep its existing 2-button keyboard for
   claim/reject — that's a different flow (B2B for sellers, not B2C
   for buyers). Do not overload.

### Frontend

No primary changes. The push action happens in Telegram, not in TWA.
Secondary: ensure listing detail rendered after "Подробнее" tap shows
the listing in the user's language (already true via D1's lang sync).

---

## OPEN QUESTIONS

1. **Toggle vs idempotent**: spec says "race condition при двойном тапе"
   → toggle. Confirm: the second tap **removes** from favorites? Or
   does the button stay "added" and become inert? Recommend toggle
   per spec.
2. **Notification grouping** ("5 new listings for your search" — spec
   edge case). When to batch vs send individual: A4 spec mentions a
   5-min Redis window. Defer to A4 owner or take ownership here?
3. **`tg://user?id=` prefill**: confirm Telegram clients ignore `?text=`
   for this scheme. If newer clients support it, simplify the fallback
   path.
4. **`Подробнее` button always present, or only for crawled listings?**
   Spec calls it "опционально". Recommend always present — cheap,
   gives the user a clear way out.
5. **Behavioral signal weighting**: spec mentions "ignoring = weak
   negative". Out of scope for D2 — record events, weighting is Ф-77/78.
   Confirm.
6. **What if Seller has no `telegram_username` AND no `telegram_id` AND
   no phone?** Currently impossible (a phone is always present for
   sellers). Document the assumption; do not over-engineer.

---

## Acceptance criteria

- New-listing push (saved search or preference match) ships with at
  least "В избранное" and "Написать продавцу" inline buttons.
- "В избранное" toggles state and edits the message in place; idempotent.
- "Написать продавцу" opens Telegram chat with the seller; prefilled
  message includes "UcharMarket", listing type, district, key params;
  prefill language is sender's language.
- "Подробнее" opens TWA at the listing-detail page via deep link.
- Buttons localized per user language.
- Every button press writes one row to `behavioral_signals`.
- Edge cases: deleted listing, missing username, race conditions —
  all handled per spec.

---

## Risks

- Spam-flag: if every saved-search match sends a push with rich keyboard,
  high-activity users may get many. Grouping (Q2) mitigates but is not
  strictly D2.
- `?text=` URL encoding: long prefill intros + Cyrillic may push past
  Telegram URL limits. Cap intro to ~200 chars; truncate via
  `_short_listing_desc()` helper.
- Bot rate limits: aiogram-side, Telegram caps outbound at ~30
  msgs/sec/bot. Existing crawler-match push already manages this; D2
  inherits the same queue.
