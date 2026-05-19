"""Block F V2.0 (F2) — rule-based synonym → parameter matcher.

Pure Python, zero LLM calls. Reads the curated ``synonym_entries``
dictionary, scans the seller's free-text editor, and surfaces hints
when a parameter is mentioned but not checked, or when the text
contradicts the structured state.

Public surface:
    SynonymMatch                                  — result row
    match_text_to_params(db, text, lang, params)  — async match call

Algorithm:
    1. Lowercase the input text.
    2. Load all ``synonym_entries`` rows for ``language IN (lang, '*')``.
    3. For each surface_form, find the first occurrence in text with
       ``str.find`` (no regex — surface forms may contain meta chars).
    4. Examine the 5-token window preceding the match for any negation
       marker (``["не", "без", "no", "yo'q", "yo'k"]``). A negation flips
       polarity.
    5. Compare resulting polarity against ``current_params[parameter_key]``
       and emit one of: ``"add" | "contradict" | "ok"``.
    6. Deduplicate by ``parameter_key`` (first hit wins).
    7. Cap at 20 matches to bound payload size.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SynonymEntry

logger = logging.getLogger(__name__)

# Negation markers searched in the 5-token window preceding a match.
# Case-folded; we compare lowercase. ``yo'q`` and ``yo'k`` are both
# common spellings in Latin Uzbek.
_NEGATION_TOKENS = {"не", "без", "no", "yo'q", "yo'k", "йўқ", "ёқ"}
_NEGATION_WINDOW = 5
_MAX_MATCHES = 20

# Token splitter: any non-alnum / non-apostrophe sequence.
_TOKEN_RE = re.compile(r"[^a-zа-яёўғқҳ0-9'’ʼ_]+", flags=re.IGNORECASE)


@dataclass(frozen=True)
class SynonymMatch:
    """One mention surfaced to the seller."""

    parameter_key: str
    parameter_value: Optional[str]
    surface_form: str
    polarity: str  # "positive" | "negative" — after negation handling
    action: str  # "add" | "contradict" | "ok"
    position: int  # char offset where the surface form was found


def _tokens_before(text: str, char_pos: int) -> list[str]:
    """Return the *5* most recent tokens preceding ``char_pos``."""
    if char_pos <= 0:
        return []
    preceding = text[:char_pos]
    tokens = [t for t in _TOKEN_RE.split(preceding.lower()) if t]
    return tokens[-_NEGATION_WINDOW:]


def _detect_polarity(text: str, char_pos: int, base_polarity: str) -> str:
    """Apply the 5-token negation window. Returns the effective
    polarity after any negation flip."""
    tokens = _tokens_before(text, char_pos)
    has_negation = any(t in _NEGATION_TOKENS for t in tokens)
    if not has_negation:
        return base_polarity
    # Flip.
    return "negative" if base_polarity == "positive" else "positive"


def _action_for(
    polarity: str,
    parameter_key: str,
    parameter_value: Optional[str],
    current_params: dict[str, Any],
) -> str:
    """Decide whether this match means add/contradict/ok against the
    seller's currently-checked structured params."""
    current = current_params.get(parameter_key)

    if polarity == "positive":
        # Boolean-style param (parameter_value is None means the
        # surface form just asserts True/False for the key).
        if parameter_value is None:
            if current is True:
                return "ok"
            if current is False:
                return "contradict"
            return "add"  # unset → invite to add
        # Enum-valued — compare exact value.
        if current == parameter_value:
            return "ok"
        if current in (None, "", []):
            return "add"
        return "contradict"

    # polarity == "negative"
    if parameter_value is None:
        if current is False:
            return "ok"
        if current is True:
            return "contradict"
        return "add"  # invite to set False
    # For enum + negative ("без мебели" but param says "with_furniture")
    if current == parameter_value:
        return "contradict"
    return "ok"


async def match_text_to_params(
    db: AsyncSession,
    text: str,
    lang: str,
    current_params: dict[str, Any] | None = None,
) -> list[SynonymMatch]:
    """Return at most ``_MAX_MATCHES`` actionable hints. Pure-read; no
    state change. Empty list when the dictionary is empty or no
    surface form matched.
    """
    current_params = current_params or {}
    if not text or not text.strip():
        return []
    text_lower = text.lower()

    # Pull every surface form for this lang + wildcard. Production
    # dictionary is ~hundreds of rows so in-memory scan is fine; if it
    # ever exceeds a few k rows we'd materialise as a static cache.
    stmt = select(SynonymEntry).where(
        or_(SynonymEntry.language == lang, SynonymEntry.language == "*")
    )
    rows = list((await db.execute(stmt)).scalars().all())

    matches: list[SynonymMatch] = []
    seen_keys: set[str] = set()
    for row in rows:
        if row.parameter_key in seen_keys:
            continue
        needle = row.surface_form.lower().strip()
        if not needle:
            continue
        pos = text_lower.find(needle)
        if pos < 0:
            continue
        polarity = _detect_polarity(text, pos, row.polarity or "positive")
        action = _action_for(
            polarity, row.parameter_key, row.parameter_value, current_params
        )
        if action == "ok":
            # Surfacing "ok" hints would just clutter the UI; the
            # spec drops them from the response.
            seen_keys.add(row.parameter_key)
            continue
        matches.append(
            SynonymMatch(
                parameter_key=row.parameter_key,
                parameter_value=row.parameter_value,
                surface_form=row.surface_form,
                polarity=polarity,
                action=action,
                position=pos,
            )
        )
        seen_keys.add(row.parameter_key)
        if len(matches) >= _MAX_MATCHES:
            break

    if matches:
        logger.info(
            "synonym_matcher.matched lang=%s match_count=%d",
            lang,
            len(matches),
        )
    return matches
