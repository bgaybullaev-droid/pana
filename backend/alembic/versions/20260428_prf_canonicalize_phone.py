"""PR-F — canonicalise users.phone and sellers.phone to E.164 format.

Walks both tables, converts each phone to ``+998XXXXXXXXX`` form via
``app.utils.phone.normalize_phone_e164``. When two rows resolve to the
same canonical phone, the row with the most recent activity wins
(``users.last_login_at`` / ``sellers.updated_at``); the others lose
their phone (set to NULL) so the unique index stays valid going
forward.

Rollback is documented as no-op — original raw formats are not
recoverable post-canonicalisation; restore from backup if a true
rollback is ever needed.

Revision ID: prf_canonicalize_phone
Revises: pre_listing_view_event
Create Date: 2026-04-28
"""

from __future__ import annotations

import re
from typing import Optional

from alembic import op
from sqlalchemy import text

revision = "prf_canonicalize_phone"
down_revision = "pre_listing_view_event"
branch_labels = None
depends_on = None


def _canonicalize(raw: Optional[str]) -> Optional[str]:
    """Mirror of ``normalize_phone_e164`` — kept inline to avoid import
    coupling between Alembic and app code paths.
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 9:
        return f"+998{digits}"
    if len(digits) == 12 and digits.startswith("998"):
        return f"+{digits}"
    if len(digits) >= 9:
        return f"+998{digits[-9:]}"
    return None


def _canonicalize_table(conn, table: str, freshness_col: str) -> None:
    """For each row with phone IS NOT NULL: compute canonical form;
    keep one row per canonical, null the others."""
    rows = conn.execute(
        text(
            f"SELECT id, phone, {freshness_col} AS freshness "
            f"FROM {table} WHERE phone IS NOT NULL"
        )
    ).fetchall()

    invalid: list = []
    groups: dict = {}
    for row in rows:
        canon = _canonicalize(row.phone)
        if canon is None:
            invalid.append(row.id)
        else:
            groups.setdefault(canon, []).append((row.id, row.freshness, row.phone))

    losers: list = []
    winners: list = []  # (id, canon)
    for canon, members in groups.items():
        # Sort newest first; None freshness sorts last.
        members.sort(key=lambda m: (m[1] is None, m[1] or ""), reverse=False)
        # Above: "is None" True last when reverse=False; we want newest first
        # so re-sort properly:
        members.sort(key=lambda m: (m[1] is not None, m[1] or ""), reverse=True)
        winner = members[0]
        # If the winner's stored phone is already canonical and unique, skip.
        if winner[2] != canon:
            winners.append((winner[0], canon))
        for member in members[1:]:
            losers.append(member[0])

    if invalid:
        conn.execute(
            text(f"UPDATE {table} SET phone = NULL WHERE id = ANY(:ids)"),
            {"ids": invalid},
        )
    if losers:
        conn.execute(
            text(f"UPDATE {table} SET phone = NULL WHERE id = ANY(:ids)"),
            {"ids": losers},
        )
    for id_, canon in winners:
        conn.execute(
            text(f"UPDATE {table} SET phone = :canon WHERE id = :id"),
            {"canon": canon, "id": id_},
        )


def upgrade() -> None:
    conn = op.get_bind()
    _canonicalize_table(conn, "users", "last_login_at")
    _canonicalize_table(conn, "sellers", "updated_at")


def downgrade() -> None:
    # Original raw formats are unrecoverable post-canonicalisation.
    pass
