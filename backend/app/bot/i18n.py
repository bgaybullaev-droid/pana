"""Internationalization (i18n) module for the seller registration bot.

Supports Russian (ru) and Uzbek (uz) languages.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = ("ru", "uz")
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


def get_language(language_code: str | None) -> str:
    """Normalize and validate language code.

    Args:
        language_code: Language code from Telegram or user preference

    Returns:
        Supported language code (defaults to 'ru' if unsupported)
    """
    if not language_code:
        return DEFAULT_LANGUAGE

    # Normalize: take first 2 chars and lowercase
    lang = language_code[:2].lower()

    # Map common variations
    lang_map = {
        "uz": "uz",
        "ru": "ru",
        "uk": "ru",  # Ukrainian -> Russian fallback
        "be": "ru",  # Belarusian -> Russian fallback
        "kk": "ru",  # Kazakh -> Russian fallback
        "tg": "ru",  # Tajik -> Russian fallback
    }

    return lang_map.get(lang, DEFAULT_LANGUAGE)


def t(lang: str, key: str, **kwargs: Any) -> str:
    """Get translated string for the given language and key.

    Args:
        lang: Language code ('ru' or 'uz')
        key: Translation key (e.g., 'welcome', 'enter_name')
        **kwargs: Format arguments for string interpolation

    Returns:
        Translated string, or key if translation not found
    """
    # Ensure translations are loaded
    if not _translations:
        load_translations()

    # Normalize language
    lang = get_language(lang)

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
