# A4 — Push notification on new found listing

**Status:** NOT STARTED — bot infra exists; the entire found-listing notification pipeline is greenfield.
**Complexity:** HARD — five interlocking pieces (match-on-import trigger, inline-callback handlers, F1-completion gate, 7-day expiry job, group-batching). Each piece is bounded, but they integrate across crawler, F1 queue, bot, fanout, and the cabinet's Found page.
**Block-A V2.0 ref:** A4 (Section "A4. Уведомление риелтору о новых найденных объявлениях", Ф-107).
**Vision-doc refs:** §3.2, §5.1 ("Уровень 1"), Ф-107.
**V1 cross-ref:** [`../../not-started/medium/F107-seller-claim-notification.md`](../../not-started/medium/F107-seller-claim-notification.md) — V1 spec sketched a simpler version (in-app + plain-text TG); V2.0 demands AI-text card + inline buttons + expiry. **Subsumes the V1 spec.**
**Dependencies:** [A1](../medium/A1-claim-reject-v2.md), [A7](./A7-parser-f1-trigger.md) (F1 must complete before push). Hard-blocked by F1 for the AI-text payload — without F1 the push card carries the realtor's raw original text, which is the exact behaviour V2.0 outlaws.

## What's done

- **Bot infra** — `backend/app/bot/main.py:44-58` instantiates aiogram with Redis FSM storage, dispatcher, router registration. Singleton bot instance accessed via `get_bot_instance()`.
- **Notification service** — `backend/app/bot/notifications.py`. `send_custom_notification()` already handles `TelegramForbiddenError` (line 119-120) and returns `False` on bot-blocked.
- **Existing claim flow endpoints** ([A1](../medium/A1-claim-reject-v2.md)) — `POST /listings/claim-{olx,telegram}/{id}` and `POST /listings/reject-crawled/{source}/{id}` accept the same operations the bot inline buttons need to call. The bot can reuse these endpoints internally; no new business logic on the claim/reject side.
- **Phone-suffix matcher** — `backend/app/services/seller_crawled_listings.py` (the function `seller_crawled_listings_for_user`) does the last-9-digits match used by the cabinet Found list. The same matcher seeds this notification trigger.

## What's missing

1. **No "new crawled listing → match phone → enqueue notification" trigger.** Crawler imports land in `backend/app/api/v1/crawler_import.py` (or the equivalent service); after insert, no code looks up registered sellers by phone and enqueues a notification.
2. **No `CRAWLED_MATCH` notification type.** `NotificationType` enum in `backend/app/db/models.py` lacks the value. Migration must `ALTER TYPE notificationtype ADD VALUE 'crawled_match'`.
3. **No inline-callback handlers.** `@router.callback_query(F.data.startswith("claim_crawled:"))` and `…("reject_crawled:")` do not exist in `backend/app/bot/handlers.py`. Without them, taps on the inline buttons return `Bad Request: query is too old` after Telegram's 1-hour callback expiry.
4. **No F1-completion gate.** Spec: send the push only after AI generation succeeds (or with a base template if F1 fails permanently). F1 itself is missing ([A7](./A7-parser-f1-trigger.md)); the trigger function must check the F1 status.
5. **No 7-day expiry job.** Spec: if no reaction within 7 days, the inline-keyboard message is edited to "this listing is waiting for you in Found" and the listing routes back to the cabinet for offline handling. No Celery beat task does this.
6. **No group-batching.** A single crawl pass can find 5+ listings for one realtor. Spec: collapse into one push ("we found 5 of your new listings, open Found"), not 5 separate pushes. No batcher exists.
7. **Bot-blocked fallback path is incomplete.** `send_custom_notification` returns `False` on block, but no caller currently routes the listing to /found explicitly. The fallback semantics (bot blocked ⇒ skip push, listing still appears in /found) only work because /found is pull-based — but if /found ever switches to push-only, this breaks. Make the fallback explicit.
8. **No idempotency on (seller × listing × type)** — re-imports of the same listing must not re-spam.

