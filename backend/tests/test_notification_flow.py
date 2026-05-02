"""
End-to-end verification of the new listing notification system.

Runs against the real database with isolated test data that is
cleaned up at the end (regardless of pass/fail).
"""

import asyncio
import sys
from datetime import date
from datetime import time as dt_time
from uuid import uuid4

import redis
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

# -- bootstrap app imports --
sys.path.insert(0, "/mnt/projects/data/siddiq/ucharmarket-new/backend")

from app.core.config import settings
from app.db.models import (
    Currency,
    Listing,
    ListingStatus,
    ListingType,
    ModerationStatus,
    Notification,
    NotificationPreferences,
    NotificationType,
    PropertyType,
    Seller,
    SourceType,
    User,
    UserRole,
)
from app.workers.tasks.notifications import (
    _build_notification_texts,
    _get_session,
    _send_new_listing_notifications,
)

# Track IDs for cleanup
_cleanup_ids: dict[str, list] = {
    "users": [],
    "sellers": [],
    "listings": [],
    "notification_preferences": [],
    "notifications": [],
}

PASS = 0
FAIL = 0


def report(name: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    tag = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{tag}] {name}{suffix}")


async def setup_test_data(db):
    """Create isolated test users, sellers, listings, and preferences."""

    # --- Buyer A: has matching preferences, push ON, has telegram_id ---
    buyer_a = User(
        id=uuid4(),
        first_name="TestBuyerA",
        language="ru",
        role=UserRole.USER,
        telegram_id=999000001,
        phone="+998990000001",
    )
    db.add(buyer_a)
    _cleanup_ids["users"].append(buyer_a.id)

    prefs_a = NotificationPreferences(
        user_id=buyer_a.id,
        enabled=True,
        time_start=dt_time(9, 0),
        time_end=dt_time(21, 0),
        daily_limit=10,
        listing_types=["sell"],
        property_types=["apartment"],
        districts=[],  # empty = match all
        rooms=[],  # empty = match all
    )
    db.add(prefs_a)
    _cleanup_ids["notification_preferences"].append(prefs_a.id)

    # --- Buyer B: push OFF, has telegram_id ---
    buyer_b = User(
        id=uuid4(),
        first_name="TestBuyerB",
        language="uz",
        role=UserRole.USER,
        telegram_id=999000002,
        phone="+998990000002",
    )
    db.add(buyer_b)
    _cleanup_ids["users"].append(buyer_b.id)

    prefs_b = NotificationPreferences(
        user_id=buyer_b.id,
        enabled=False,
        time_start=dt_time(9, 0),
        time_end=dt_time(21, 0),
        daily_limit=10,
        listing_types=["sell"],
        property_types=[],
        districts=[],
        rooms=[],
    )
    db.add(prefs_b)
    _cleanup_ids["notification_preferences"].append(prefs_b.id)

    # --- Buyer C: non-matching preferences (wants rent, not sell) ---
    buyer_c = User(
        id=uuid4(),
        first_name="TestBuyerC",
        language="ru",
        role=UserRole.USER,
        phone="+998990000003",
    )
    db.add(buyer_c)
    _cleanup_ids["users"].append(buyer_c.id)

    prefs_c = NotificationPreferences(
        user_id=buyer_c.id,
        enabled=True,
        time_start=dt_time(9, 0),
        time_end=dt_time(21, 0),
        daily_limit=10,
        listing_types=["rent"],
        property_types=[],
        districts=[],
        rooms=[],
    )
    db.add(prefs_c)
    _cleanup_ids["notification_preferences"].append(prefs_c.id)

    # --- Buyer D: daily_limit=1, push ON ---
    buyer_d = User(
        id=uuid4(),
        first_name="TestBuyerD",
        language="ru",
        role=UserRole.USER,
        telegram_id=999000004,
        phone="+998990000004",
    )
    db.add(buyer_d)
    _cleanup_ids["users"].append(buyer_d.id)

    prefs_d = NotificationPreferences(
        user_id=buyer_d.id,
        enabled=True,
        time_start=dt_time(9, 0),
        time_end=dt_time(21, 0),
        daily_limit=1,
        listing_types=["sell"],
        property_types=[],
        districts=[],
        rooms=[],
    )
    db.add(prefs_d)
    _cleanup_ids["notification_preferences"].append(prefs_d.id)

    # --- Buyer E: no NotificationPreferences row ---
    buyer_e = User(
        id=uuid4(),
        first_name="TestBuyerE",
        language="ru",
        role=UserRole.USER,
        phone="+998990000005",
    )
    db.add(buyer_e)
    _cleanup_ids["users"].append(buyer_e.id)

    # --- Seller (owner of listings) ---
    seller_user = User(
        id=uuid4(),
        first_name="TestSeller",
        language="ru",
        role=UserRole.SELLER,
        telegram_id=999000099,
        phone="+998990000099",
    )
    db.add(seller_user)
    _cleanup_ids["users"].append(seller_user.id)

    seller = Seller(
        id=uuid4(),
        user_id=seller_user.id,
        phone="+998900000000",
    )
    db.add(seller)
    _cleanup_ids["sellers"].append(seller.id)

    # Also give the seller matching preferences (to test owner exclusion)
    prefs_seller = NotificationPreferences(
        user_id=seller_user.id,
        enabled=True,
        time_start=dt_time(9, 0),
        time_end=dt_time(21, 0),
        daily_limit=10,
        listing_types=["sell"],
        property_types=[],
        districts=[],
        rooms=[],
    )
    db.add(prefs_seller)
    _cleanup_ids["notification_preferences"].append(prefs_seller.id)

    await db.flush()

    # --- Listing 1: approved+active, type=sell, apartment ---
    listing_1 = Listing(
        id=uuid4(),
        seller_id=seller.id,
        type=ListingType.SELL,
        property_type=PropertyType.APARTMENT,
        price=75000,
        currency=Currency.USD,
        district="test_district",
        rooms=3,
        status=ListingStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
        source_type=SourceType.MANUAL,
    )
    db.add(listing_1)
    _cleanup_ids["listings"].append(listing_1.id)

    # --- Listing 2: PENDING (not approved) ---
    listing_2 = Listing(
        id=uuid4(),
        seller_id=seller.id,
        type=ListingType.SELL,
        property_type=PropertyType.APARTMENT,
        price=80000,
        currency=Currency.USD,
        district="test_district",
        rooms=2,
        status=ListingStatus.ACTIVE,
        moderation_status=ModerationStatus.PENDING,
        source_type=SourceType.MANUAL,
    )
    db.add(listing_2)
    _cleanup_ids["listings"].append(listing_2.id)

    # --- Listing 3: approved but PAUSED ---
    listing_3 = Listing(
        id=uuid4(),
        seller_id=seller.id,
        type=ListingType.SELL,
        property_type=PropertyType.APARTMENT,
        price=90000,
        currency=Currency.USD,
        district="test_district",
        rooms=4,
        status=ListingStatus.PAUSED,
        moderation_status=ModerationStatus.APPROVED,
        source_type=SourceType.MANUAL,
    )
    db.add(listing_3)
    _cleanup_ids["listings"].append(listing_3.id)

    await db.commit()

    return {
        "buyer_a": buyer_a,
        "buyer_b": buyer_b,
        "buyer_c": buyer_c,
        "buyer_d": buyer_d,
        "buyer_e": buyer_e,
        "seller_user": seller_user,
        "seller": seller,
        "listing_1": listing_1,
        "listing_2": listing_2,
        "listing_3": listing_3,
    }


