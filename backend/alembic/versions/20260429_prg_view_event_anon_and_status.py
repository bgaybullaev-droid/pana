"""PR-G — Block A V2.0 schema changes.

Three additive parts:

1. ``listing_view_event`` gains ``anon_id`` (varchar 64, nullable). The
   partial unique dedup index is rebuilt to span the disjunction
   ``(coalesce(user_id::text, anon_id), listing_id, event_type, day)`` so
   anonymous viewers (cookie-only) are deduped per day too.

2. Extend the ``listingstatus`` enum with three new values used by the F1
   AI-generation pipeline: ``PENDING_GENERATION``, ``GENERATION_FAILED``,
   ``UNCONFIRMED``. ListingStatus column maps via Python enum *names*
   (uppercase), matching the existing DB enum values.

3. ``listings`` gains the AI-description triplet ``ai_description_ru``,
   ``ai_description_uz``, ``ai_description_uz_cyrl`` (all TEXT, nullable),
   plus an ``ai_generation_attempted_at`` timestamp for retry bookkeeping.

4. ``notificationtype`` gains ``crawled_match`` (lowercase — Notification
   serialises via ``values_callable``). ``Notification.expires_at`` added.
   Unique partial index ``uq_notification_crawled_match`` enforces one
   crawled-match notification per (user, listing).

Postgres requires ``ALTER TYPE … ADD VALUE`` to commit before the new
value can be used. The enum additions are wrapped in
``op.get_context().autocommit_block()`` so they commit immediately;
later DDL in this migration can then reference the new values.

Additive, idempotent.

Revision ID: prg_view_event_anon_and_status
Revises: prf_canonicalize_phone
Create Date: 2026-04-29
"""

from alembic import op

revision = "prg_view_event_anon_and_status"
down_revision = "prf_canonicalize_phone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── (0) Enum value additions, in autocommit so they're visible to the
    #        rest of this migration's DDL. ─────────────────────────────
    with op.get_context().autocommit_block():
        # ListingStatus uses Python enum NAMES (uppercase) in the DB.
        op.execute(
            "ALTER TYPE listingstatus ADD VALUE IF NOT EXISTS 'PENDING_GENERATION'"
        )
        op.execute(
            "ALTER TYPE listingstatus ADD VALUE IF NOT EXISTS 'GENERATION_FAILED'"
        )
        op.execute(
            "ALTER TYPE listingstatus ADD VALUE IF NOT EXISTS 'UNCONFIRMED'"
        )
        # NotificationType uses values_callable → lowercase in the DB.
        op.execute(
            """
            DO $$ BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationtype') THEN
                    EXECUTE 'ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS ''crawled_match''';
                END IF;
            END $$;
            """
        )

    # ── (1) listing_view_event: anon_id + rebuilt dedup index ─────────
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listing_view_event' AND column_name = 'anon_id'
            ) THEN
                ALTER TABLE listing_view_event
                    ADD COLUMN anon_id VARCHAR(64) NULL;
            END IF;
        END $$;
        """
    )

    op.execute(
        """
        DROP INDEX IF EXISTS uq_listing_view_event_dedup;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_listing_view_event_dedup_v2
            ON listing_view_event (
                COALESCE(user_id::text, anon_id),
                listing_id,
                event_type,
                (date(viewed_at))
            )
            WHERE COALESCE(user_id::text, anon_id) IS NOT NULL;
        """
    )

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_listing_view_event_anon_time
            ON listing_view_event (anon_id, viewed_at DESC)
            WHERE anon_id IS NOT NULL;
        """
    )

    # ── (2) listings: AI description columns + retry timestamp ────────
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'ai_description_ru'
            ) THEN
                ALTER TABLE listings
                    ADD COLUMN ai_description_ru TEXT NULL,
                    ADD COLUMN ai_description_uz TEXT NULL,
                    ADD COLUMN ai_description_uz_cyrl TEXT NULL,
                    ADD COLUMN ai_generation_attempted_at TIMESTAMP NULL;
            END IF;
        END $$;
        """
    )

    # ── (3) notifications: expires_at + crawled_match unique index ────
    # The 'crawled_match' enum value was added in step (0) under autocommit,
    # so it's now visible to this transaction.
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name = 'notifications'
            ) THEN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'notifications' AND column_name = 'expires_at'
                ) THEN
                    ALTER TABLE notifications ADD COLUMN expires_at TIMESTAMP NULL;
                END IF;

                CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_crawled_match
                    ON notifications (user_id, listing_id, type)
                    WHERE type = 'crawled_match';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Enum-value additions are not reversible in Postgres without a
    # disruptive type swap; treat schema additions as one-way for safety.
    op.execute(
        """
        ALTER TABLE listings DROP COLUMN IF EXISTS ai_description_ru;
        ALTER TABLE listings DROP COLUMN IF EXISTS ai_description_uz;
        ALTER TABLE listings DROP COLUMN IF EXISTS ai_description_uz_cyrl;
        ALTER TABLE listings DROP COLUMN IF EXISTS ai_generation_attempted_at;
        ALTER TABLE listing_view_event DROP COLUMN IF EXISTS anon_id;
        DROP INDEX IF EXISTS uq_listing_view_event_dedup_v2;
        DROP INDEX IF EXISTS idx_listing_view_event_anon_time;
        DROP INDEX IF EXISTS uq_notification_crawled_match;
        ALTER TABLE notifications DROP COLUMN IF EXISTS expires_at;
        """
    )
