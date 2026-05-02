"""Sprint 2 — Rent foundation + sale finance flags.

Adds 11 columns plus indexes per Master Technical Blueprint §1.2 + §4.1:

    Rent (T-002, T-003):
        rent_period, deposit, utilities_incl, min_rent_months,
        allowed_students, allowed_pets, rent_payment
    Sale finance (T-004):
        mortgage_ok, installment_ok, halol_ok
    Deed (T-005):
        deed_type

Check constraints enforce enum values for rent_period, min_rent_months, and
deed_type. rent_payment element validation happens at the Pydantic boundary
(Postgres has no clean per-element CHECK for ARRAY columns without triggers).

The three sale-finance booleans default to false so existing rows backfill
implicitly; on a < 100k-row table this is a metadata-only update in PG 11+.

Indexes use Alembic's declarative form with postgresql_where for partials.
On production, ops runbook calls for running the equivalent CREATE INDEX
CONCURRENTLY statements manually BEFORE upgrade so the upgrade step itself
becomes a no-op marker (see sprint-2-technical-doc.md §1.1.2).

Revision ID: sprint2_rent_sale_finance
Revises: add_listing_phase2_fields
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision = "sprint2_rent_sale_finance"
down_revision = "add_listing_phase2_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── T-002: rent period ────────────────────────────────────────────
    op.add_column("listings", sa.Column("rent_period", sa.String(20), nullable=True))
    op.create_check_constraint(
        "ck_listings_rent_period_enum",
        "listings",
        "rent_period IS NULL OR rent_period IN ('long_term', 'daily')",
    )

    # ── T-003: rent details ───────────────────────────────────────────
    op.add_column("listings", sa.Column("deposit", sa.BigInteger(), nullable=True))
    op.create_check_constraint(
        "ck_listings_deposit_nonneg",
        "listings",
        "deposit IS NULL OR deposit >= 0",
    )

    op.add_column("listings", sa.Column("utilities_incl", sa.Boolean(), nullable=True))

    op.add_column("listings", sa.Column("min_rent_months", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_listings_min_rent_months_enum",
        "listings",
        "min_rent_months IS NULL OR min_rent_months IN (1, 3, 6, 12)",
    )

    op.add_column(
        "listings", sa.Column("allowed_students", sa.Boolean(), nullable=True)
    )
    op.add_column("listings", sa.Column("allowed_pets", sa.Boolean(), nullable=True))

    op.add_column(
        "listings",
        sa.Column("rent_payment", ARRAY(sa.String(20)), nullable=True),
    )

    # ── T-004: sale finance flags ─────────────────────────────────────
    op.add_column(
        "listings",
        sa.Column(
            "mortgage_ok",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "listings",
        sa.Column(
            "installment_ok",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "listings",
        sa.Column(
            "halol_ok",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # ── T-005: deed type ──────────────────────────────────────────────
    op.add_column("listings", sa.Column("deed_type", sa.String(20), nullable=True))
    op.create_check_constraint(
        "ck_listings_deed_type_enum",
        "listings",
        "deed_type IS NULL OR deed_type IN ('cadastre', 'order', 'other')",
    )

    # ── T-022 Sprint 2 indexes ────────────────────────────────────────
    op.create_index(
        "idx_listings_rent_period",
        "listings",
        ["rent_period"],
        # Enum labels in PG are upper-case (SQLAlchemy Enum uses Python enum
        # NAMES, not values, when values_callable is not supplied).
        postgresql_where=sa.text("type = 'RENT'"),
    )
    op.create_index(
        "idx_listings_mortgage_ok",
        "listings",
        ["mortgage_ok"],
        postgresql_where=sa.text("mortgage_ok = true"),
    )
    op.create_index(
        "idx_listings_installment_ok",
        "listings",
        ["installment_ok"],
        postgresql_where=sa.text("installment_ok = true"),
    )
    op.create_index(
        "idx_listings_halol_ok",
        "listings",
        ["halol_ok"],
        postgresql_where=sa.text("halol_ok = true"),
    )
    op.create_index(
        "idx_listings_main_feed",
        "listings",
        ["property_type", "type", "status", "moderation_status", "created_at"],
        postgresql_where=sa.text(
            "status = 'ACTIVE' AND moderation_status = 'APPROVED'"
        ),
    )
    op.create_index(
        "idx_listings_amenities_gin",
        "listings",
        ["amenities"],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_listings_nearby_amenities_gin",
        "listings",
        ["nearby_amenities"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("idx_listings_nearby_amenities_gin", table_name="listings")
    op.drop_index("idx_listings_amenities_gin", table_name="listings")
    op.drop_index("idx_listings_main_feed", table_name="listings")
    op.drop_index("idx_listings_halol_ok", table_name="listings")
    op.drop_index("idx_listings_installment_ok", table_name="listings")
    op.drop_index("idx_listings_mortgage_ok", table_name="listings")
    op.drop_index("idx_listings_rent_period", table_name="listings")

    op.drop_constraint("ck_listings_deed_type_enum", "listings", type_="check")
    op.drop_column("listings", "deed_type")

    op.drop_column("listings", "halol_ok")
    op.drop_column("listings", "installment_ok")
    op.drop_column("listings", "mortgage_ok")

    op.drop_column("listings", "rent_payment")
    op.drop_column("listings", "allowed_pets")
    op.drop_column("listings", "allowed_students")
    op.drop_constraint("ck_listings_min_rent_months_enum", "listings", type_="check")
    op.drop_column("listings", "min_rent_months")
    op.drop_column("listings", "utilities_incl")
    op.drop_constraint("ck_listings_deposit_nonneg", "listings", type_="check")
    op.drop_column("listings", "deposit")

    op.drop_constraint("ck_listings_rent_period_enum", "listings", type_="check")
    op.drop_column("listings", "rent_period")