async def cleanup(db):
    """Remove all test data."""
    for nid in _cleanup_ids["notifications"]:
        await db.execute(delete(Notification).where(Notification.id == nid))
    # Also clean any notifications created for test users
    for uid in _cleanup_ids["users"]:
        await db.execute(delete(Notification).where(Notification.user_id == uid))
    for pid in _cleanup_ids["notification_preferences"]:
        await db.execute(
            delete(NotificationPreferences).where(NotificationPreferences.id == pid)
        )
    for lid in _cleanup_ids["listings"]:
        await db.execute(delete(Listing).where(Listing.id == lid))
    for sid in _cleanup_ids["sellers"]:
        await db.execute(delete(Seller).where(Seller.id == sid))
    for uid in _cleanup_ids["users"]:
        await db.execute(delete(User).where(User.id == uid))
    await db.commit()

    # Clean Redis test keys
    r = redis.from_url(settings.redis_connection_url, decode_responses=True)
    for uid in _cleanup_ids["users"]:
        key = f"notif_daily:{uid}:{date.today().isoformat()}"
        r.delete(key)
    r.close()


async def get_notifications_for_user(db, user_id, listing_id=None):
    """Get NEW_LISTING notifications for a user."""
    q = select(Notification).where(
        Notification.user_id == user_id,
        Notification.type == NotificationType.NEW_LISTING,
    )
    if listing_id:
        q = q.where(Notification.listing_id == listing_id)
    result = await db.execute(q)
    return result.scalars().all()


