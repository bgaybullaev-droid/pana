# D4 — Bot autoposting with auto-update and auto-delete

**Difficulty**: hard (6–8 days)
**Spec source**: Block D V2.0, §D4
**Dependencies**: C3 (subscription model, exists), D3 ("Подробнее"
deep links), F1 (AI text exists in 3 locales)
**Blocks**: nothing — this is anchor functionality for Cabinet
subscription (99 000 sum/mo)

---

## Goal

A seller plugs the bot into their Telegram channel as admin. From then
on, every new listing in their UcharMarket cabinet auto-posts to the
channel. Edits go via a "Update post" button (with a 48h media-edit
modal when needed). Sold listings get the "ПРОДАНО" overlay; Paused /
Archived / Deleted listings are removed from the channel.

---

## Existing infrastructure to reuse

(see TRUTH_LAYER_AUDIT.md §4 for citations)

- aiogram 3.x — supports `bot.send_message`, `bot.send_photo`,
  `bot.edit_message_text`, `bot.edit_message_media`,
  `bot.delete_message` for channels where the bot is admin.
- `Listing.ai_description_ru/uz/uz_cyrl` — `db/models.py:508-510`.
- `Subscription` + `SubscriptionType.CABINET` — `db/models.py:865-920`.
- `Seller.telegram_username`, `User.language` for the post language.
- D3 deep-link builder (D3.10) — used for the "Подробнее" inline button
  on each channel post.

---

## What changes

### Data model — new

```sql
-- Seller's own outbound channel (different from the inbound source_channel)
ALTER TABLE sellers ADD COLUMN autopost_channel_username VARCHAR(64) NULL;
ALTER TABLE sellers ADD COLUMN autopost_channel_id BIGINT NULL;
ALTER TABLE sellers ADD COLUMN autopost_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE sellers ADD COLUMN autopost_verified_at TIMESTAMPTZ NULL;

-- Per-listing channel post tracking (one row per post)
CREATE TABLE bot_channel_posts (
  id UUID PRIMARY KEY,
  listing_id UUID REFERENCES listings(id) ON DELETE CASCADE,
  seller_id UUID REFERENCES sellers(id),
  channel_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,                  -- the Telegram message id
  posted_at TIMESTAMPTZ DEFAULT NOW(),
  last_edited_at TIMESTAMPTZ NULL,
  last_listing_version INT NOT NULL,           -- snapshot for staleness check
  status VARCHAR(16) DEFAULT 'live'            -- live / sold_marker / deleted
);
CREATE UNIQUE INDEX ON bot_channel_posts (listing_id, channel_id);
CREATE INDEX ON bot_channel_posts (seller_id, status);
```

`last_listing_version` is an integer that increments on every
listing-mutating event. The cabinet shows "post stale" when
`listing.version > post.last_listing_version`.

### Backend services

1. **Channel verification flow** — new endpoints under
   `backend/app/api/v1/autopost.py`:
   - `POST /seller/autopost/connect` — body `{"channel": "@..."}`.
     Server resolves username → channel_id via `bot.get_chat`, verifies
     bot can post (calls `bot.get_chat_member(channel_id, bot.id)` and
     checks `status="administrator"` and `can_post_messages=True`).
     Writes `Seller.autopost_channel_*` and pings a tiny verification
     post (sticker or 1-line message) that is then deleted. Returns
     `{"status": "verified"}`.
   - `POST /seller/autopost/disconnect`.
   - `GET /seller/autopost/posts` — paginated list of
     `bot_channel_posts` for the cabinet's history view.

