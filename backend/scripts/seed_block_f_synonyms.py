"""Block F V2.0 F2 — seed synonym_entries with curated launch list.

Idempotent. Re-running adds new entries without duplicating existing
rows (composite unique index enforces dedup).

Usage:
    python -m backend.scripts.seed_block_f_synonyms
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running as a script: ``python backend/scripts/seed_block_f_synonyms.py``.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.database import async_session_maker
from app.db.models import SynonymEntry


# (parameter_key, parameter_value, surface_form, language, polarity)
_SEED: list[tuple[str, str | None, str, str, str]] = [
    # Air-conditioner
    ("air_conditioner", None, "кондиционер", "ru", "positive"),
    ("air_conditioner", None, "кондей", "ru", "positive"),
    ("air_conditioner", None, "сплит-система", "ru", "positive"),
    ("air_conditioner", None, "konditsioner", "uz", "positive"),
    ("air_conditioner", None, "kondisioner", "uz", "positive"),
    ("air_conditioner", None, "кондиционер", "uz_cyrl", "positive"),
    # Balcony
    ("balcony", None, "балкон", "ru", "positive"),
    ("balcony", None, "лоджия", "ru", "positive"),
    ("balcony", None, "balkon", "uz", "positive"),
    ("balcony", None, "балкон", "uz_cyrl", "positive"),
    # Elevator
    ("elevator", None, "лифт", "ru", "positive"),
    ("elevator", None, "лифты", "ru", "positive"),
    ("elevator", None, "lift", "uz", "positive"),
    ("elevator", None, "лифт", "uz_cyrl", "positive"),
    # Furniture (enum: with/without)
    ("furniture", "full", "мебель", "ru", "positive"),
    ("furniture", "full", "с мебелью", "ru", "positive"),
    ("furniture", "none", "без мебели", "ru", "positive"),
    ("furniture", "full", "mebel", "uz", "positive"),
    ("furniture", "full", "mebel bilan", "uz", "positive"),
    ("furniture", "none", "mebelsiz", "uz", "positive"),
    ("furniture", "full", "мебел билан", "uz_cyrl", "positive"),
    # Parking
    ("parking", None, "парковка", "ru", "positive"),
    ("parking", None, "своя парковка", "ru", "positive"),
    ("parking", None, "парковочное место", "ru", "positive"),
    ("parking", None, "parkovka", "uz", "positive"),
    ("parking", None, "to'xtash joyi", "uz", "positive"),
    ("parking", None, "парковка", "uz_cyrl", "positive"),
    # Pets allowed
    ("pets_allowed", None, "можно с животными", "ru", "positive"),
    ("pets_allowed", None, "разрешены животные", "ru", "positive"),
    ("pets_allowed", None, "uy hayvonlari mumkin", "uz", "positive"),
    # Internet
    ("internet", None, "интернет", "ru", "positive"),
    ("internet", None, "wi-fi", "ru", "positive"),
    ("internet", None, "wifi", "ru", "positive"),
    ("internet", None, "вайфай", "ru", "positive"),
    ("internet", None, "internet", "uz", "positive"),
    # Security
    ("security", None, "охрана", "ru", "positive"),
    ("security", None, "видеонаблюдение", "ru", "positive"),
    ("security", None, "охраняемая территория", "ru", "positive"),
    ("security", None, "qo'riqlash", "uz", "positive"),
    # Repair / condition
    ("condition", "euro", "евроремонт", "ru", "positive"),
    ("condition", "designer", "дизайнерский ремонт", "ru", "positive"),
    ("condition", "needs_repair", "требует ремонта", "ru", "positive"),
    ("condition", "euro", "evro remont", "uz", "positive"),
    # Gas
    ("gas_supply", "central", "газ", "ru", "positive"),
    ("gas_supply", "central", "природный газ", "ru", "positive"),
    ("gas_supply", "central", "gaz", "uz", "positive"),
    # Heating
    ("heating", "central", "центральное отопление", "ru", "positive"),
    ("heating", "individual", "автономное отопление", "ru", "positive"),
    ("heating", "individual", "индивидуальное отопление", "ru", "positive"),
    # Wall material
    ("wall_material", "brick", "кирпичный дом", "ru", "positive"),
    ("wall_material", "panel", "панельный дом", "ru", "positive"),
    ("wall_material", "monolith", "монолитный дом", "ru", "positive"),
    # Mortgage / installment / halal
    ("mortgage_ok", None, "можно в ипотеку", "ru", "positive"),
    ("installment_ok", None, "в рассрочку", "ru", "positive"),
    ("halol_ok", None, "халяль", "ru", "positive"),
    ("halol_ok", None, "халол", "uz_cyrl", "positive"),
    # Urgent
    ("urgent_flag", None, "срочно", "ru", "positive"),
    ("urgent_flag", None, "shoshilinch", "uz", "positive"),
]


async def main() -> None:
    total_inserted = 0
    async with async_session_maker() as db:
        values = [
            {
                "parameter_key": pk,
                "parameter_value": pv,
                "surface_form": surf,
                "language": lang,
                "polarity": pol,
            }
            for pk, pv, surf, lang, pol in _SEED
        ]
        stmt = (
            pg_insert(SynonymEntry)
            .values(values)
            .on_conflict_do_nothing()
            .returning(SynonymEntry.id)
        )
        rows = list((await db.execute(stmt)).scalars().all())
        total_inserted = len(rows)
        await db.commit()
    print(
        f"seed_block_f_synonyms: inserted={total_inserted} "
        f"requested={len(_SEED)} skipped={len(_SEED) - total_inserted}"
    )


if __name__ == "__main__":
    asyncio.run(main())