# =========================================================================
# TEST FUNCTIONS
# =========================================================================


async def test_approved_active_listing(data):
    """TEST 1: Approved+active listing creates notifications for matching users."""
    print("\n[TEST 1] Approved+active listing — matching users get notifications")

    result = await _send_new_listing_notifications(str(data["listing_1"].id))

    # Buyer A (matching, push ON) + Buyer B (matching, push OFF) + Buyer D (matching, limit=1)
    # Buyer C (non-matching) + Buyer E (no prefs) + Seller (owner) = excluded
    report(
        "notifications_sent >= 3",
        result["notifications_sent"] >= 3,
        f"got {result['notifications_sent']}",
    )

    # Verify in-app notifications exist
    async with _get_session() as db:
        notifs_a = await get_notifications_for_user(
            db, data["buyer_a"].id, data["listing_1"].id
        )
        report("Buyer A got in-app notification", len(notifs_a) == 1)

        notifs_b = await get_notifications_for_user(
            db, data["buyer_b"].id, data["listing_1"].id
        )
        report("Buyer B got in-app notification (push OFF)", len(notifs_b) == 1)

        notifs_d = await get_notifications_for_user(
            db, data["buyer_d"].id, data["listing_1"].id
        )
        report("Buyer D got in-app notification", len(notifs_d) == 1)

    return result


async def test_non_matching_excluded(data):
    """TEST 2: Non-matching preferences → no notification."""
    print("\n[TEST 2] Non-matching preferences excluded")

    async with _get_session() as db:
        notifs_c = await get_notifications_for_user(
            db, data["buyer_c"].id, data["listing_1"].id
        )
        report(
            "Buyer C (wants rent) got 0 notifications",
            len(notifs_c) == 0,
            f"got {len(notifs_c)}",
        )


async def test_no_prefs_excluded(data):
    """TEST 3: User with no NotificationPreferences row → no notification."""
    print("\n[TEST 3] No NotificationPreferences row → excluded")

    async with _get_session() as db:
        notifs_e = await get_notifications_for_user(
            db, data["buyer_e"].id, data["listing_1"].id
        )
        report(
            "Buyer E (no prefs) got 0 notifications",
            len(notifs_e) == 0,
            f"got {len(notifs_e)}",
        )


async def test_owner_excluded(data):
    """TEST 4: Listing owner is excluded even if preferences match."""
    print("\n[TEST 4] Owner exclusion")

    async with _get_session() as db:
        notifs_seller = await get_notifications_for_user(
            db, data["seller_user"].id, data["listing_1"].id
        )
        report(
            "Seller (owner) got 0 notifications",
            len(notifs_seller) == 0,
            f"got {len(notifs_seller)}",
        )


