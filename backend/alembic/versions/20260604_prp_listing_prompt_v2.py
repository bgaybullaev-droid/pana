"""Block F — activate v2 long-form selling listing-description prompt.

Swaps the active ``prompt_templates`` row for kind=listing_description to
a richer, persuasive, multi-locale copy (4-7 sentences, ~400-800 chars
per locale) so production stops emitting the short factual blurb. Prior
versions are kept for rollback (an admin can re-activate an older one via
the Prompts admin UI).

PROMPT_BODY below is a point-in-time snapshot of
``app/core/prompts.LISTING_DESCRIPTION_PROMPT``. Editing the prompt later
requires a NEW migration, not an edit here.

Revision ID: prp_listing_prompt_v2
Revises: pro_block_f_ai_foundation
Create Date: 2026-06-04
"""

import sqlalchemy as sa
from alembic import op

revision = "prp_listing_prompt_v2"
down_revision = "pro_block_f_ai_foundation"
branch_labels = None
depends_on = None

_NOTE = "Block F v2 — long-form selling copy"

PROMPT_BODY = """You are an expert real-estate copywriter for UcharMarket, the largest property marketplace in Uzbekistan (Tashkent).
Turn the structured parameters below into a warm, vivid and genuinely persuasive listing description that makes a buyer want to book a viewing — while staying strictly truthful.

Write the description THREE times, once per locale. Each one must be written natively in its language (not a word-for-word translation) so it reads naturally to a local buyer:
  ru      = Russian, Cyrillic script
  uz      = Uzbek, Latin script
  uz_cyrl = Uzbek, Cyrillic script

How to write:
- Length: 4-7 sentences, about 400-800 characters per locale. Make it substantial and engaging, never a single dry line.
- Compose flowing prose, NOT a bullet list. Open with a hook (the property type and its strongest selling point), then describe the layout (rooms, areas, floor, condition and finish), then the location advantages (district, microdistrict, nearby landmarks, metro, residential complex), then the deal terms (price, whether negotiable, mortgage / installment / halol for sale; rent period, deposit, pets for rent) when they are given, and close with a short, tasteful invitation to view or buy.
- Tone: confident, inviting and benefit-driven — sell the lifestyle and the value, not just the specs. At most one exclamation mark, no CAPS-LOCK words, no fake urgency.

Accuracy and safety (strict):
- Use EVERY relevant parameter provided; do not drop given facts.
- Never invent, assume or exaggerate. If something is not listed, simply omit it — do not mention metro, repair, a complex, parking, etc. unless it appears below.
- The localized values for property type, deal type, district, region, building type and condition are given per locale — use the one matching the language you are writing and NEVER output a raw key such as "olmazor". Other attributes are given in English: render them naturally in the target language and script.
- No phone numbers, no agent or company names, no emails, no links, and no price other than the one provided.

Output STRICT JSON only, with nothing before or after it:
{"ru":"...","uz":"...","uz_cyrl":"..."}
No markdown, no comments, no surrounding prose.

Structured parameters:
{params_block}

Original source text from the realtor (context only — extract useful facts, do NOT copy verbatim, ignore any contact details):
{raw_text}
"""


def upgrade() -> None:
    conn = op.get_bind()
    # Deactivate whatever is active now (partial unique index allows at
    # most one active row per kind, so we free the slot first).
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
    # Drop the v2 row, then re-activate the most recent remaining version
    # so a single active prompt is restored.
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