2. **`active_subscription_check(user_id, type)`** helper —
   `backend/app/services/subscriptions.py` (new). Reads from
   `Subscription` table, returns bool. **Phase 1**: returns True
   for all sellers (per spec: "during test period — available to
   everyone"). **Post-test**: real check.

3. **Autopost service** — `backend/app/services/autopost.py` (new):
   ```python
   async def autopost_listing(listing: Listing) -> Optional[BotChannelPost]:
       """Called on listing.status → ACTIVE transition.
       Skip if seller.autopost_enabled is False, or seller did not opt-in
       on this specific listing (form checkbox), or no active subscription."""

   async def update_post(post: BotChannelPost) -> EditResult: ...
   async def delete_post(post: BotChannelPost) -> None: ...
   async def mark_sold(post: BotChannelPost) -> None:
       """Edit text to '🔴 ПРОДАНО / SOTILDI / СОТИЛДИ\n\n<original>',
       preserve media."""
   ```

4. **Post body builder** — `_render_channel_post(listing, lang)`:
   - Caption: AI description on seller's language + structured params
     line + price.
   - Media: main photo only (Telegram caption limit ~1024 chars).
   - Inline keyboard: single button "Подробнее →" with URL =
     D3 listing deep link.
   - Footer line: "Через @ucharmarket_bot" (small footer).

5. **Listing-event hooks**:
   - **Listing → ACTIVE** (after AI generation succeeds): enqueue
     `autopost_listing(listing)` if seller opted in.
   - **Listing edited**: do NOT auto-update. Increment
     `listing.version` so the cabinet shows staleness badge.
   - **"Update post" button** (manual trigger): cabinet calls
     `POST /seller/autopost/posts/<post_id>/update`. Server fetches
     fresh listing data, attempts to edit via `bot.edit_message_caption`
     (or `edit_message_media` if photo changed). Returns
     `{"result": "updated"}` or `{"result": "media_too_old",
     "needs_recreate": true}` to trigger the 48h modal in the cabinet.
   - **Listing → SOLD or RENTED**: call `mark_sold(post)`.
   - **Listing → PAUSED, ARCHIVED, or DELETED**: call `delete_post(post)`.

6. **48h cutoff handling** in `update_post()`:
   - If `now - post.posted_at < 48h`: try `edit_message_media` (photo+text)
     or `edit_message_caption` (text-only when photo unchanged).
   - If `now - post.posted_at >= 48h` **and** photo changed:
     - Return `media_too_old` to caller. Cabinet shows modal with
       3 options (Update text only / Delete and repost / Cancel).
   - If `now - post.posted_at >= 48h` and only text changed: edit text
     without modal.

7. **Retry queue** for transient Telegram failures — leverage existing
   Celery infra. Backoff: 1m / 5m / 30m / give up + admin notification.

8. **Bot-kicked-from-channel detection**: on any
   `TelegramForbiddenError` / `BadRequest "not enough rights"`, set
   `Seller.autopost_verified_at = NULL` and surface a cabinet warning.
   No further auto-publishes attempted until the seller re-verifies.

### Frontend (seller cabinet)

1. **"Autoposting" section** in seller cabinet
   (`frontend/src/modules/seller/pages/autoposting/` — new module):
   - Empty state: "Connect your Telegram channel to auto-publish your
     listings."
   - Connected state: channel name + status + Disconnect button +
     "Stale posts" counter + table of recent posts.

2. **Listing-create form checkbox**: "Опубликовать в моём канале"
   (default: checked when `Seller.autopost_enabled`; can be toggled
   per listing).

3. **"Pôst stale" badge** on `My Listings` cards when
   `listing.version > post.last_listing_version`.

4. **"Update post in channel" button** on the listing card and on the
   Autoposting section row.

5. **48h-cutoff modal** with 3 buttons:
   - "Обновить только текст" → `POST .../update?force_text_only=true`
   - "Удалить старый пост и опубликовать новый" → DELETE old + new
     `autopost_listing`
   - "Отмена"

---

## OPEN QUESTIONS

1. **Phase-1 access**: spec confirms "available to all during test
   period, then subscribers only." When does that transition? Need
   a feature-flag mechanism in `active_subscription_check`.

2. **Per-listing opt-in default**: spec says checkbox default-on.
   Confirm: also default-on for **claimed crawled listings** that
   the seller didn't manually create? Recommend: off by default for
   claimed, because the seller may not want a flood of channel posts
   on day 1.

3. **Multi-channel per seller**: spec says "one channel per account in
   MVP." Schema reflects this. Confirm.

4. **Footer wording / inclusion**: "Через @ucharmarket_bot" — is the
   bot username locked? Recommend a setting in `core/config.py`.

5. **Sold-marker on private channel**: if the channel is private and
   the bot is admin, edit/delete still works via channel_id. Confirm
   product wants the bot to keep working on private channels (yes per
   spec).

6. **What if seller deletes the post manually from their channel?**
   Next update attempt will return `MessageToEditNotFound`. Mark
   `bot_channel_posts.status = "deleted"` and stop trying. Do not
   auto-repost (the seller chose to remove it).

7. **Rate-limit policy for mass updates**: if seller updates 30
   listings, that's 30 edits. Spec says "use a queue with pauses."
   What pace? Telegram allows ~30 msgs/sec but channel edits can hit
   stricter limits. Recommend 1 edit/sec serial queue per channel.

8. **Disconnect cleanup**: when a seller disconnects, what happens to
   the existing posts in their channel? Three options: (a) leave
   them, do nothing — most polite; (b) delete all — destructive; (c)
   stop tracking but leave posts. Recommend (c).

---

## Acceptance criteria

- Seller can connect their channel via "add bot as admin" flow and
  verify in 1 click.
- New ACTIVE listing auto-posts to the channel in seller's language
  with photo, structured params, AI description, "Подробнее" button,
  "Через @ucharmarket_bot" footer.
- Per-listing opt-out via form checkbox works.
- Listing edits show a "stale" badge but do not auto-update the post.
- "Update post" button works; for media changes within 48h, edit
  succeeds; past 48h with media change, modal offers 3 options.
- SOLD/RENTED transitions overlay "ПРОДАНО/СОТИЛДИ/СОТИЛДИ" in
  seller's language, preserving the post.
- PAUSED/ARCHIVED/DELETED transitions remove the post.
- Bot kicked from channel → graceful warning, no retries until
  re-verified.
- Cabinet shows post history with timestamps and statuses.
- Idempotent: `bot_channel_posts (listing_id, channel_id)` unique.
- Phase-1: all sellers can use it. Post-test: only Cabinet
  subscribers.

---

## Risks

- **Race**: seller flips listing ACTIVE→PAUSED while autopost task is
  still in queue. Solution: at task start, re-read listing.status,
  bail if no longer ACTIVE.
- **Channel deleted by seller**: Telegram returns `ChatNotFound`.
  Mark `autopost_enabled = false`, notify seller in cabinet.
- **Photo URL expiry**: AI-pipeline stores photos on R2/S3. Telegram
  fetches the URL when sending. If we delete the photo, the post can
  break on edit. Solution: keep photos for life of the listing.
- **Caption length**: Telegram caption max is 1024 chars. AI text +
  params + footer can exceed. Truncate AI text with ellipsis; full
  text via "Подробнее".
- **Spam-flag from channel subscribers**: if a seller's channel
  audience reports the bot — Telegram may auto-restrict. Out of our
  control; cabinet shows "bot restricted" status if applicable.