async def test_telegram_gating(first_result):
    """TEST 5: Telegram sent only when push enabled AND telegram_id exists."""
    print("\n[TEST 5] Telegram dispatch gating")

    # The result from test 1 tells us how many Telegram tasks were dispatched.
    # Buyer A: push ON + telegram_id → YES
    # Buyer B: push OFF + telegram_id → NO
    # Buyer D: push ON + telegram_id → YES (within limit on first run)
    # Seller: excluded
    # Buyer C: non-matching
    # Buyer E: no prefs
    # So telegram_sent should be 2 (A + D)
    report(
        "telegram_sent == 2",
        first_result["telegram_sent"] == 2,
        f"got {first_result['telegram_sent']}",
    )


async def test_pending_listing_blocked(data):
    """TEST 6: Pending listing → no notifications."""
    print("\n[TEST 6] Pending listing blocked")

    result = await _send_new_listing_notifications(str(data["listing_2"].id))
    report(
        "notifications_sent == 0 for PENDING listing",
        result["notifications_sent"] == 0,
        f"got {result['notifications_sent']}",
    )


async def test_paused_listing_blocked(data):
    """TEST 7: Paused listing → no notifications."""
    print("\n[TEST 7] Paused listing (approved but inactive) blocked")

    result = await _send_new_listing_notifications(str(data["listing_3"].id))
    report(
        "notifications_sent == 0 for PAUSED listing",
        result["notifications_sent"] == 0,
        f"got {result['notifications_sent']}",
    )


async def test_nonexistent_listing():
    """TEST 8: Nonexistent listing ID → graceful return."""
    print("\n[TEST 8] Nonexistent listing ID")

    fake_id = str(uuid4())
    result = await _send_new_listing_notifications(fake_id)
    report("notifications_sent == 0", result["notifications_sent"] == 0)


async def test_idempotency(data):
    """TEST 9: Running task twice for same listing → no duplicate notifications."""
    print("\n[TEST 9] Idempotency — no duplicates on re-run")

    # Run again for listing_1 (already ran in test 1)
    result = await _send_new_listing_notifications(str(data["listing_1"].id))
    report(
        "Second run: notifications_sent == 0",
        result["notifications_sent"] == 0,
        f"got {result['notifications_sent']}",
    )

    # Verify counts in DB
    async with _get_session() as db:
        notifs_a = await get_notifications_for_user(
            db, data["buyer_a"].id, data["listing_1"].id
        )
        report(
            "Buyer A still has exactly 1 notification",
            len(notifs_a) == 1,
            f"got {len(notifs_a)}",
        )

        notifs_b = await get_notifications_for_user(
            db, data["buyer_b"].id, data["listing_1"].id
        )
        report(
            "Buyer B still has exactly 1 notification",
            len(notifs_b) == 1,
            f"got {len(notifs_b)}",
        )


async def test_daily_limit(data):
    """TEST 10: Daily Telegram limit — in-app always created, Telegram gated."""
    print("\n[TEST 10] Daily Telegram limit")

    # Buyer D has daily_limit=1. After test 1, they already got 1 Telegram.
    # Create a second listing and run notifications for it.
    async with _get_session() as db:
        listing_4 = Listing(
            id=uuid4(),
            seller_id=data["seller"].id,
            type=ListingType.SELL,
            property_type=PropertyType.APARTMENT,
            price=60000,
            currency=Currency.USD,
            district="test_district_2",
            rooms=2,
            status=ListingStatus.ACTIVE,
            moderation_status=ModerationStatus.APPROVED,
            source_type=SourceType.MANUAL,
        )
        db.add(listing_4)
        _cleanup_ids["listings"].append(listing_4.id)
        await db.commit()

    result = await _send_new_listing_notifications(str(listing_4.id))

    # Buyer D should get in-app but NOT Telegram (limit=1, already sent 1)
    async with _get_session() as db:
        notifs_d = await get_notifications_for_user(
            db, data["buyer_d"].id, listing_4.id
        )
        report(
            "Buyer D got in-app for 2nd listing",
            len(notifs_d) == 1,
            f"got {len(notifs_d)}",
        )

    # Check Redis counter for Buyer D
    r = redis.from_url(settings.redis_connection_url, decode_responses=True)
    daily_key = f"notif_daily:{data['buyer_d'].id}:{date.today().isoformat()}"
    count = r.get(daily_key)
    r.close()
    # Counter should still be 1 (not incremented for the 2nd listing since it was over limit)
    report(
        "Buyer D Redis daily count == 1 (not incremented)", count == "1", f"got {count}"
    )


