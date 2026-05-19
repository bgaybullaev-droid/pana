# D5 — In-bot search (form + Inline Mode) with fuzzy matching

**Difficulty**: hard (5–7 days)
**Spec source**: Block D V2.0, §D5
**Dependencies**: D1 (language for results), D3 (deep links for "open
in app" + obj_ for each result), A7 (parser dictionary), F1 (AI text
for result snippets)
**Blocks**: nothing structurally — viral mechanic + power-user path

---

## Goal

Users can search listings without opening TWA, in two contexts:

1. **In bot chat**: tap "Поиск" or write free text — bot returns a
   compact list of 5–10 matches and a "Open all in app" button.
2. **Inline Mode** in any chat: type `@ucharmarket_bot 2комн Чиланзар`
   and pick a card to send into the chat.

Both contexts use the same query parser with fuzzy district matching,
transliteration, and morphological forgiveness.

---

## Existing infrastructure to reuse

(see TRUTH_LAYER_AUDIT.md §5 for citations)

- Meilisearch index `listings` with ~80 filterable attributes,
  including `district`, `region`, `city`, `metro_station` —
  `backend/app/services/search_index.py`.
- Default Meilisearch typoTolerance (typo-1/typo-2 — good enough out
  of the box).
- District dictionary with Cyrillic/Latin aliases —
  `backend/app/core/regions.py:263-334` and helper `infer_region()`.
- aiogram 3.x — `InlineQueryHandler` available, not yet registered.
- AI text per locale on every listing.

---

## What changes

### Backend

1. **Natural-language query parser** —
   `backend/app/services/query_parser.py` (new):
   ```python
   @dataclass
   class ParsedQuery:
       district: Optional[str]          # canonical key e.g. "chilonzor"
       rooms_min: Optional[int]
       rooms_max: Optional[int]
       price_min: Optional[int]
       price_max: Optional[int]
       price_currency: Optional[str]    # UZS / USD inferred from token
       deal_type: Optional[str]         # SALE / RENT
       property_type: Optional[str]     # APARTMENT / HOUSE / OFFICE / ...
       raw_text: str                    # original input
       confidence: float                # 0.0-1.0 (0 if nothing parsed)

   def parse(text: str, user_lang: str) -> ParsedQuery: ...
   ```
   Implementation: rule-based.
   - **Districts**: `infer_region(token)` already does fuzzy lookup
     with Cyrillic/Latin. Iterate over tokens and pick the strongest
     match. Reuse existing module.
   - **Rooms**: regex `(\d+)[-\s]*(?:комн|комнат|xona)` plus word
     forms ("одно", "двух", "трёх" → 1, 2, 3).
   - **Price**: regex `(?:до|less than|от|more than)?\s*([\d\s]+)
     (?:тыс|k|млн|m|у\.е|usd|сум|so'm)?`. Currency inferred from token
     suffix.
   - **Deal type**: keyword set
     `{ru: [продажа,купить,...]; uz: [sotiladi,sotib olish,...]}`.
   - **Property type**: keyword set including
     `[квартира, дом, офис, xonadon, ...]`.
   - **Morphology**: precompiled set of forms in a YAML dictionary
     `backend/app/services/query_parser_dict.yml`.
   - **No LLM call** in the hot path — cost concern and latency.
     LLM stays in the ingest crawler.

2. **Search executor** for the bot —
   `backend/app/services/bot_search.py` (new):
   - Translates `ParsedQuery` to Meilisearch filter expression.
   - Calls `meili_client.index("listings").search(...)` with limits
     5–10 for in-bot and up to 20 for Inline Mode.
   - Returns ordered list of `BotSearchResult` (id, title, price,
     district, ai_description, photo_url).
   - Cache key: `(parsed_filter_hash, lang)` → Redis TTL 60s.

3. **Bot search command** (sceanrio 1):
   - `/search` command + free-text fallback in the message router.
   - Heuristic to recognize a query: contains a known district name,
     OR contains `\d+\s*(комн|xona)`, OR contains `продажа|аренда|
     sotiladi|ijara|купить|снять`, OR contains a price token.
   - If heuristic fails: reply "Не понял запрос. Попробуйте: район,
     количество комнат, цену." with a Reply Keyboard button "Поиск".
   - On success: render a compact message (markdown link per row,
     plus a single "Открыть все результаты в приложении" button with
     filter_<deep-link-id>).

