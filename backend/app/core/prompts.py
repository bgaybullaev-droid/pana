"""Block F F1/F5 — LLM prompt text for listing-description generation.

Single source of truth shared by the worker hard-coded fallback
(``ai_generation._build_prompt``) and the registry seed
(``scripts/seed_block_f_prompts.py``). Production actually reads the
active row of ``prompt_templates``; a migration inserts and activates a
copy of this text so prod picks it up without an admin action. When you
edit this prompt, also bump the active ``prompt_templates`` version
(migration or the Prompts admin UI) and keep the migration copy in sync.

Placeholders are substituted with ``str.replace`` (NOT ``str.format``)
so the literal JSON braces in the body are safe:
    {params_block} — localized structured parameters
    {raw_text}     — PII-scrubbed source text from the realtor
"""

# NOTE: keep this apostrophe-free in the instruction text so it embeds
# cleanly everywhere it is stored. Localized values that need apostrophes
# (Uzbek Latin o' / g') live in {params_block}, not here.
LISTING_DESCRIPTION_PROMPT = (
    "You are writing a property listing description for UcharMarket "
    "(Uzbekistan, Tashkent).\n"
    "Describe the property below the way an ordinary local person would "
    "describe their own home to a friend: simple, friendly and natural, NOT "
    "a glossy marketing pitch.\n"
    "\n"
    "Write the description THREE times, once per locale, each written "
    "natively in its language (not a word-for-word translation):\n"
    "  ru      = Russian, Cyrillic script\n"
    "  uz      = Uzbek, Latin script\n"
    "  uz_cyrl = Uzbek, Cyrillic script\n"
    "\n"
    "How to write:\n"
    "- Length: 3-4 short sentences, MAXIMUM 500 characters per locale. Calm "
    "and to the point, never padded.\n"
    "- Structure each locale as 2-3 short paragraphs with one blank line "
    "between them:\n"
    "  paragraph 1 = what it is (rooms, area, floor, condition);\n"
    "  paragraph 2 = location and what is nearby;\n"
    "  paragraph 3 = one short, plain closing line.\n"
    "- Tone: plain, calm, conversational. NO exclamation marks. Avoid "
    "marketing cliches such as \"представляем вашему вниманию\", \"идеальный "
    "выбор\", \"не упустите шанс\" or \"спешите\". Do not oversell; state the "
    "facts with at most a light positive note.\n"
    "\n"
    "Accuracy and safety (strict):\n"
    "- Use only the parameters provided; never invent, assume or exaggerate. "
    "If something is not listed, simply omit it.\n"
    "- The localized values for property type, deal type, district, region, "
    "building type and condition are given per locale: use the one matching "
    "the language you are writing and NEVER output a raw key such as "
    '"olmazor". Other attributes are given in English: render them naturally '
    "in the target language and script.\n"
    "- Do NOT mention any price or money amount - it is shown separately on "
    "the page. No phone numbers, no agent or company names, no emails, no "
    "links.\n"
    "\n"
    "Output STRICT JSON only, with nothing before or after it:\n"
    '{"ru":"...","uz":"...","uz_cyrl":"..."}\n'
    "No markdown, no comments, no surrounding prose.\n"
    "\n"
    "Structured parameters:\n"
    "{params_block}\n"
    "\n"
    "Original source text from the realtor (context only - extract useful "
    "facts, do NOT copy verbatim, ignore any contact details):\n"
    "{raw_text}\n"
)
