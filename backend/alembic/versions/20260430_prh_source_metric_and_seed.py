"""PR-H — Block A V2.0 (A8) — source_metric table + seed parser_sources.

Adds:
1. ``source_metric`` table with one row per (source × calendar-day) plus
   counters: listings_found, listings_extracted, listings_failed,
   dupes_filtered, ai_failed.
2. Unique index ``uq_source_metric_day`` on ``(source_id, day)``.
3. Conditional seed: if ``parser_sources`` is empty, insert the 14
   channels currently configured in ``telegram-ai/crawler/schemas/real_estate.yaml``.

Additive, idempotent. Re-runnable safely.

Revision ID: prh_source_metric_and_seed
Revises: prg_view_event_anon_and_status
Create Date: 2026-04-30
"""

from alembic import op

revision = "prh_source_metric_and_seed"
down_revision = "prg_view_event_anon_and_status"
branch_labels = None
depends_on = None


_SEED_CHANNELS = [
    # (identifier, display name, priority)
    ("baburieltor", "BaburieLtor (Tashkent sale)", "low"),
    ("realtor_alii", "Realtor Alii (Sergeli, mixed UZ/RU)", "high"),
    ("Kvartira_doma_Tashkent", "Kvartira Doma Tashkent (center)", "medium"),
    ("Nedvijimosss", "Nedvijimosss (Mirzo Ulugbek)", "low"),
    ("realtor_yunusov", "Realtor Yunusov (center, structured)", "high"),
    ("grandestate2019", "Grandestate2019 (premium center)", "high"),
    ("RealestTash", "RealestTash (Tashkent)", "medium"),
    ("vitrinanedvizhimosti", "Vitrina Nedvizhimosti (rentals)", "medium"),
    ("arentash", "AreNTash (rentals)", "high"),
    ("UyCharxiy9", "UyCharxiy9 (Kokand/Fergana, largest)", "high"),
    ("Imkonuyjoysavdoo", "Imkon Uyjoy Savdoo (Fergana)", "low"),
    ("ANDIJON_UYJOY", "Andijon Uyjoy (Andijan)", "medium"),
    ("NAMANGAN_UYJOY_BOZORI", "Namangan Uyjoy Bozori", "low"),
    ("testReiltor", "Test Realtor", "low"),
]


def upgrade() -> None:
    # ── 1. source_metric table ────────────────────────────────────────
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'source_metric'
            ) THEN
                CREATE TABLE source_metric (
                    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    source_id           UUID NOT NULL REFERENCES parser_sources(id) ON DELETE CASCADE,
                    day                 TIMESTAMP NOT NULL,
                    listings_found      INTEGER NOT NULL DEFAULT 0,
                    listings_extracted  INTEGER NOT NULL DEFAULT 0,
                    listings_failed     INTEGER NOT NULL DEFAULT 0,
                    dupes_filtered      INTEGER NOT NULL DEFAULT 0,
                    ai_failed           INTEGER NOT NULL DEFAULT 0,
                    created_at          TIMESTAMP NOT NULL DEFAULT now(),
                    updated_at          TIMESTAMP NOT NULL DEFAULT now()
                );

                CREATE UNIQUE INDEX uq_source_metric_day
                    ON source_metric (source_id, day);

                CREATE INDEX idx_source_metric_source_id
                    ON source_metric (source_id);

                CREATE INDEX idx_source_metric_day
                    ON source_metric (day);
            END IF;
        END $$;
        """
    )

    # ── 2. Seed parser_sources if empty ───────────────────────────────
    # We use a plain SELECT count check; the inner INSERTs use
    # ON CONFLICT DO NOTHING (identifier is UNIQUE) so re-runs are safe.
    for identifier, display_name, priority in _SEED_CHANNELS:
        op.execute(
            f"""
            INSERT INTO parser_sources (
                id, type, identifier, name,
                is_active, priority, parse_interval_minutes, config,
                total_parsed, total_errors, consecutive_errors,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(), 'telegram_channel', '{identifier}',
                $${display_name}$$,
                TRUE, '{priority}', 60, '{{}}'::jsonb,
                0, 0, 0,
                now(), now()
            WHERE NOT EXISTS (
                SELECT 1 FROM parser_sources WHERE identifier = '{identifier}'
            );
            """
        )

    # OLX is also a parser source, conceptually. Seed once.
    op.execute(
        """
        INSERT INTO parser_sources (
            id, type, identifier, name,
            is_active, priority, parse_interval_minutes, config,
            total_parsed, total_errors, consecutive_errors,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(), 'website', 'olx.uz', 'OLX.uz',
            TRUE, 'high', 30, '{}'::jsonb,
            0, 0, 0,
            now(), now()
        WHERE NOT EXISTS (
            SELECT 1 FROM parser_sources WHERE identifier = 'olx.uz'
        );
        """
    )


def downgrade() -> None:
    # Seed rows are deliberately left in place on downgrade — they're
    # safe to keep and removing them would orphan related metrics.
    op.execute(
        """
        DROP TABLE IF EXISTS source_metric CASCADE;
        """
    )
