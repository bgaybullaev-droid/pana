"""Phone number normalization utilities."""

from typing import Optional


def normalize_phone(phone: Optional[str]) -> str:
    """Extract last 9 digits from any phone format for matching.

    Examples:
        +998901234567 → 901234567
        998901234567  → 901234567
        901234567     → 901234567
        90 123 45 67  → 901234567
        None          → ""
    """
    if not phone:
        return ""
    digits = "".join(c for c in phone if c.isdigit())
    return digits[-9:] if len(digits) >= 9 else digits


def normalize_phone_e164(phone: Optional[str]) -> str:
    """Normalize phone to full E.164 format (+998XXXXXXXXX).

    Returns empty string if phone is None/empty or doesn't have enough digits.

    Examples:
        +998901234567 → +998901234567
        998901234567  → +998901234567
        901234567     → +998901234567
        90 123 45 67  → +998901234567
        None          → ""
    """
    if not phone:
        return ""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 9:
        return f"+998{digits}"
    if len(digits) == 12 and digits.startswith("998"):
        return f"+{digits}"
    if len(digits) >= 9:
        # Take last 9 digits and prepend +998
        return f"+998{digits[-9:]}"
    return ""
