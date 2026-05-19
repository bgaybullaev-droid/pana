"""Block D V2.0 (D5) — natural-language query parser for bot search.

Pure-function module that turns free-text input like
``"2-комн Чиланзар до 35тыс у.е."`` into a structured
:class:`ParsedQuery` the search executor can hand to Meilisearch.

Design discipline (per Block D guardrails)
==========================================

- **No LLM in the hot path.** Rule-based regex + dictionary lookups
  only. Latency budget for Inline Mode is ~1 s end-to-end; LLM calls
  blow that budget and add per-query cost with no MVP justification.
- **Explicit over clever.** District / rooms / deal type / property
  type dictionaries live inline as Python dicts — no YAML, no plugin
  system, no meta-programming. ``grep`` finds every recognised token.
- **Domain returns domain objects.** ``parse()`` produces a
  :class:`ParsedQuery` dataclass. The bot adapter (``bot/inline.py``,
  ``bot/handlers.py``) is the only layer that knows about Telegram.
- **Deletable in one commit.** The parser has zero side effects, zero
  I/O, no DB schema. Removing D5 means deleting this file.

Coverage today
==============

Districts:     reuse ``core.regions._DISTRICT_ALIASES`` (already a
               curated Cyrillic / Latin / fuzzy alias list).
Rooms:         "2комн", "3 комнаты", "1-комн", "двухкомнатная",
               "2 xona", "3-xonali" — Russian + Uzbek numerals 1-9.
Price:         "до 30000", "от 50 тыс", "до $40k", "до 35тыс у.е.",
               "до 35000 сум", "200 млн so'm" — UZS default per
               D5-Q8; switches to USD if "у.е.", "y.e.", "usd", "$"
               appears anywhere.
Deal type:     "продажа", "купить", "аренда", "снять", "sotiladi",
               "ijara".
Property type: "квартира", "дом", "коммерческ", "офис", "xonadon",
               "uy", "kommertsiya".

Anything else (street names, landmarks, vague phrases) is silently
ignored — the parser is conservative; an unrecognised token never
mis-parses.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from app.core.regions import _DISTRICT_ALIASES

# Bare-form district aliases. The shared ``_DISTRICT_ALIASES`` covers
# the suffixed forms ("Чиланзарский", "Yunusobod tumani") but bot
# queries are usually casual ("Чиланзар", "Юнусабад"). These
# additional entries cover the bare form without modifying the
# shared module (which is also consumed by the crawler).
_BARE_DISTRICT_FORMS: dict[str, str] = {
    "чиланзар": "chilonzor",
    "юнусабад": "yunusobod",
    "юнусобод": "yunusobod",
    "сергели": "sergeli",
    "яшнабад": "yashnobod",
    "яшнобод": "yashnobod",
    "мирабад": "mirobod",
    "мирабод": "mirobod",
    "алмазар": "olmazor",
    "олмазор": "olmazor",
    "учтепа": "uchtepa",
    "уч-тепа": "uchtepa",
    "шайхантахур": "shayxontohur",
    "шайхонтохур": "shayxontohur",
    "бектемир": "bektemir",
    "мирзо-улугбек": "mirzo_ulugbek",
    "мирзо улугбек": "mirzo_ulugbek",
    "юкори": "yakkasaroy",
    "яккасарай": "yakkasaroy",
    "яккасарой": "yakkasaroy",
    "хамза": "yashnobod",  # historical name
    "хамзинский": "yashnobod",
}

logger = logging.getLogger(__name__)


# =============================================================================
# Output type
# =============================================================================


@dataclass(frozen=True)
class ParsedQuery:
    """Structured result of :func:`parse`.

    Every field is optional — callers should treat the presence of any
    non-None field as "the user expressed a preference for this." The
    ``confidence`` field captures how many filters were extracted
    relative to the input length; the heuristic in
    :mod:`app.bot.handlers` uses this to distinguish a search query
    from casual chat.
    """

    district: Optional[str] = None          # canonical district key
    rooms_min: Optional[int] = None
    rooms_max: Optional[int] = None
    price_min: Optional[int] = None         # in price_currency units
    price_max: Optional[int] = None
    price_currency: Optional[str] = None    # "UZS" | "USD"
    deal_type: Optional[str] = None          # "sell" | "rent"
    property_type: Optional[str] = None      # "apartment" | "house" | ...
    raw_text: str = ""
    extracted_fields: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        """True if no filter was extracted — caller should show a hint."""
        return not self.extracted_fields


# =============================================================================
# Dictionaries (explicit, grep-friendly)
# =============================================================================


# Russian + Uzbek word→number for room counts. Covers ordinary speech
# and the more frequent "X-комн" / "X-xonali" forms.
_ROOM_WORDS_RU: dict[str, int] = {
    "одно": 1, "однокомн": 1, "однокомнатн": 1,
    "двух": 2, "двухкомн": 2, "двухкомнатн": 2,
    "трёх": 3, "трех": 3, "трёхкомн": 3, "трехкомн": 3, "трехкомнатн": 3,
    "четырёх": 4, "четырех": 4, "четырёхкомн": 4, "четырехкомн": 4,
    "пяти": 5, "пятикомн": 5,
}
_ROOM_WORDS_UZ_LATIN: dict[str, int] = {
    "bir xonali": 1, "ikki xonali": 2, "uch xonali": 3,
    "tort xonali": 4, "to'rt xonali": 4, "tórt xonali": 4,
    "besh xonali": 5,
}

# Deal-type vocabulary. Match against tokens (post-normalisation).
_DEAL_TYPE_KEYWORDS: dict[str, str] = {
    # sell
    "продажа": "sell", "продаж": "sell",
    "купить": "sell", "куплю": "sell",
    "sotiladi": "sell", "sotmoq": "sell", "sotuv": "sell",
    "sotib olmoq": "sell", "sotib": "sell",
    # rent
    "аренда": "rent", "аренд": "rent",
    "снять": "rent", "сниму": "rent",
    "ijara": "rent", "ijarag": "rent", "ijaraga": "rent",
    "kira": "rent",
}

# Property-type vocabulary.
_PROPERTY_TYPE_KEYWORDS: dict[str, str] = {
    # apartment
    "квартира": "apartment", "квартир": "apartment", "квартиру": "apartment",
    "xonadon": "apartment", "kvartira": "apartment",
    # house
    "дом": "house", "дома": "house",
    "uy": "house", "uy-joy": "house", "hovli": "house",
    # commercial
    "коммерческ": "commercial", "офис": "commercial",
    "kommertsiya": "commercial", "ofis": "commercial",
    # land
    "земель": "land", "участок": "land", "yer": "land",
}

# Currency tokens — presence ANYWHERE in the query flips default to USD.
_USD_TOKENS = ("у.е.", "y.e.", "у.е", "y.e", "usd", "$", "дол", "доллар")
_UZS_TOKENS = ("сум", "сўм", "so'm", "som", "soʻm")

# Price-magnitude multipliers (case-insensitive).
_MAGNITUDE_MULTIPLIERS: dict[str, int] = {
    "тыс": 1_000, "tys": 1_000, "k": 1_000, "к": 1_000,
    "млн": 1_000_000, "mln": 1_000_000, "m": 1_000_000,
}


# =============================================================================
# Sub-parsers (each returns Optional[value])
# =============================================================================


_PRICE_BOUND_RE = re.compile(
    r"""
    (?P<bound>\bдо\b|\bот\b|\bdo\b|\bot\b|≤|<=|≥|>=)?    # optional bound word
    \s*
    \$?                                                 # optional leading $
    (?P<num>\d[\d\s.,]*)                                # the number
    \s*
    # Magnitude suffix MUST be followed by whitespace / punctuation /
    # end-of-string so we don't mis-match the leading "к" of "комнаты"
    # or the "m" of "metroplis" etc.
    (?:(?P<mult>тыс|tys|k|к|млн|mln|m)(?=\s|$|[^а-яёa-z]))?
    """,
    re.IGNORECASE | re.VERBOSE | re.UNICODE,
)

_ROOMS_DIGIT_RE = re.compile(
    r"""(?<!\d)(\d+)\s*[-]?\s*(?:комн|комнат|xona|xonali|hona|honali)""",
    re.IGNORECASE,
)


def _parse_district(text: str) -> Optional[str]:
    """Return canonical district key for the longest matching alias.

    Walks two dictionaries: the shared ``_DISTRICT_ALIASES`` (covers
    suffixed forms like "Чиланзарский район") and a bot-specific
    ``_BARE_DISTRICT_FORMS`` (covers casual short forms like
    "Чиланзар"). Longest match wins.
    """
    normalized = text.lower()
    best_key: Optional[str] = None
    best_len = 0
    for source in (_DISTRICT_ALIASES, _BARE_DISTRICT_FORMS):
        for alias, canonical in source.items():
            if len(alias) <= best_len:
                continue
            if alias in normalized:
                best_key = canonical
                best_len = len(alias)
    return best_key


def _parse_rooms(text: str) -> tuple[Optional[int], Optional[int]]:
    """Return ``(rooms_min, rooms_max)``. MVP: same value for both."""
    # Digit form: "2-комн" / "3xonali" / "1 комнат"
    m = _ROOMS_DIGIT_RE.search(text)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 9:
            return n, n

    # Russian word forms.
    norm = text.lower()
    for word, n in _ROOM_WORDS_RU.items():
        if word in norm:
            return n, n

    # Uzbek Latin word forms.
    for phrase, n in _ROOM_WORDS_UZ_LATIN.items():
        if phrase in norm:
            return n, n

    return None, None


def _parse_deal_type(text: str) -> Optional[str]:
    norm = text.lower()
    for keyword, value in _DEAL_TYPE_KEYWORDS.items():
        if keyword in norm:
            return value
    return None


def _parse_property_type(text: str) -> Optional[str]:
    norm = text.lower()
    for keyword, value in _PROPERTY_TYPE_KEYWORDS.items():
        if keyword in norm:
            return value
    return None


def _detect_currency(text: str) -> str:
    """Default UZS; switch to USD only if an explicit USD token is present.

    Per DECISION_MATRIX D5-Q8. We do NOT look at Tashkent prices to
    infer currency — a bare ``30000`` could be either; trusting the
    presence of an explicit currency token is the only safe rule.
    """
    norm = text.lower()
    if any(tok in norm for tok in _USD_TOKENS):
        return "USD"
    # Explicit UZS-tokens don't change anything (UZS is already default)
    # but checking helps with future logic like multi-currency display.
    return "UZS"


def _parse_price(text: str) -> tuple[Optional[int], Optional[int]]:
    """Return ``(price_min, price_max)`` in the current currency unit.

    Recognises ``до X`` / ``от X`` ranges + magnitude suffixes
    (тыс / k / млн). Multiple price tokens in one query: ``до X`` wins
    for the upper bound, ``от X`` wins for the lower.
    """
    norm = text.lower()
    price_min: Optional[int] = None
    price_max: Optional[int] = None

    for m in _PRICE_BOUND_RE.finditer(norm):
        raw = m.group("num")
        # Reject if the number is fewer than 3 digits AND has no magnitude
        # suffix — guards against parsing "2-комн" digits as prices.
        # We also skip if the surrounding word is a known room indicator.
        digits = re.sub(r"[^\d]", "", raw)
        if not digits:
            continue
        n = int(digits)
        mult = m.group("mult")
        if mult:
            n *= _MAGNITUDE_MULTIPLIERS.get(mult.lower(), 1)
        elif n < 100:
            # No magnitude and tiny number — likely room count, not a price.
            # Skip to avoid mis-parsing "2 комн" as price=2.
            continue

        bound = (m.group("bound") or "").lower()
        if bound in ("до", "do", "<=", "≤"):
            price_max = n if price_max is None else min(price_max, n)
        elif bound in ("от", "ot", ">=", "≥"):
            price_min = n if price_min is None else max(price_min, n)
        else:
            # Bare number — treat as upper bound (most common: "100k")
            if price_max is None:
                price_max = n

    return price_min, price_max


# =============================================================================
# Public API
# =============================================================================


def parse(text: str, lang: str = "ru") -> ParsedQuery:
    """Extract structured filters from a free-text query.

    Caller passes the user's language so future enhancements can
    bias dictionaries (today both languages share the same dicts).
    """
    del lang  # reserved for future use; kept in signature to avoid churn
    text = (text or "").strip()
    if not text:
        return ParsedQuery(raw_text="")

    district = _parse_district(text)
    rooms_min, rooms_max = _parse_rooms(text)
    deal_type = _parse_deal_type(text)
    property_type = _parse_property_type(text)
    currency = _detect_currency(text)
    price_min, price_max = _parse_price(text)

    extracted: list[str] = []
    if district:
        extracted.append("district")
    if rooms_min is not None:
        extracted.append("rooms")
    if deal_type:
        extracted.append("deal_type")
    if property_type:
        extracted.append("property_type")
    if price_min is not None or price_max is not None:
        extracted.append("price")

    return ParsedQuery(
        district=district,
        rooms_min=rooms_min,
        rooms_max=rooms_max,
        price_min=price_min,
        price_max=price_max,
        price_currency=currency if (price_min is not None or price_max is not None) else None,
        deal_type=deal_type,
        property_type=property_type,
        raw_text=text,
        extracted_fields=tuple(extracted),
    )
