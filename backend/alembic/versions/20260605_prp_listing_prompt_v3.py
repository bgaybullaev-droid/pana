"""Block F — activate v3 calm, paragraphed, price-free listing prompt.

Swaps the active ``prompt_templates`` row for kind=listing_description to a
calmer, more natural copy: plain conversational tone (no marketing cliches,
no exclamation marks), 2-3 short paragraphs, max ~500 chars per locale, and
NO price/money amount in the generated text (price is shown separately on the
listing page). Prior versions are kept for rollback (re-activate an older one
via the Prompts admin UI or this migration's downgrade).

PROMPT_BODY below is a point-in-time snapshot of
``app/core/prompts.LISTING_DESCRIPTION_PROMPT``. Editing the prompt later
requires a NEW migration, not an edit here.

Revision ID: prp_listing_prompt_v3
Revises: rename_city_district_keys
Create Date: 2026-06-05
"""

import sqlalchemy as sa
from alembic import op

revision = "prp_listing_prompt_v3"
down_revision = "rename_city_district_keys"
branch_labels = None
depends_on = None

_NOTE = "Block F v3 — calm local copy, no price, paragraphs"

PROMPT_BODY = """You are writing a property listing description for UcharMarket (Uzbekistan, Tashkent).
Describe the property below the way an ordinary local person would describe their own home to a friend: simple, friendly and natural, NOT a glossy marketing pitch.

Write the description THREE times, once per locale, each written natively in its language (not a word-for-word translation):
  ru      = Russian, Cyrillic script
  uz      = Uzbek, Latin script
  uz_cyrl = Uzbek, Cyrillic script

How to write:
- Length: 3-4 short sentences, MAXIMUM 500 characters per locale. Calm and to the point, never padded.
- Structure each locale as 2-3 short paragraphs with one blank line between them:
  paragraph 1 = what it is (rooms, area, floor, condition);
  paragraph 2 = location and what is nearby;
  paragraph 3 = one short, plain closing line.
- Tone: plain, calm, conversational. NO exclamation marks. Avoid marketing cliches such as "представляем вашему вниманию", "идеальный выбор", "не упустите шанс" or "спешите". Do not oversell; state the facts with at most a light positive note.

Accuracy and safety (strict):
- Use only the parameters provided; never invent, assume or exaggerate. If something is not listed, simply omit it.
- The localized values for property type, deal type, district, region, building type and condition are given per locale: use the one matching the language you are writing and NEVER output a raw key such as "olmazor". Other attributes are given in English: render them naturally in the target language and script.
- Do NOT mention any price or money amount - it is shown separately on the page. No phone numbers, no agent or company names, no emails, no links.

Output STRICT JSON only, with nothing before or after it:
{"ru":"...","uz":"...","uz_cyrl":"..."}
No markdown, no comments, no surrounding prose.

Structured parameters:
{params_block}

Original source text from the realtor (context only - extract useful facts, do NOT copy verbatim, ignore any contact details):
{raw_text}
"""


def upgrade() -> None:
    conn = op.get_bind()
    # Deactivate whatever is active now (partial unique index allows at most
    # one active row per kind, so we free the slot first).
    conn.execute(
        sa.text(
            "UPDATE prompt_templates SET is_active = false "
            "WHERE kind = 'listing_description' AND is_active = true"
        )
    )
    # Insert the new version as the active prompt (version = max + 1).
    conn.execute(
        sa.text(
            "INSERT INTO prompt_templates "
            "(kind, version, body, model_hint, is_active, notes) VALUES "
            "('listing_description', "
            "COALESCE((SELECT MAX(version) FROM prompt_templates "
            "WHERE kind = 'listing_description'), 0) + 1, "
            ":body, 'gpt-4o-mini', true, :note)"
        ).bindparams(body=PROMPT_BODY, note=_NOTE)
    )


def downgrade() -> None:
    conn = op.get_bind()
    # Drop the v3 row, then re-activate the most recent remaining version so a
    # single active prompt is restored.
    conn.execute(
        sa.text(
            "DELETE FROM prompt_templates "
            "WHERE kind = 'listing_description' AND notes = :note"
        ).bindparams(note=_NOTE)
    )
    conn.execute(
        sa.text(
            "UPDATE prompt_templates SET is_active = true WHERE id = ("
            "  SELECT id FROM prompt_templates "
            "  WHERE kind = 'listing_description' "
            "  ORDER BY version DESC LIMIT 1"
            ") AND NOT EXISTS ("
            "  SELECT 1 FROM prompt_templates "
            "  WHERE kind = 'listing_description' AND is_active = true"
            ")"
        )
    )