## Path to DONE

Order: stand up the trigger and the data model first; layer batching, expiry, and the F1 gate after.

### Step 1 — data model

- Migration: `ALTER TYPE notificationtype ADD VALUE 'crawled_match'`.
- Migration: add unique partial index on `notifications (user_id, listing_id, type)` for `type='crawled_match'`. Prevents re-spam.
- Optional column: `Notification.expires_at TIMESTAMP NULL` — used by the 7-day expiry job. Reusable across notification types.

### Step 2 — match-on-import trigger

`backend/app/workers/tasks/notifications.py` — new `notify_sellers_of_crawled_listing(listing_id)` Celery task. Invoked at the end of crawler import, *after* the F1-status check (Step 5). Pseudocode:

```python
@celery_app.task
def notify_sellers_of_crawled_listing(listing_id: str) -> dict:
    return asyncio.run(_notify_sellers_of_crawled_listing(listing_id))

async def _notify_sellers_of_crawled_listing(listing_id):
    async with _get_session() as db:
        listing = await _load_listing_with_ai(db, listing_id)
        if listing.status != ListingStatus.PENDING_GENERATION and listing.ai_description is None:
            return {"skipped": "no_ai_description"}
        if listing.seller_id:  # already claimed somewhere
            return {"skipped": "already_claimed"}
        suffix = normalize_phone(listing.phone)
        sellers = await db.execute(
            select(User).where(
                func.right(User.phone, 9) == suffix,
                User.role.in_([UserRole.SELLER, UserRole.ADMIN]),
                User.deleted_at.is_(None),
            )
        )
        for user in sellers.scalars():
            # Reuse the existing notification fanout — it handles dedup, in-app + Telegram dispatch
            await create_notification(db, user, listing, NotificationType.CRAWLED_MATCH)
```

### Step 3 — inline keyboard

In `backend/app/bot/notifications.py`, the Telegram-side dispatch for `CRAWLED_MATCH` builds:

```python
keyboard = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text=t("bot.crawled.claim", lang), callback_data=f"claim_crawled:{listing.id}"),
    InlineKeyboardButton(text=t("bot.crawled.reject", lang), callback_data=f"reject_crawled:{listing.id}"),
]])
```

Card body uses `listing.ai_description_<lang>`, never `listing.raw_text`.

### Step 4 — callback handlers

`backend/app/bot/handlers.py`:

```python
@router.callback_query(F.data.startswith("claim_crawled:"))
async def handle_claim_crawled(call: CallbackQuery):
    listing_id = call.data.split(":")[1]
    # Reuse the existing claim service (same code path as /listings/claim-…)
    result = await claim_listing_for_user(call.from_user.id, listing_id)
    await call.message.edit_text(
        text=t("bot.crawled.confirmedFooter", ...),
        reply_markup=open_in_app_keyboard(listing_id),
    )
```

Race rule: if the listing was already claimed via the cabinet, `claim_listing_for_user` returns the existing master-record id; the bot edits the message to "уже подтверждено в кабинете".

### Step 5 — F1-completion gate

The trigger from Step 2 enqueues only after F1 completes. Two implementation options:
- **Sync in F1**: when F1 finishes for a listing, it calls `notify_sellers_of_crawled_listing.delay(listing_id)`. Cleaner; recommended.
- **Async tick**: a Celery beat job sweeps `Listing.status='ready_for_notification'` rows. Acceptable fallback if F1 chain hooks are awkward.

If F1 ends in `generation_failed`, the trigger fires with a base template description (per spec edge case).

### Step 6 — 7-day expiry

Celery beat job daily: select notifications where `type='crawled_match' AND expires_at <= now() AND not_acknowledged`. For each: edit the bot message to "this listing is waiting for you in Found", strip the inline keyboard, mark the notification expired. Listing remains in /found via the standard pull endpoint — no extra write needed.

### Step 7 — group-batching

When a crawl pass produces ≥ 2 listings for the same seller within a short window (say 5 minutes), the trigger should group:

