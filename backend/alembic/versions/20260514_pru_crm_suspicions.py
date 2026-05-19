"""pru_crm_suspicions — phase-2 CRM tables + account suspicion / link tables.

Two feature areas in one atomic migration:

* CRM: ``seller_clients`` + ``seller_client_listings`` — a lightweight
  pipeline-style client tracker the seller uses to manage their own
  prospect list and pin specific listings to each prospect.
* Suspicions: ``account_suspicion`` + ``account_link`` — admin-side
  workflow tables for the nightly duplicate-account detection signals
  (phone collision, similar names, …). One open suspicion per pair is
  kept idempotent by the daily worker; admin decisions either merge
  (creates an ``account_link``) or dismiss the suspicion.

Revision ID: pru_crm_suspicions
Revises: prq_block_f_exports
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "pru_crm_suspicions"
down_revision: str | None = "prq_block_f_exports"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    # ── CRM ────────────────────────────────────────────────────────────
    op.create_table(
        "seller_clients",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "seller_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("sellers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "pipeline_stage",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'new'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_seller_clients_seller_stage",
        "seller_clients",
        ["seller_id", "pipeline_stage"],
    )

    op.create_table(
        "seller_client_listings",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "client_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("seller_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "listing_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "added_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "client_id",
            "listing_id",
            name="uq_seller_client_listing_pair",
        ),
    )

    # ── Suspicions ────────────────────────────────────────────────────
    op.create_table(
        "account_suspicion",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "primary_user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("signal_kind", sa.String(48), nullable=False),
        sa.Column(
            "evidence",
            sa.dialects.postgresql.JSONB,
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column(
            "reviewed_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_account_suspicion_status_created",
        "account_suspicion",
        ["status", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_account_suspicion_primary_user",
        "account_suspicion",
        ["primary_user_id"],
    )

    op.create_table(
        "account_link",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id_a",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id_b",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relation", sa.String(32), nullable=False),
        sa.Column(
            "decided_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("decided_at", sa.DateTime, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "user_id_a", "user_id_b", name="uq_account_link_pair"
        ),
        sa.CheckConstraint(
            "user_id_a < user_id_b", name="ck_account_link_normalised_pair"
        ),
    )


def downgrade() -> None:
    op.drop_table("account_link")
    op.drop_index(
        "ix_account_suspicion_primary_user", table_name="account_suspicion"
    )
    op.drop_index(
        "ix_account_suspicion_status_created", table_name="account_suspicion"
    )
    op.drop_table("account_suspicion")
    op.drop_table("seller_client_listings")
    op.drop_index("ix_seller_clients_seller_stage", table_name="seller_clients")
    op.drop_table("seller_clients")
