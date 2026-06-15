"""Block D (FU3) — admin-managed bot rate-limit settings.

Creates the singleton ``bot_rate_limit_settings`` table that backs the
Telegram bot's per-user rate limiter (in-chat search + Inline Mode) and the
editable "too many requests" message. One row, pinned to ``id = 1`` by a CHECK
constraint, seeded with sensible defaults (search 10/60s, inline 30/60s) and
the message pre-filled in all three bot locales.

Idempotent: ``CREATE TABLE IF NOT EXISTS`` + ``ON CONFLICT DO NOTHING`` on the
seed, so re-runs are safe.

Revision ID: bot_rate_limit_settings
Revises: autopost_last_result
Create Date: 2026-06-15
"""

from alembic import op

revision = "bot_rate_limit_settings"
down_revision = "autopost_last_result"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_rate_limit_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            search_enabled BOOLEAN NOT NULL DEFAULT true,
            search_limit INTEGER NOT NULL DEFAULT 10,
            search_window_sec INTEGER NOT NULL DEFAULT 60,
            inline_enabled BOOLEAN NOT NULL DEFAULT true,
            inline_limit INTEGER NOT NULL DEFAULT 30,
            inline_window_sec INTEGER NOT NULL DEFAULT 60,
            limit_message_ru TEXT NOT NULL,
            limit_message_uz TEXT NOT NULL,
            limit_message_uz_cyrl TEXT NOT NULL,
            updated_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_by_admin_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            CONSTRAINT ck_bot_rate_limit_singleton CHECK (id = 1)
        );
        """
    )
    # Seed the single config row with defaults in all three bot locales.
    # Apostrophes in the Uzbek-Latin text are SQL-escaped by doubling.
    op.execute(
        """
        INSERT INTO bot_rate_limit_settings (
            id, limit_message_ru, limit_message_uz, limit_message_uz_cyrl
        ) VALUES (
            1,
            'Слишком много запросов. Подождите минуту и попробуйте снова.',
            'So''rovlar juda ko''p. Bir daqiqa kuting va qayta urinib ko''ring.',
            'Сўровлар жуда кўп. Бир дақиқа кутиб, қайта уриниб кўринг.'
        )
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bot_rate_limit_settings;")
