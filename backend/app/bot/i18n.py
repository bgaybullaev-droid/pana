"""Internationalization (i18n) module for the seller registration bot.

Supports Russian (ru), Uzbek Latin (uz), and Uzbek Cyrillic (uz_cyrl).
Block D V2.0 added uz_cyrl as the third locale to honor the
language-consistency principle across bot + TWA surfaces.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Supported languages — canonical backend identifiers.
# Frontend i18n folder uses "uz-cyrl" (kebab); the boundary mapping
# happens in the API schema layer.
SUPPORTED_LANGUAGES = ("ru", "uz", "uz_cyrl")
DEFAULT_LANGUAGE = "ru"

# Translation cache
_translations: dict[str, dict[str, str]] = {}

# Path to translations directory
TRANSLATIONS_DIR = Path(__file__).parent / "translations"


def load_translations() -> None:
    """Load all translation files into memory."""
    global _translations

    for lang in SUPPORTED_LANGUAGES:
        lang_file = TRANSLATIONS_DIR / f"{lang}.json"
        if lang_file.exists():
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    _translations[lang] = json.load(f)
                logger.info(
                    f"Loaded {len(_translations[lang])} translations for '{lang}'"
                )
            except Exception as e:
                logger.error(f"Failed to load translations for '{lang}': {e}")
                _translations[lang] = {}
        else:
            logger.warning(f"Translation file not found: {lang_file}")
            _translations[lang] = {}


def get_language(value: str | None) -> str:
    """Validate and normalise a stored language value.

    Input is expected to be either a canonical backend identifier
    ("ru", "uz", "uz_cyrl") or the kebab variant ("uz-cyrl") used by
    the frontend; unknown values fall back to ``DEFAULT_LANGUAGE``.

    For Telegram's 2-char ``language_code`` (where "uz" must map to
    ``uz_cyrl`` per D1-Q2), use :func:`language_from_telegram_code`
    instead — the two have different semantics and must not be merged.
    """
    if not value:
        return DEFAULT_LANGUAGE

    normalized = value.lower().replace("-", "_")
    if normalized in SUPPORTED_LANGUAGES:
        return normalized
    # Legacy values or odd 2-letter codes that happened to be persisted
    # — funnel through the Telegram-code mapping so e.g. an old "en"
    # row degrades to ru rather than blowing up.
    return language_from_telegram_code(normalized)


def language_from_telegram_code(code: str | None) -> str:
    """Map Telegram's ISO 639-1 ``language_code`` to canonical form.

    Per Block D D1-Q2, Telegram ``"uz"`` is treated as Uzbek-Cyrillic
    because Cyrillic is the dominant keyboard layout among Uzbek
    Telegram users.
    """
    if not code:
        return DEFAULT_LANGUAGE
    short = code.lower()[:2]
    return {
        "ru": "ru",
        "uz": "uz_cyrl",  # D1-Q2
        "uk": "ru",  # Ukrainian -> Russian fallback
        "be": "ru",  # Belarusian -> Russian fallback
        "kk": "ru",  # Kazakh -> Russian fallback
        "tg": "ru",  # Tajik -> Russian fallback
    }.get(short, DEFAULT_LANGUAGE)


def t(lang: str, key: str, **kwargs: Any) -> str:
    """Get translated string for the given language and key.

    Args:
        lang: Language code ('ru', 'uz', or 'uz_cyrl')
        key: Translation key (e.g., 'welcome', 'enter_name')
        **kwargs: Format arguments for string interpolation

    Returns:
        Translated string, or key if translation not found

    Block D production safety:
        - If ``settings.i18n_uz_cyrl_bot_fallback_to_ru`` is True, every
          ``lang="uz_cyrl"`` lookup is rewritten to ``"ru"`` BEFORE the
          translation lookup. This is the kill-switch for the
          programmatic transliteration — flippable via env var without
          a code deploy if native review finds critical issues.
        - Missing keys always fall back through DEFAULT_LANGUAGE; never
          raise.
    """
    # Ensure translations are loaded
    if not _translations:
        load_translations()

    # Normalize language
    lang = get_language(lang)

    # Block D safety override: env-flipped fallback for uz_cyrl.
    # Imported lazily to avoid a startup-order circular with config.
    if lang == "uz_cyrl":
        try:
            from app.core.config import settings as _settings

            if getattr(_settings, "i18n_uz_cyrl_bot_fallback_to_ru", False):
                lang = DEFAULT_LANGUAGE
        except Exception:
            pass

    # Get translation
    translations = _translations.get(lang, {})
    text = translations.get(key)

    # Fallback to default language
    if text is None and lang != DEFAULT_LANGUAGE:
        text = _translations.get(DEFAULT_LANGUAGE, {}).get(key)
        if text:
            logger.debug(f"Fallback to {DEFAULT_LANGUAGE} for key '{key}'")

    # If still not found, return the key
    if text is None:
        logger.warning(f"Translation not found: lang='{lang}', key='{key}'")
        return f"[{key}]"

    # Apply string formatting if kwargs provided
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing format key {e} in translation '{key}'")

    return text


def get_all_keys(lang: str = DEFAULT_LANGUAGE) -> list[str]:
    """Get all available translation keys for a language."""
    if not _translations:
        load_translations()
    return list(_translations.get(lang, {}).keys())


# Convenience function for keyboards
def tk(lang: str, key: str) -> str:
    """Get translated string for keyboard buttons (short form)."""
    return t(lang, f"btn_{key}")


# Initialize translations on module load
load_translations()
