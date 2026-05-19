"""Block F V2.0 F4a — seed export_templates with 3 platforms × 3 langs.

Idempotent: re-running updates active template bodies in place; insert
only happens when no active row exists for (platform, language).

Templates are placeholder-only (no Jinja control blocks) per the F4
spec sandbox contract. Missing seller fields (signature/CTA/hashtags)
render as empty strings — the renderer trims trailing whitespace so the
final body stays clean.

Usage:
    python -m backend.scripts.seed_block_f_export_templates
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.database import async_session_maker
from app.db.models import ExportTemplate

# (platform, language) → body. Placeholders only.
_TEMPLATES: dict[tuple[str, str], str] = {
    ("olx", "ru"): """\
{{ title }}

{{ description }}

Цена: {{ price_formatted }}
Район: {{ district }}

{{ cta }}
{{ signature }}""",
    ("olx", "uz"): """\
{{ title }}

{{ description }}

Narxi: {{ price_formatted }}
Tuman: {{ district }}

{{ cta }}
{{ signature }}""",
    ("olx", "uz_cyrl"): """\
{{ title }}

{{ description }}

Нархи: {{ price_formatted }}
Туман: {{ district }}

{{ cta }}
{{ signature }}""",
    ("telegram_channel", "ru"): """\
🏠 {{ title }}

{{ description }}

💰 {{ price_formatted }}
📍 {{ district }}

🔗 {{ listing_url }}

{{ cta }} {{ extra_hashtags }}""",
    ("telegram_channel", "uz"): """\
🏠 {{ title }}

{{ description }}

💰 {{ price_formatted }}
📍 {{ district }}

🔗 {{ listing_url }}

{{ cta }} {{ extra_hashtags }}""",
    ("telegram_channel", "uz_cyrl"): """\
🏠 {{ title }}

{{ description }}

💰 {{ price_formatted }}
📍 {{ district }}

🔗 {{ listing_url }}

{{ cta }} {{ extra_hashtags }}""",
    ("instagram", "ru"): """\
{{ title }}

{{ description }}

📍 {{ district }}  ·  💰 {{ price_formatted }}

{{ cta }}

#недвижимость #квартира #продажа #ucharmarket {{ extra_hashtags }}""",
    ("instagram", "uz"): """\
{{ title }}

{{ description }}

📍 {{ district }}  ·  💰 {{ price_formatted }}

{{ cta }}

#kochmas_mulk #kvartira #ucharmarket {{ extra_hashtags }}""",
    ("instagram", "uz_cyrl"): """\
{{ title }}

{{ description }}

📍 {{ district }}  ·  💰 {{ price_formatted }}

{{ cta }}

#кучмас_мулк #квартира #ucharmarket {{ extra_hashtags }}""",
}


async def main() -> None:
    inserted = 0
    updated = 0
    async with async_session_maker() as db:
        for (platform, lang), body in _TEMPLATES.items():
            existing = (
                await db.execute(
                    select(ExportTemplate).where(
                        ExportTemplate.platform == platform,
                        ExportTemplate.language == lang,
                        ExportTemplate.is_active.is_(True),
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                db.add(
                    ExportTemplate(
                        platform=platform,
                        language=lang,
                        template_body=body,
                        is_active=True,
                    )
                )
                inserted += 1
            elif existing.template_body != body:
                existing.template_body = body
                updated += 1
        await db.commit()
    print(
        f"seed_block_f_export_templates: inserted={inserted} updated={updated}"
    )


if __name__ == "__main__":
    asyncio.run(main())
