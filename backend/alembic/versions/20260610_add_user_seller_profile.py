"""Add seller_type and seller_telegram to users table.

Users can now store their seller classification (owner/realtor/developer) and
Telegram contact once in their profile rather than repeating it on every listing.
The listing form reads these values and pre-populates without showing a UI field.

Both columns are nullable VARCHAR — existing rows keep NULL which maps to
undefined on the frontend (no value selected / no telegram set).

Revision ID: add_user_seller_profile
Revises: merge_loc_prompt_moderation
Create Date: 2026-06-10
"""

from alembic import op

revision = "add_user_seller_profile"
down_revision = "merge_loc_prompt_moderation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'users'
                  AND column_name = 'seller_type'
            ) THEN
                ALTER TABLE users ADD COLUMN seller_type VARCHAR(20);
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'users'
                  AND column_name = 'seller_telegram'
            ) THEN
                ALTER TABLE users ADD COLUMN seller_telegram VARCHAR(100);
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'users'
                  AND column_name = 'seller_telegram'
            ) THEN
                ALTER TABLE users DROP COLUMN seller_telegram;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'users'
                  AND column_name = 'seller_type'
            ) THEN
                ALTER TABLE users DROP COLUMN seller_type;
            END IF;
        END$$;
        """
    )
