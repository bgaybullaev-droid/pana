# 07 — Bot Autoposting to Seller's Telegram Channel

**Status:** DONE
**Complexity:** HARD — my_chat_member listener, multi-channel state machine (verify / promote / demote), edit / delete / re-circulation, Telegram rate limits, soft-fail invariants on every channel write.
**Vision-doc refs:** Section 5.2 (the *strategic* viral loop)
**Why now:** Phase 1. The doc treats this as the single biggest organic-acquisition lever. 50 sellers each running a Telegram channel = 50 free B2C funnels.

## Goal

Seller adds the UcharMarket bot as admin (with post permission) to their own Telegram channel. From that point on:

- Every published or updated listing in the seller cabinet auto-posts to the channel as a styled card with photos, price, key params, and a `📎 Подробнее на UcharMarket` button (deep-links into the listing detail).
- Marking a listing sold either edits the post to `🔴 ПРОДАНО` or deletes it (seller's choice).
- Periodic re-circulation: pick N best-performing active listings per week and bump them to channel top.
- Seller can disable categories or set frequency in cabinet.

## Proposed data model

Add to `Seller` (or a 1:1 satellite `SellerChannel` if churn is expected):

| Column | Notes |
|---|---|
| `channel_id` | BigInt, nullable. Telegram channel id (negative number, e.g. `-100123456789`). |
| `channel_username` | Optional username, for display only. |
| `channel_admin_verified_at` | Timestamp of last successful admin check. Nullable. |
| `channel_autopost_enabled` | Bool, default true. |
| `channel_autopost_categories` | TEXT[] (e.g. `["sell.apartment", "rent.house"]`). Empty = all. |
| `channel_on_sold` | Enum `EDIT_SOLD` / `DELETE` / `KEEP`. Default `EDIT_SOLD`. |

Add to `Listing` (or new table `ListingChannelPost` for multi-channel future):

| Column | Notes |
|---|---|
| `channel_message_id` | Bigint, nullable. The bot's message id in the seller's channel; lets us edit/delete later. |

Migration adds these columns + a partial index on `Seller(channel_id) WHERE channel_id IS NOT NULL`.

## Proposed flow

### A. Onboarding the channel

1. Seller cabinet "Channels" page — instructs them to add `@<bot_username>` as admin with **Post messages** permission.
2. Bot detects `my_chat_member` update — if it's promoted to admin in a channel, it stores the channel id as a candidate.
3. Frontend offers a "Verify channel" button that calls `POST /sellers/me/channel/verify` with `{channel_id_or_username}`. Backend calls `bot.get_chat_administrators(chat_id)`; if the bot is in the list with post rights, sets `Seller.channel_id` and `channel_admin_verified_at = now()`.
4. The `my_chat_member` listener also handles demotion → clear `channel_id`.

### B. Posting on listing publish

Celery task `post_listing_to_channel(listing_id)`, triggered after listing transitions to `ACTIVE`:

```python
seller = listing.seller
if not seller.channel_id or not seller.channel_autopost_enabled:
    return
if seller.channel_autopost_categories and category(listing) not in seller.channel_autopost_categories:
    return

text = render_channel_card(listing, lang=seller.user.language)
photos = [InputMediaPhoto(...) for img in listing.images[:10]]
msg = await bot.send_media_group(seller.channel_id, photos[:1], caption=text, parse_mode="HTML")  # or send_photo if single
listing.channel_message_id = msg.message_id
```

### C. Edit / delete on status change

Hook on `Listing.status` transitions:

- `ACTIVE → SOLD`: edit caption to mark sold (`channel_on_sold=EDIT_SOLD`), or delete (`DELETE`), or no-op (`KEEP`).
- `ACTIVE → INACTIVE / EXPIRED / REJECTED`: delete the channel post.
- `PATCH /listings/{id}` with material change (price, title, photos): re-post or edit caption.

### D. Periodic re-circulation (Phase 2 polish)

Daily celery beat job: for each active seller channel, pick top 3 listings by views/contacts in the last 7 days that haven't been re-posted in the last 14 days; re-post (i.e. send fresh message) and update `channel_message_id`.

## Behaviour & invariants

- **Idempotency** — every channel write checks `listing.channel_message_id` first; if present, edits instead of re-sending.
- **Rate limits** — Telegram allows 30 messages per second per bot, but channels are stricter (~1 per second per channel). Use a per-channel queue or `aiogram` retry.
- **Failure → soft-fail** — channel write failures don't roll back listing publish. Log + mark `channel_admin_verified_at = NULL` if we get permission errors so the seller is prompted to re-verify.
- **Privacy** — never leak the seller's phone in the channel post; the post links to UcharMarket where the contact form is mediated.

## Acceptance criteria

- Seller can add bot as admin and verify channel from cabinet.
- Publishing a listing produces one channel post; editing produces a caption edit; selling either edits or deletes per seller preference.
- Disabling channel autopost stops further writes immediately.
- Re-imported / dedup'd listings don't double-post.

## Open questions

- Multi-channel per seller (some sellers have 2-3 niche channels)? Defer until we see demand.
- How to handle photos > 10? Telegram caps `send_media_group` at 10. Truncate; mention "ещё N фото на UcharMarket" in caption.
- Russian-only vs. RU/UZ — render channel cards in `seller.user.language` for consistency with their audience.
