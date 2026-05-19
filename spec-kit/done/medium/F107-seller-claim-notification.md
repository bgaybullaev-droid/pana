# 06 — Ф-107 — Seller Claim Notification

**Status:** DONE
**Complexity:** MEDIUM — one celery task, one new enum value, one dedup constraint; cross-cutting integration with the existing fanout.
**Vision-doc refs:** Section 3.2, Section 5.1 ("Уровень 1"), Ф-107
**Why now:** Phase 1 critical — the strategic moment of the B2B onboarding. A seller registers, then within minutes/hours a Telegram message says "we just found your new listing on OLX, claim it in one tap" — that's the wow.

## Goal

When a crawler imports a new `Listing` whose phone matches a registered seller's phone, fire a Telegram message to that seller with the listing summary and a "Это моё" CTA that opens the Mini App's Found page (or, even better, the Found page deep-linked to that specific listing).

## Proposed data model

No new tables. Use existing `NotificationType` — add `CRAWLED_MATCH` enum value:

```python
class NotificationType(str, Enum):
    ...
    CRAWLED_MATCH = "crawled_match"
```

Migration: ALTER TYPE `notificationtype` ADD VALUE 'crawled_match'.

## Proposed background task

`backend/app/workers/tasks/notifications.py` — new function `notify_sellers_of_crawled_listing(listing_id)`:

```python
@celery_app.task
def notify_sellers_of_crawled_listing(listing_id: str) -> dict:
    return asyncio.run(_notify_sellers_of_crawled_listing(listing_id))

async def _notify_sellers_of_crawled_listing(listing_id):
    async with _get_session() as db:
        listing = await _load_listing(db, listing_id)
        if not listing.phone or listing.seller_id:
            return {"matched_count": 0}  # already claimed or no phone

        # Match by last-9-digits — same as claim flow
        suffix = normalize_phone(listing.phone)
        sellers = await db.execute(
            select(User).where(
                func.right(User.phone, 9) == suffix,
                User.role.in_([UserRole.SELLER, UserRole.ADMIN]),
                User.deleted_at.is_(None),
            )
        )
        for user in sellers.scalars():
            # In-app notification
            db.add(Notification(
                user_id=user.id,
                type=NotificationType.CRAWLED_MATCH,
                source="crawler",
                title=_CRAWL_TITLE[user.language],
                message=_CRAWL_MESSAGE[user.language].format(...),
                listing_id=listing_id,
            ))
            # Telegram with deep link to Found page
            if user.telegram_id:
                send_telegram_notification.delay(
                    user.telegram_id,
                    _CRAWL_TG_TEMPLATE[user.language].format(...),
                    "HTML",
                )
```

Triggered from `backend/app/api/v1/crawler_import.py` after each new `Listing` insert via `notify_sellers_of_crawled_listing.delay(listing_id)`.

## Proposed copy (RU)

- Title: `Мы нашли ваше объявление`
- Body: `{property_label} в {district} за {price}. Подтвердите — один тап, и оно будет на вашем профиле.`
- Telegram CTA: inline button `🔘 Это моё → откроется в приложении`.

## Behaviour & invariants

- **One notification per (seller × listing)** — enforce via DB unique on `(user_id, listing_id, type)` for `CRAWLED_MATCH`. Re-imports of the same listing don't re-spam.
- **Skip already-claimed listings** — `listing.seller_id IS NOT NULL` → skip.
- **Honour disabled types** — `if "crawled_match" in prefs.disabled_types: skip`.
- **Daily limit applies** — share counter with the existing notification stages.
- **Time window does NOT apply** — these are seller-business notifications, fire 24/7 (mirrors preferences-stage semantics).

## Acceptance criteria

- New listing imported with phone matching a seller → seller gets one in-app + one Telegram notification.
- Re-importing the same listing → no duplicate notification.
- Already-claimed listing → no notification.
- Tapping the Telegram CTA opens the Mini App on Found, scrolled to that listing.
- Match transparency log line per seller: `crawled-match notify user=… listing=… reason=match_phone_suffix`.
