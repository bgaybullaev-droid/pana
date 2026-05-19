"""Block F V2.0 (F3a) — SEO metadata + slug + JSON-LD builders.

Pure functions, no I/O. The SEO router (F3b) and template layer
consume these to render `<head>` content and structured data.

Public surface:
    SEOMeta                         — frozen dataclass for HTML head
    build_listing_meta(l, lang)     — title / description / OG / canonical
    build_filter_meta(filters, lang)— filter-page meta
    build_listing_jsonld(l, lang)   — schema.org RealEstateListing dict
    slug_for_listing(l, lang)       — deterministic Latin URL slug

Language-code conventions (per Block F V2.0 §F3 robots.txt mapping):
    URL `ru`       → `Listing.ai_description_ru`
    URL `uz`       → `Listing.ai_description_uz_cyrl` (Cyrillic default)
    URL `uz-latn`  → `Listing.ai_description_uz`      (Latin variant)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from app.core.config import settings
from app.core.regions import DISTRICT_TO_REGION, _DISTRICT_ALIASES
from app.db.models import Listing, ListingType, PropertyType

# Public-facing URL path segments per F3 spec.
SUPPORTED_LANGS: tuple[str, ...] = ("ru", "uz", "uz-latn")

# Map URL lang segment → DB column suffix on Listing.ai_description_*.
_LANG_TO_AI_FIELD: dict[str, str] = {
    "ru": "ai_description_ru",
    "uz": "ai_description_uz_cyrl",
    "uz-latn": "ai_description_uz",
}

# Russian/Cyrillic + Latin display labels for districts. Anything not
# present falls back to a title-cased version of the canonical district
# key (which is already Latin / ASCII-safe).
_DISTRICT_LABELS_RU: dict[str, str] = {
    "bektemir": "Бектемире",
    "chilonzor": "Чиланзаре",
    "mirzo_ulugbek": "Мирзо-Улугбекском районе",
    "mirobod": "Мирабадском районе",
    "olmazor": "Алмазарском районе",
    "sergeli": "Сергелийском районе",
    "shayxontohur": "Шайхантахурском районе",
    "uchtepa": "Учтепинском районе",
    "yakkasaroy": "Яккасарайском районе",
    "yashnobod": "Яшнабадском районе",
    "yunusobod": "Юнусабаде",
    # Regional cities — most-common queries.
    "andijon_sh": "Андижане",
    "buxoro_sh": "Бухаре",
    "fargona_sh": "Фергане",
    "namangan_sh": "Намангане",
    "navoiy_sh": "Навои",
    "nukus_sh": "Нукусе",
    "qarshi_sh": "Карши",
    "samarqand_sh": "Самарканде",
    "termiz_sh": "Термезе",
    "urganch_sh": "Ургенче",
    "guliston_sh": "Гулистане",
    "jizzax_sh": "Джизаке",
}

_DISTRICT_LABELS_UZ_LATN: dict[str, str] = {
    "bektemir": "Bektemir tumani",
    "chilonzor": "Chilonzor tumani",
    "mirzo_ulugbek": "Mirzo Ulug'bek tumani",
    "mirobod": "Mirobod tumani",
    "olmazor": "Olmazor tumani",
    "sergeli": "Sergeli tumani",
    "shayxontohur": "Shayxontohur tumani",
    "uchtepa": "Uchtepa tumani",
    "yakkasaroy": "Yakkasaroy tumani",
    "yashnobod": "Yashnobod tumani",
    "yunusobod": "Yunusobod tumani",
    "andijon_sh": "Andijon shahri",
    "buxoro_sh": "Buxoro shahri",
    "fargona_sh": "Farg'ona shahri",
    "namangan_sh": "Namangan shahri",
    "navoiy_sh": "Navoiy shahri",
    "nukus_sh": "Nukus shahri",
    "qarshi_sh": "Qarshi shahri",
    "samarqand_sh": "Samarqand shahri",
    "termiz_sh": "Termiz shahri",
    "urganch_sh": "Urganch shahri",
    "guliston_sh": "Guliston shahri",
    "jizzax_sh": "Jizzax shahri",
}

_DISTRICT_LABELS_UZ_CYRL: dict[str, str] = {
    "bektemir": "Бектемир тумани",
    "chilonzor": "Чилонзор тумани",
    "mirzo_ulugbek": "Мирзо Улуғбек тумани",
    "mirobod": "Миробод тумани",
    "olmazor": "Олмазор тумани",
    "sergeli": "Сергели тумани",
    "shayxontohur": "Шайхонтохур тумани",
    "uchtepa": "Учтепа тумани",
    "yakkasaroy": "Яккасарой тумани",
    "yashnobod": "Яшнобод тумани",
    "yunusobod": "Юнусобод тумани",
    "andijon_sh": "Андижон шаҳри",
    "buxoro_sh": "Бухоро шаҳри",
    "fargona_sh": "Фарғона шаҳри",
    "namangan_sh": "Наманган шаҳри",
    "navoiy_sh": "Навоий шаҳри",
    "nukus_sh": "Нукус шаҳри",
    "qarshi_sh": "Қарши шаҳри",
    "samarqand_sh": "Самарқанд шаҳри",
    "termiz_sh": "Термиз шаҳри",
    "urganch_sh": "Урганч шаҳри",
    "guliston_sh": "Гулистон шаҳри",
    "jizzax_sh": "Жиззах шаҳри",
}

# Per-locale fixed strings.
_BRAND_NAME = "UcharMarket"
_DEAL_LABELS: dict[tuple[str, str], str] = {
    # (deal_type, lang) → display fragment used in titles
    ("sell", "ru"): "Продажа",
    ("rent", "ru"): "Аренда",
    ("sell", "uz"): "Сотиш",
    ("rent", "uz"): "Ижара",
    ("sell", "uz-latn"): "Sotish",
    ("rent", "uz-latn"): "Ijara",
}
_PROPERTY_LABELS: dict[tuple[str, str], str] = {
    ("apartment", "ru"): "квартиры",
    ("house", "ru"): "дома",
    ("commercial", "ru"): "коммерческой недвижимости",
    ("land", "ru"): "земельного участка",
    ("apartment", "uz"): "квартираларни",
    ("house", "uz"): "уйларни",
    ("commercial", "uz"): "тижорат кўчмас мулкини",
    ("land", "uz"): "ер участкаларини",
    ("apartment", "uz-latn"): "kvartiralarini",
    ("house", "uz-latn"): "uylarini",
    ("commercial", "uz-latn"): "tijorat ko'chmas mulkini",
    ("land", "uz-latn"): "yer uchastkalarini",
}
_CURRENCY_SHORT_RU: dict[str, str] = {"USD": "у.е.", "UZS": "сум"}
_CURRENCY_SHORT_UZ: dict[str, str] = {"USD": "у.е.", "UZS": "сўм"}
_CURRENCY_SHORT_UZ_LATN: dict[str, str] = {"USD": "y.e.", "UZS": "so'm"}

# Maximum lengths per SEO best practice (Google truncates beyond these).
_MAX_TITLE_LEN = 60
_MAX_DESCRIPTION_LEN = 160


@dataclass(frozen=True)
class SEOMeta:
    """Frozen, template-safe container for `<head>` metadata."""

    title: str
    description: str
    og_title: str
    og_description: str
    og_image: Optional[str]
    canonical: str
    # IETF lang code (`ru`, `uz`, `uz-latn`, `x-default`) → absolute URL.
    hreflang: Mapping[str, str] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _normalize_district_key(district: Optional[str]) -> Optional[str]:
    """Return the canonical district key for a free-form district string.

    Returns ``None`` if the district can't be normalized. Used by every
    helper here to converge to one ``_DISTRICT_TO_REGION``-compatible
    identifier regardless of the input casing/script.
    """
    if not district:
        return None
    if district in DISTRICT_TO_REGION:
        return district
    normalized = district.lower().strip()
    if alias := _DISTRICT_ALIASES.get(normalized):
        if alias in DISTRICT_TO_REGION:
            return alias
    slug = (
        normalized.replace(" ", "_")
        .replace("'", "_")
        .replace("’", "_")
        .replace("-", "_")
    )
    if slug in DISTRICT_TO_REGION:
        return slug
    return None


def _district_label(district_key: Optional[str], lang: str) -> str:
    """Display label for a district in the requested locale."""
    if not district_key:
        return ""
    if lang == "ru":
        return _DISTRICT_LABELS_RU.get(district_key, district_key.replace("_", " ").title())
    if lang == "uz-latn":
        return _DISTRICT_LABELS_UZ_LATN.get(district_key, district_key.replace("_", " ").title())
    # default uz (Cyrillic)
    return _DISTRICT_LABELS_UZ_CYRL.get(district_key, district_key.replace("_", " ").title())


def _truncate(text: str, max_len: int) -> str:
    """Trim *text* to *max_len* preserving word boundaries when possible."""
    if not text:
        return ""
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[:max_len].rsplit(" ", 1)[0]
    return (cut or cleaned[:max_len]).rstrip()


def _ai_description(listing: Listing, lang: str) -> str:
    """Pick the AI-generated description in the page's URL language.

    Falls back across the other locales so a missing translation never
    produces an empty `description` meta — Google penalises stub pages.
    """
    field_name = _LANG_TO_AI_FIELD.get(lang, "ai_description_ru")
    primary = getattr(listing, field_name, None) or ""
    if primary:
        return primary
    for fallback in ("ai_description_ru", "ai_description_uz", "ai_description_uz_cyrl"):
        value = getattr(listing, fallback, None) or ""
        if value:
            return value
    # Final fallback: any seller-typed description.
    return getattr(listing, "description", None) or ""


def _primary_image_url(listing: Listing) -> Optional[str]:
    """Absolute URL of the primary photo or first image; None if none."""
    images = getattr(listing, "images", None) or []
    if not images:
        return None
    primary = next((img for img in images if getattr(img, "is_primary", False)), None)
    if primary is None:
        primary = min(images, key=lambda img: getattr(img, "position", 0) or 0)
    return (
        getattr(primary, "large_url", None)
        or getattr(primary, "medium_url", None)
        or getattr(primary, "original_url", None)
    )


def _format_price(price: Optional[int], currency: Optional[str], lang: str) -> str:
    if price is None or price <= 0:
        return ""
    cur_map = {
        "ru": _CURRENCY_SHORT_RU,
        "uz": _CURRENCY_SHORT_UZ,
        "uz-latn": _CURRENCY_SHORT_UZ_LATN,
    }.get(lang, _CURRENCY_SHORT_RU)
    cur_str = cur_map.get((currency or "USD").upper(), currency or "")
    # Use thin-space (U+202F) thousand separator — Cyrillic typography
    # convention; renders cleanly in all 3 locales.
    formatted = f"{price:,}".replace(",", " ")
    return f"{formatted} {cur_str}".strip()


def _public_host() -> str:
    """Normalized public web host (no trailing slash)."""
    return settings.f3_public_web_host.rstrip("/")


# ─────────────────────────────────────────────────────────────────────
# Slugs
# ─────────────────────────────────────────────────────────────────────


_SLUG_MAX = 30
_SLUG_SAFE = re.compile(r"[^a-z0-9-]+")


def slug_for_listing(listing: Listing, lang: str = "ru") -> str:
    """Deterministic, URL-safe, Latin-only slug for a listing.

    Shape: ``<rooms>-rooms-<district-latin>`` truncated to 30 chars.
    Latin-only so the slug is identical across all three locales —
    matches Google's preference for one canonical URL per content
    regardless of `<link rel="alternate">` hreflang variants.

    Examples (district key already Latin):
        rooms=3, district="chilonzor"  → "3-rooms-chilonzor"
        rooms=None, district="sergeli" → "sergeli"
        rooms=2, district=None         → "2-rooms"
        anything fully empty           → "listing"
    """
    parts: list[str] = []
    rooms = getattr(listing, "rooms", None)
    if rooms is not None and rooms > 0:
        parts.append(f"{int(rooms)}-rooms")
    district_key = _normalize_district_key(getattr(listing, "district", None))
    if district_key:
        # Canonical district keys are already lowercase-Latin (_DISTRICT_TO_REGION).
        parts.append(district_key.replace("_", "-"))
    raw = "-".join(parts) or "listing"
    cleaned = _SLUG_SAFE.sub("-", raw.lower()).strip("-")
    return cleaned[:_SLUG_MAX].rstrip("-") or "listing"


# ─────────────────────────────────────────────────────────────────────
# URLs / canonical / hreflang
# ─────────────────────────────────────────────────────────────────────


def _listing_url(listing_id: Any, slug: str, lang: str) -> str:
    return f"{_public_host()}/{lang}/listing/{listing_id}/{slug}"


def _hreflang_for_listing(listing: Listing) -> dict[str, str]:
    """All three locale URLs + ``x-default`` for `<link rel="alternate">`.

    Slug is locale-independent (Latin-only), so the only thing that
    changes across locales is the ``/{lang}/`` path segment.
    """
    slug = slug_for_listing(listing)
    lid = listing.id
    return {
        "ru": _listing_url(lid, slug, "ru"),
        "uz": _listing_url(lid, slug, "uz"),
        "uz-latn": _listing_url(lid, slug, "uz-latn"),
        "x-default": _listing_url(lid, slug, "ru"),
    }


# ─────────────────────────────────────────────────────────────────────
# Title / description / og
# ─────────────────────────────────────────────────────────────────────


def _listing_title(listing: Listing, lang: str) -> str:
    """Compose a structured human title for the listing page.

    Examples (ru):
        "3-комн в Чиланзаре, 65 м², 35 000 у.е. — UcharMarket"
        "Дом в Самарканде, 120 м², 80 000 у.е. — UcharMarket"
    """
    bits: list[str] = []
    rooms = getattr(listing, "rooms", None)
    prop_type_raw = getattr(listing, "property_type", None)
    prop_type = (
        prop_type_raw.value if isinstance(prop_type_raw, PropertyType) else prop_type_raw
    )
    district_key = _normalize_district_key(getattr(listing, "district", None))
    district_label = _district_label(district_key, lang)
    area = getattr(listing, "area", None)
    price = _format_price(
        getattr(listing, "price", None),
        getattr(listing, "currency", None).value
        if getattr(listing, "currency", None) is not None
        and hasattr(getattr(listing, "currency", None), "value")
        else getattr(listing, "currency", None),
        lang,
    )

    if lang == "ru":
        if rooms and prop_type == "apartment":
            bits.append(f"{int(rooms)}-комн")
        elif prop_type == "house":
            bits.append("Дом")
        elif prop_type == "commercial":
            bits.append("Коммерческая недвижимость")
        elif prop_type == "land":
            bits.append("Участок")
        if district_label:
            bits.append(f"в {district_label}")
    elif lang == "uz-latn":
        if rooms and prop_type == "apartment":
            bits.append(f"{int(rooms)}-xonali kvartira")
        elif prop_type == "house":
            bits.append("Uy")
        elif prop_type == "commercial":
            bits.append("Tijorat ko'chmas mulk")
        elif prop_type == "land":
            bits.append("Yer uchastkasi")
        if district_label:
            bits.append(district_label)
    else:  # uz (Cyrillic)
        if rooms and prop_type == "apartment":
            bits.append(f"{int(rooms)}-хонали квартира")
        elif prop_type == "house":
            bits.append("Уй")
        elif prop_type == "commercial":
            bits.append("Тижорат кўчмас мулк")
        elif prop_type == "land":
            bits.append("Ер участкаси")
        if district_label:
            bits.append(district_label)

    # Spec title example: "3-комн в Чиланзаре, 65 м², 35 000 у.е." —
    # rooms + district join with a single space; the comma only
    # separates that head from the (area, price) tail.
    head = " ".join(b for b in bits if b)
    tail_bits: list[str] = []
    if area:
        try:
            area_val = float(area)
            if area_val > 0:
                tail_bits.append(
                    f"{int(area_val) if area_val.is_integer() else area_val:g} м²"
                    if lang == "ru"
                    else (f"{int(area_val) if area_val.is_integer() else area_val:g} m²")
                )
        except (TypeError, ValueError):
            pass
    if price:
        tail_bits.append(price)

    body = ", ".join(part for part in [head, *tail_bits] if part)
    full = f"{body} — {_BRAND_NAME}" if body else _BRAND_NAME
    return _truncate(full, _MAX_TITLE_LEN)


def build_listing_meta(listing: Listing, lang: str = "ru") -> SEOMeta:
    """Compose ``SEOMeta`` for a listing-detail page in *lang*."""
    if lang not in SUPPORTED_LANGS:
        lang = "ru"

    title = _listing_title(listing, lang)
    raw_description = _ai_description(listing, lang)
    description = _truncate(raw_description, _MAX_DESCRIPTION_LEN) or title
    image = _primary_image_url(listing)
    slug = slug_for_listing(listing)
    canonical = _listing_url(listing.id, slug, lang)

    return SEOMeta(
        title=title,
        description=description,
        og_title=title,
        og_description=description,
        og_image=image,
        canonical=canonical,
        hreflang=_hreflang_for_listing(listing),
    )


def build_filter_meta(filters: Mapping[str, Any], lang: str = "ru") -> SEOMeta:
    """Compose ``SEOMeta`` for a filter / landing page.

    Filter dict accepts (all optional): ``deal`` (sell|rent),
    ``property_type`` (apartment|house|commercial|land),
    ``district`` (canonical key or alias), ``rooms`` (int), ``page`` (int).
    """
    if lang not in SUPPORTED_LANGS:
        lang = "ru"

    deal = (filters.get("deal") or "").lower() or None
    if isinstance(deal, str) and deal in ("sale",):  # accept "sale" as alias
        deal = "sell"
    prop = (filters.get("property_type") or "").lower() or None
    district_key = _normalize_district_key(filters.get("district"))
    rooms = filters.get("rooms")
    try:
        rooms_int = int(rooms) if rooms not in (None, "") else None
    except (TypeError, ValueError):
        rooms_int = None

    fragments: list[str] = []
    if deal and (deal, lang) in _DEAL_LABELS:
        fragments.append(_DEAL_LABELS[(deal, lang)])
    if prop and (prop, lang) in _PROPERTY_LABELS:
        fragments.append(_PROPERTY_LABELS[(prop, lang)])
    if rooms_int and rooms_int > 0:
        if lang == "ru":
            fragments.append(f"{rooms_int}-комн")
        elif lang == "uz-latn":
            fragments.append(f"{rooms_int}-xonali")
        else:
            fragments.append(f"{rooms_int}-хонали")
    if district_key:
        label = _district_label(district_key, lang)
        if label:
            fragments.append(
                f"в {label}" if lang == "ru" else f"{label}da" if lang == "uz-latn" else f"{label}да"
            )

    head = " ".join(f for f in fragments if f)
    base = head or (
        "Недвижимость" if lang == "ru" else
        "Ko'chmas mulk" if lang == "uz-latn" else
        "Кўчмас мулк"
    )
    title = _truncate(f"{base} — {_BRAND_NAME}", _MAX_TITLE_LEN)

    if lang == "ru":
        description = _truncate(
            f"Все объявления: {head} на UcharMarket. Свежие предложения от собственников и агентств.",
            _MAX_DESCRIPTION_LEN,
        )
    elif lang == "uz-latn":
        description = _truncate(
            f"Barcha e'lonlar: {head} UcharMarket'da. Egalari va agentliklardan yangi takliflar.",
            _MAX_DESCRIPTION_LEN,
        )
    else:
        description = _truncate(
            f"Барча эълонлар: {head} UcharMarket'да. Эгалари ва агентликлардан янги таклифлар.",
            _MAX_DESCRIPTION_LEN,
        )

    # Filter-page canonical: rebuild the path from the normalized filters
    # so e.g. ``/ru/sell/apartment/3-rooms/chilonzor``.
    canonical_path = _filter_canonical_path(lang, deal, prop, rooms_int, district_key)
    canonical = f"{_public_host()}{canonical_path}"
    hreflang = {
        lang_code: f"{_public_host()}{_filter_canonical_path(lang_code, deal, prop, rooms_int, district_key)}"
        for lang_code in SUPPORTED_LANGS
    }
    hreflang["x-default"] = hreflang["ru"]

    return SEOMeta(
        title=title,
        description=description,
        og_title=title,
        og_description=description,
        og_image=None,
        canonical=canonical,
        hreflang=hreflang,
    )


def _filter_canonical_path(
    lang: str,
    deal: Optional[str],
    prop: Optional[str],
    rooms: Optional[int],
    district_key: Optional[str],
) -> str:
    """Compose the URL path for a filter page given normalized inputs.

    Honors the 3-param-depth indexable rule from F3 spec:
        /{lang}                         (root — not generated here)
        /{lang}/tashkent/{district}     (district-only)
        /{lang}/{deal}/{type}           (deal × type)
        /{lang}/{deal}/{type}/{district}
        /{lang}/{deal}/{type}/{rooms}-rooms/{district}
    """
    if deal and prop and rooms and district_key:
        return f"/{lang}/{deal}/{prop}/{rooms}-rooms/{district_key.replace('_', '-')}"
    if deal and prop and district_key:
        return f"/{lang}/{deal}/{prop}/{district_key.replace('_', '-')}"
    if deal and prop:
        return f"/{lang}/{deal}/{prop}"
    if district_key:
        return f"/{lang}/tashkent/{district_key.replace('_', '-')}"
    return f"/{lang}/"


# ─────────────────────────────────────────────────────────────────────
# JSON-LD
# ─────────────────────────────────────────────────────────────────────


_PROPERTY_TYPE_TO_SCHEMA: dict[str, str] = {
    "apartment": "Apartment",
    "house": "House",
    "commercial": "CommercialProperty",
    "land": "LandPlot",
}


def _drop_nones(payload: Any) -> Any:
    """Recursively strip ``None`` / empty-dict values so the emitted
    JSON-LD never contains ``"key": null`` (Google Rich Results rejects
    those for several required RealEstateListing fields)."""
    if isinstance(payload, dict):
        cleaned = {k: _drop_nones(v) for k, v in payload.items() if v is not None}
        return {k: v for k, v in cleaned.items() if v not in ({}, [], "")}
    if isinstance(payload, list):
        return [_drop_nones(item) for item in payload if item is not None]
    return payload


def build_listing_jsonld(listing: Listing, lang: str = "ru") -> dict[str, Any]:
    """Emit a ``schema.org RealEstateListing`` payload for the page.

    Caller serialises with ``json.dumps(..., ensure_ascii=False)`` and
    drops the result into ``<script type="application/ld+json">``.

    Optional/missing fields are stripped so the payload always passes
    Google Rich Results validation.
    """
    if lang not in SUPPORTED_LANGS:
        lang = "ru"

    rooms = getattr(listing, "rooms", None)
    area = getattr(listing, "area", None)
    title = _listing_title(listing, lang)
    description = _ai_description(listing, lang) or title
    price = getattr(listing, "price", None)
    currency_raw = getattr(listing, "currency", None)
    currency = (
        currency_raw.value
        if currency_raw is not None and hasattr(currency_raw, "value")
        else currency_raw
    )
    image = _primary_image_url(listing)
    slug = slug_for_listing(listing)
    canonical = _listing_url(listing.id, slug, lang)

    prop_raw = getattr(listing, "property_type", None)
    prop = prop_raw.value if isinstance(prop_raw, PropertyType) else prop_raw
    sub_type = _PROPERTY_TYPE_TO_SCHEMA.get((prop or "").lower())

    type_raw = getattr(listing, "type", None)
    deal = type_raw.value if isinstance(type_raw, ListingType) else type_raw

    district_key = _normalize_district_key(getattr(listing, "district", None))
    region = getattr(listing, "region", None) or (
        DISTRICT_TO_REGION.get(district_key) if district_key else None
    )

    address: dict[str, Any] = {
        "@type": "PostalAddress",
        "addressCountry": "UZ",
        "addressLocality": _district_label(district_key, lang) or None,
        "addressRegion": region,
        "streetAddress": getattr(listing, "address", None) or None,
    }

    offers: dict[str, Any] = (
        {
            "@type": "Offer",
            "price": price,
            "priceCurrency": (currency or "").upper() or None,
            "availability": "https://schema.org/InStock",
            "url": canonical,
        }
        if price is not None and price > 0
        else {}
    )

    payload: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "RealEstateListing",
        "name": title,
        "description": _truncate(description, 5000),
        "url": canonical,
        "datePosted": (
            getattr(listing, "created_at", None).isoformat()
            if getattr(listing, "created_at", None) is not None
            else None
        ),
        "dateModified": (
            getattr(listing, "updated_at", None).isoformat()
            if getattr(listing, "updated_at", None) is not None
            else None
        ),
        "image": image,
        "address": address,
        "offers": offers,
        "numberOfRooms": int(rooms) if rooms else None,
        "floorSize": (
            {"@type": "QuantitativeValue", "value": float(area), "unitCode": "MTK"}
            if area is not None and area > 0
            else None
        ),
        "additionalType": sub_type,
        "transactionType": (
            "https://schema.org/Sale"
            if deal == "sell"
            else "https://schema.org/Rental"
            if deal == "rent"
            else None
        ),
    }
    return _drop_nones(payload)
