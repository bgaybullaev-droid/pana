# 17 — Bot Inline Mode (`@bot query`)

**Status:** DONE
**Complexity:** MEDIUM — single inline_query handler tapping the existing Meilisearch index plus deep-link wiring.
**Vision-doc refs:** §4.2 ("Inline Mode: Поиск объявлений прямо в любом чате через @ucharmarket_bot — виральный инструмент")
**Why now:** Phase 2 polish. Pure organic growth — no UI cost, no marketing cost; users do the work.

## Goal

Typing `@<bot_username> 2 комнаты Чиланзар` in any Telegram chat returns inline results — listing cards that, when sent, render with image, price, title, district and a button "Подробнее на UcharMarket". Anyone in the chat tapping the result lands in the Mini App on that listing's detail page.

## Implementation outline

aiogram inline-query handler:

```python
@dp.inline_query()
async def handle_inline_query(query: InlineQuery):
    text = query.query.strip()
    if not text:
        results = await get_top_listings(limit=20)
    else:
        results = await search_listings(text, limit=20)

    answers = []
    for listing in results:
        answers.append(InlineQueryResultArticle(
            id=str(listing.id),
            title=f"{property_label} {rooms_text} в {district}",
            description=f"{price_str} · {listing.area} м²",
            thumb_url=listing.primary_image_url,
            input_message_content=InputTextMessageContent(
                message_text=render_share_card(listing),
                parse_mode="HTML",
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Подробнее на UcharMarket",
                    url=f"https://t.me/{bot_username}?startapp=listing_{listing.id}",
                ),
            ]]),
        ))

    await query.answer(answers, cache_time=60, is_personal=False)
```

`search_listings(text)` reuses the Meilisearch index (already populated) — query against title + description + district fields.

## Behaviour & invariants

- **No auth required** — inline queries go through the bot anonymously.
- **Cache** — 60 s `cache_time` on `query.answer` prevents re-querying for trending searches.
- **Result limit** — Telegram caps at 50; our 20 is safer for rendering.
- **Shared card** — text-only fallback when no image (rare). Image preview renders inline in chat for cards with `thumb_url`.
- **Deep link to Mini App** — `startapp=listing_<id>` requires [`deep-links-filter-prefill`](../easy/deep-links-filter-prefill.md) routing on the frontend.

## Acceptance criteria

- Typing `@<bot> 2 ком чиланзар` in any chat shows up to 20 matching listings.
- Sending a result posts a card with image + button to the chat.
- Tapping the button opens the Mini App on the listing detail.
- Empty query returns top listings (most-viewed last 7 days).

## Open questions

- Localisation — query language detection? Probably accept any of RU/UZ tokens; Meilisearch handles unicode out of the box.
- Tracking — record inline-query terms anonymously for trend analytics? Useful but optional.