```
"Мы нашли 5 ваших новых объявлений" + [Open Found] button
```

Implementation: instead of calling `send_telegram_notification` per listing, the trigger queues into Redis (`pending_crawled_match:{user_id}`) with a 5-minute debounce; a follow-up task drains the bucket and emits one message. Inline claim/reject is not offered when batched (forces the user into the cabinet); fewer than the threshold (1-2 listings) gets per-listing inline buttons.

### Step 8 — bot-blocked fallback

In the trigger task, if `send_custom_notification` returns `False`: log + mark the notification with `delivery_status='bot_blocked'`, do nothing else (the listing is still in /found via the standard pull path; nothing to "fall back" to in code).

## Behaviour & invariants

- **AI text only.** Push card body comes from `Listing.ai_description_<lang>`. Raw realtor text never reaches B2B push surfaces.
- **One notification per (seller × listing × type)** — DB-enforced unique index.
- **Already-claimed listings ⇒ no notification.** `seller_id IS NOT NULL` short-circuits.
- **Disabled types honoured** — existing notification preferences gate (similar to other types).
- **Daily limit** shared with other notification types (existing fanout).
- **Time-of-day window does NOT apply** — these are seller-business notifications; Telegram client-side quiet hours are the user's responsibility.
- **Race with cabinet** — cabinet action wins. Bot inline button on a listing already claimed via cabinet: edits to "уже подтверждено в кабинете".
- **Idempotent re-imports** — second import of the same Telegram message_id (or OLX listing_id) does not re-notify.
- **Multi-source dedup** — the same listing appearing in OLX + 3 Telegram channels yields one notification (the dedup logic in [A7](./A7-parser-f1-trigger.md) collapses them upstream).

## Acceptance criteria

- New crawled listing whose phone matches a registered seller ⇒ within ~5 minutes of capture (after F1), the seller gets one in-app notification + one Telegram message with two inline buttons.
- Push card body is AI-generated text in the seller's language.
- Tapping "Это моё" in the bot creates the master-record (same data path as web claim) and edits the bot message to "Подтверждено. Открыть в кабинете".
- Tapping "Не моё" sets `rejected_by_seller_id` and edits the message to "Отклонено".
- Re-importing the same Telegram message_id ⇒ no duplicate notification.
- Bot blocked ⇒ no error in logs, listing still appears in cabinet `/found` via the standard pull endpoint.
- 7-day-old un-acted notification ⇒ message edited to "ждёт вас в Found", inline keyboard stripped.
- Crawl pass producing ≥ 2 listings for one seller within 5 min ⇒ one batched message ("we found N new listings"), no inline buttons, button to open Found.
- F1 failure permanent ⇒ push fires with base template description (e.g. "3-комн квартира в Чиланзаре, 65 м²").
- Match-transparency log line per delivery: `crawled-match notify user=… listing=… reason=phone_suffix_match status=delivered|bot_blocked|skipped_already_claimed`.

## References

- `backend/app/bot/main.py:44-58` — bot init.
- `backend/app/bot/notifications.py:119-120` — bot-blocked detection (extend).
- `backend/app/bot/handlers.py` — add `claim_crawled` / `reject_crawled` callback handlers.
- `backend/app/services/seller_crawled_listings.py` — phone-match query (reuse).
- `backend/app/api/v1/listings.py:2195, 2407, 2506` — claim/reject service to reuse from inline handlers.
- `backend/app/db/models.py:65-72` — `ListingStatus` enum (extended by [A7](./A7-parser-f1-trigger.md)).
- `backend/app/workers/celery_app.py:13-19` — task registration (add new task).
- [A1 medium](../medium/A1-claim-reject-v2.md) — service path that the inline handlers reuse.
- [A7 hard](./A7-parser-f1-trigger.md) — F1 generation pipeline (hard prerequisite).
- [V1 F107 spec](../../not-started/medium/F107-seller-claim-notification.md) — superseded by this V2.0 spec.
