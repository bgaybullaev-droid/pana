"""Seed the active prompt_templates row for Block F F5.

Idempotent: skips if a row with the same kind already has is_active=true.

Run after `alembic upgrade head` and before restarting the worker so
the worker's first invocation reads from the registry instead of
falling back to the inline prompt.

Usage:
    cd backend
    venv/bin/python scripts/seed_block_f_prompts.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running from anywhere under backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import select  # noqa: E402

from app.core.prompts import LISTING_DESCRIPTION_PROMPT  # noqa: E402
from app.db.database import async_session_maker  # noqa: E402
from app.db.models import PromptTemplate  # noqa: E402


# Shared with the worker fallback and the activating migration. The
# migration is what flips production onto this body; this seed only fires
# on a fresh DB with no active prompt yet.
LISTING_DESCRIPTION_BODY = LISTING_DESCRIPTION_PROMPT


async def main() -> int:
    async with async_session_maker() as db:
        existing = await db.execute(
            select(PromptTemplate).where(
                PromptTemplate.kind == "listing_description",
                PromptTemplate.is_active.is_(True),
            )
        )
        if existing.scalar_one_or_none() is not None:
            print("SKIP — active prompt for kind=listing_description already exists")
            return 0

        all_versions = await db.execute(
            select(PromptTemplate).where(
                PromptTemplate.kind == "listing_description"
            )
        )
        next_v = max((r.version for r in all_versions.scalars().all()), default=0) + 1

        row = PromptTemplate(
            kind="listing_description",
            version=next_v,
            body=LISTING_DESCRIPTION_BODY,
            model_hint="gpt-4o-mini",
            is_active=True,
            notes=(
                "Block F — long-form selling copy (4-7 sentences, "
                "~400-800 chars/locale). Mirrors app/core/prompts."
            ),
        )
        db.add(row)
        await db.commit()
        print(
            f"SEEDED — kind=listing_description version={next_v} "
            f"model_hint=gpt-4o-mini is_active=true"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