async def test_notification_content(data):
    """TEST 11: Notification content is correct."""
    print("\n[TEST 11] Notification content verification")

    async with _get_session() as db:
        result = await db.execute(
            select(Listing).where(Listing.id == data["listing_1"].id)
        )
        listing = result.scalar_one()

        # Russian text
        texts_ru = _build_notification_texts(listing, "ru")
        report("RU title", texts_ru["title"] == "Новое объявление")
        report("RU message contains property type", "Квартира" in texts_ru["message"])
        report("RU message contains rooms", "3 комн." in texts_ru["message"])
        report("RU telegram contains emoji", "🏠" in texts_ru["telegram_message"])

        # Uzbek text
        texts_uz = _build_notification_texts(listing, "uz")
        report("UZ title", texts_uz["title"] == "Yangi e'lon")
        report("UZ message contains property type", "Kvartira" in texts_uz["message"])

        # Check Buyer B got Uzbek content (language=uz)
        notifs_b = await get_notifications_for_user(
            db, data["buyer_b"].id, data["listing_1"].id
        )
        if notifs_b:
            report(
                "Buyer B (lang=uz) got Uzbek title",
                notifs_b[0].title == "Yangi e'lon",
                f"got: {notifs_b[0].title}",
            )


async def test_push_disabled_no_telegram(first_result, data):
    """TEST 12: Verify push disabled user gets in-app but not Telegram."""
    print("\n[TEST 12] Push disabled — in-app YES, Telegram NO")

    async with _get_session() as db:
        # Buyer B has enabled=False
        notifs = await get_notifications_for_user(
            db, data["buyer_b"].id, data["listing_1"].id
        )
        report("Buyer B has in-app notification", len(notifs) == 1)

    # Telegram count from test 1 excludes Buyer B
    # Buyer A and D get Telegram = 2 total. If B also got it, it would be 3.
    report(
        "Total telegram_sent excludes push-OFF user",
        first_result["telegram_sent"] == 2,
        f"got {first_result['telegram_sent']}",
    )


# =========================================================================
# MAIN
# =========================================================================


async def main():
    global PASS, FAIL

    print("=" * 60)
    print("NOTIFICATION SYSTEM — END-TO-END VERIFICATION")
    print("=" * 60)

    async with _get_session() as db:
        data = await setup_test_data(db)

    try:
        first_result = await test_approved_active_listing(data)
        await test_non_matching_excluded(data)
        await test_no_prefs_excluded(data)
        await test_owner_excluded(data)
        await test_telegram_gating(first_result)
        await test_pending_listing_blocked(data)
        await test_paused_listing_blocked(data)
        await test_nonexistent_listing()
        await test_idempotency(data)
        await test_daily_limit(data)
        await test_notification_content(data)
        await test_push_disabled_no_telegram(first_result, data)
    finally:
        print("\n--- Cleaning up test data ---")
        async with _get_session() as db:
            await cleanup(db)
        print("Cleanup complete.")

    print("\n" + "=" * 60)
    print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print("=" * 60)

    return FAIL == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
