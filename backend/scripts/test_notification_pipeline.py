"""
Diagnostic script to test the notification pipeline end-to-end.

Run from backend dir:
    python -m scripts.test_notification_pipeline

This does NOT send actual notifications — it just checks each step.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models import (
    User, Listing, ListingStatus, ModerationStatus,
    NotificationPreferences, UserPreferences, Notification, NotificationType,
)


async def main():
    engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        # Step 1: Check users
        users_result = await db.execute(
            select(User).where(User.deleted_at.is_(None))
        )
        users = users_result.scalars().all()
        print(f"\n{'='*60}")
        print(f"STEP 1: Users ({len(users)} total)")
        print(f"{'='*60}")
        for u in users:
            print(f"  - {u.first_name} (@{u.username}) | id={u.id} | tg_id={u.telegram_id} | lang={u.language}")

        # Step 2: Check UserPreferences
        up_result = await db.execute(select(UserPreferences))
        user_prefs = up_result.scalars().all()
        print(f"\n{'='*60}")
        print(f"STEP 2: UserPreferences ({len(user_prefs)} records)")
        print(f"{'='*60}")
        for up in user_prefs:
            user = next((u for u in users if u.id == up.user_id), None)
            name = f"{user.first_name} (@{user.username})" if user else "unknown"
            print(f"  - {name}")
            print(f"    districts={up.districts}, types={up.property_types}, listing_types={up.listing_types}")
            print(f"    price={up.price_min}-{up.price_max}, rooms={up.rooms}")

        # Step 3: Check NotificationPreferences (THIS IS THE CRITICAL ONE)
        np_result = await db.execute(select(NotificationPreferences))
        notif_prefs = np_result.scalars().all()
        print(f"\n{'='*60}")
        print(f"STEP 3: NotificationPreferences ({len(notif_prefs)} records)")
        print(f"{'='*60}")
        if not notif_prefs:
            print("  *** PROBLEM: No NotificationPreferences records exist! ***")
            print("  *** The notification matching query will find ZERO users ***")
            print("  *** User must save preferences AFTER the code fix is deployed ***")
        for np in notif_prefs:
            user = next((u for u in users if u.id == np.user_id), None)
            name = f"{user.first_name} (@{user.username})" if user else "unknown"
            print(f"  - {name} | enabled={np.enabled}")
            print(f"    districts={np.districts}, types={np.property_types}, listing_types={np.listing_types}")
            print(f"    price={np.price_min}-{np.price_max}, rooms={np.rooms}")

        # Step 4: Check recent listings
        listings_result = await db.execute(
            select(Listing)
            .where(Listing.deleted_at.is_(None))
            .options(selectinload(Listing.seller))
            .order_by(Listing.created_at.desc())
            .limit(5)
        )
        listings = listings_result.scalars().all()
        print(f"\n{'='*60}")
        print(f"STEP 4: Recent Listings (latest 5)")
        print(f"{'='*60}")
        for l in listings:
            seller_name = f"seller_id={l.seller_id}" if l.seller_id else "no seller"
            print(f"  - {l.title or 'no title'} | id={l.id}")
            print(f"    status={l.status.value}, moderation={l.moderation_status.value}, {seller_name}")
            print(f"    type={l.type.value}, property={l.property_type.value}, district={l.district}")
            print(f"    price={l.price}, rooms={l.rooms}, currency={l.currency.value}")

        # Step 5: Simulate matching for the most recent listing
        if listings:
            latest = listings[0]
            print(f"\n{'='*60}")
            print(f"STEP 5: Simulating notification match for listing '{latest.title}'")
            print(f"{'='*60}")

            if latest.moderation_status != ModerationStatus.APPROVED:
                print(f"  *** BLOCKED: moderation_status={latest.moderation_status.value} (need APPROVED) ***")
            if latest.status != ListingStatus.ACTIVE:
                print(f"  *** BLOCKED: status={latest.status.value} (need ACTIVE) ***")

            from sqlalchemy import or_, literal
            NP = NotificationPreferences
            query = (
                select(NP, User)
                .join(User, NP.user_id == User.id)
                .where(User.deleted_at.is_(None))
            )

            # Exclude owner
            if latest.seller and latest.seller.user_id:
                query = query.where(User.id != latest.seller.user_id)
                print(f"  Excluding owner: user_id={latest.seller.user_id}")

            result = await db.execute(query)
            all_np_users = result.all()
            print(f"  NotificationPreferences users (excl. owner): {len(all_np_users)}")

            for np, user in all_np_users:
                print(f"\n  Checking user: {user.first_name} (@{user.username})")
                match = True

                # listing_types
                if np.listing_types and len(np.listing_types) > 0:
                    if latest.type.value not in np.listing_types:
                        print(f"    MISMATCH listing_type: listing={latest.type.value}, pref={np.listing_types}")
                        match = False
                    else:
                        print(f"    OK listing_type: {latest.type.value} in {np.listing_types}")
                else:
                    print(f"    OK listing_type: empty filter (matches all)")

                # property_types
                if np.property_types and len(np.property_types) > 0:
                    if latest.property_type.value not in np.property_types:
                        print(f"    MISMATCH property_type: listing={latest.property_type.value}, pref={np.property_types}")
                        match = False
                    else:
                        print(f"    OK property_type: {latest.property_type.value} in {np.property_types}")
                else:
                    print(f"    OK property_type: empty filter (matches all)")

                # districts
                if np.districts and len(np.districts) > 0 and latest.district:
                    if latest.district not in np.districts:
                        print(f"    MISMATCH district: listing={latest.district}, pref={np.districts}")
                        match = False
                    else:
                        print(f"    OK district: {latest.district} in {np.districts}")
                else:
                    print(f"    OK district: empty filter or no district")

                # price
                if np.price_min is not None and latest.price is not None:
                    if latest.price < np.price_min:
                        print(f"    MISMATCH price_min: listing={latest.price} < pref={np.price_min}")
                        match = False
                    else:
                        print(f"    OK price_min: {latest.price} >= {np.price_min}")
                if np.price_max is not None and latest.price is not None:
                    if latest.price > np.price_max:
                        print(f"    MISMATCH price_max: listing={latest.price} > pref={np.price_max}")
                        match = False
                    else:
                        print(f"    OK price_max: {latest.price} <= {np.price_max}")

                # rooms
                if np.rooms and len(np.rooms) > 0 and latest.rooms is not None:
                    if latest.rooms not in np.rooms:
                        print(f"    MISMATCH rooms: listing={latest.rooms}, pref={np.rooms}")
                        match = False
                    else:
                        print(f"    OK rooms: {latest.rooms} in {np.rooms}")
                else:
                    print(f"    OK rooms: empty filter or no rooms")

                print(f"    --> {'MATCH' if match else 'NO MATCH'}")

        # Step 6: Check existing notifications
        notif_count = await db.execute(select(func.count()).select_from(Notification))
        total_notifs = notif_count.scalar()
        print(f"\n{'='*60}")
        print(f"STEP 6: Notifications in DB ({total_notifs} total)")
        print(f"{'='*60}")
        if total_notifs > 0:
            recent_notifs = await db.execute(
                select(Notification).order_by(Notification.created_at.desc()).limit(5)
            )
            for n in recent_notifs.scalars().all():
                user = next((u for u in users if u.id == n.user_id), None)
                name = f"{user.first_name}" if user else "unknown"
                print(f"  - [{n.type.value}] to {name}: {n.title} | {n.message}")
                print(f"    listing_id={n.listing_id}, read={n.read}, created={n.created_at}")
        else:
            print("  No notifications in the database at all.")

        # Step 7: Check Redis/Celery connectivity
        print(f"\n{'='*60}")
        print(f"STEP 7: Config check")
        print(f"{'='*60}")
        print(f"  Database URL: {settings.async_database_url[:50]}...")
        print(f"  Redis URL: {settings.redis_connection_url}")
        print(f"  Celery broker: {settings.celery_broker_url}")
        print(f"  Telegram bot token: {'SET' if settings.telegram_bot_token else 'NOT SET'}")
        print(f"  Auto-approve listings: {settings.auto_approve_listings}")

    await engine.dispose()
    print(f"\n{'='*60}")
    print("DONE")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