4. **Inline Mode handler** —
   `backend/app/bot/inline.py` (new):
   ```python
   @inline_router.inline_query()
   async def handle_inline(query: InlineQuery): ...
   ```
   - Parse `query.query` with same parser.
   - Build up to 20 `InlineQueryResultArticle` items with
     `input_message_content=InputTextMessageContent(...)` + per-item
     inline button "Открыть в UcharMarket" pointing to obj_/listing_
     deep link.
   - Empty `query.query` → return last 10–20 ACTIVE listings as
     examples.
   - `cache_time=60` to mitigate stale-card issues per spec.

5. **Register the inline handler**: `backend/app/bot/main.py` —
   include `inline_router` in the dispatcher.

6. **Spam / rate-limit**: per-user counter
   `bot:search_rl:<user_id>` with sliding-window in Redis (e.g. 60
   queries/min). Above limit → silently truncate to one
   answer/minute.

### Frontend

No primary changes. Secondary:
- The "Открыть все в приложении" button uses `filter_<id>` from D3,
  so the home page should be tolerant of filters delivered via the
  deep-link mechanism (D3 frontend extension already handles this).
- "Открыть в UcharMarket" inline buttons land on `/listings/:id`
  (already wired).

---

## OPEN QUESTIONS

1. **Query parser approach**: rule-based (recommended) vs LLM-assisted.
   LLM is more forgiving but adds 200–500ms latency and $$ per call.
   Recommend rule-based, with the YAML dictionary curated alongside
   A7's parser dictionary.
2. **"Сохранить поиск" from bot**: spec says don't show the button in
   bot — only in TWA. Confirm. Recommend: show a one-line hint after
   results "Сохраните поиск в приложении, чтобы получать уведомления"
   linked to TWA.
3. **Bot search lang for results**: spec says result snippets use
   user's language. For B2C buyer (User.language) — clear. For
   anonymous users using Inline Mode? Inline queries carry
   `query.from.language_code` but we don't know who they are in our
   DB. Use Telegram's `language_code` as fallback (matches D1's same
   convention).
4. **Heuristic for "is this a query"**: above heuristic is conservative.
   Should we be more aggressive (try to parse any user message that's
   not a command)? Recommend conservative — false-positives confuse
   users.
5. **Inline Mode placeholder text**: BotFather settings allow setting
   a placeholder. Recommend: "Район, комнаты, цена".
6. **Pagination in bot search**: spec says 5–10 results + "Open all" —
   no in-bot pagination. Confirm. Recommend yes (paginating in chat
   is messy).
7. **Cache invalidation**: 60s Redis cache + Telegram's own
   `cache_time=60`. If a listing's price changes mid-cache, stale
   results may appear. Acceptable per spec "это нормальное поведение
   Telegram."
8. **Currency normalisation**: query "до 35тыс" — is 35тыс UZS or USD?
   Recommend: default to UZS, but switch to USD if "у.е." / "usd" /
   "$" appears anywhere.

---

## Acceptance criteria

- `@ucharmarket_bot <query>` in any chat returns up to 20 results
  with deep-link buttons.
- Free-text query to the bot chat returns 5–10 compact results +
  "Открыть все" button.
- "Поиск" Reply-Keyboard button shows the entry prompt for novices.
- Query parser extracts district / rooms / price / deal type / property
  type from natural Russian and Uzbek (Latin + Cyrillic).
- Fuzzy district matching covers transliteration and 1–2 typos.
- Unrecognized queries get a helpful fallback message — never an empty
  list with no explanation.
- Empty inline query returns 10–20 most-recent listings as examples.
- Inline results carry `cache_time=60`.
- All result text is in the user's language.
- Per-user rate-limit prevents abuse.

---

## Risks

- **Latency**: Inline Mode UX expects ~1s. Parse + Meilisearch + render
  must fit. Pre-compiled regexes; Meilisearch typically <50ms.
- **Cold cache**: first query for a popular filter may be slow. The
  60s Redis cache absorbs subsequent queries.
- **District ambiguity**: "Юнусабад" matches both Юнусабадский район
  and the metro station nearby. `infer_region` returns the district
  variant; this is correct.
- **Inline Mode TOS**: bots advertising via inline mode in unrelated
  chats can get flagged. Our use case is user-initiated, so safe.
- **Query parser drift**: as users invent new phrasing, the dictionary
  needs updates. Treat the YAML as a living asset; metrics on
  unrecognised-query rate must inform iteration.
