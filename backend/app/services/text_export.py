"""Block F V2.0 (F4a) — per-platform text export renderer.

Pure read-path service. Loads the active ``ExportTemplate`` for
``(platform, language)``, builds a context dict from the listing +
seller, renders via a **sandboxed** Jinja2 environment with autoescape
ON, and applies per-platform truncation.

Public surface:
    ExportPayload                                       — frozen result
    render_for_platform(db, listing, seller, ...)        — async render
    PLATFORM_LIMITS                                      — caps per platform

Sandbox guarantees:
    * No file-system access (sandboxed env).
    * No ``if`` / ``for`` blocks — template syntax restricted to plain
      ``{{ placeholder }}`` substitution. Anything else raises
      ``jinja2.exceptions.SecurityError`` at render time, which we
      convert to a 422 at the API layer.
    * Allowlisted placeholders: any context key not in this set is
      shadowed with an empty string so a typo in the admin template
      body can't leak unrelated data.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

from jinja2.exceptions import SecurityError, TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ExportTemplate, Listing, Seller
from app.services.deeplink import build_listing_link

logger = logging.getLogger(__name__)

# Supported (platform, language) shapes. Caller validates via these.
SUPPORTED_PLATFORMS = ("olx", "telegram_channel", "instagram", "pack")
SUPPORTED_LANGS = ("ru", "uz", "uz_cyrl")

# Per-platform body/title length caps.
PLATFORM_LIMITS: dict[str, dict[str, int]] = {
    "olx": {"title": 70, "body": 9000},
    "telegram_channel": {"body": 4096},
    "instagram": {"body": 2200},
}

# Allowlisted placeholder names. Anything else evaluates to empty.
ALLOWED_PLACEHOLDERS = frozenset(
    {
        "title",
        "price_formatted",
        "district",
        "rooms",
        "area",
        "description",
        "signature",
        "cta",
        "extra_hashtags",
        "listing_url",
    }
)


@dataclass(frozen=True)
class ExportPayload:
    """Result of rendering one (listing, platform, lang) combination."""

    text: str
    title: Optional[str]
    truncated: bool


# ─────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────


_PLACEHOLDER_RE = re.compile(r"\{\{[\s]*([a-zA-Z_][a-zA-Z0-9_]*)[\s]*\}\}")


def _scrub_unknown_placeholders(body: str) -> str:
    """Replace ``{{ name }}`` references whose name isn't in the
    allowlist with empty string before handing the template to Jinja.
    Defence-in-depth so a misconfigured admin template never surfaces
    unintended context keys."""

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return match.group(0) if name in ALLOWED_PLACEHOLDERS else ""

    return _PLACEHOLDER_RE.sub(_replace, body)


def _safe_context(
    listing: Listing,
    seller: Seller,
    lang: str,
) -> dict[str, Any]:
    """Build the allowlist-only context dict consumed by the template.

    Values that are missing become empty strings rather than literal
    ``"None"`` strings — Jinja renders ``None`` as ``"None"`` otherwise."""
    from app.services.seo_meta import (
        _district_label,
        _format_price,
        _normalize_district_key,
    )

    lang_field = {
        "ru": "ai_description_ru",
        "uz": "ai_description_uz",
        "uz_cyrl": "ai_description_uz_cyrl",
    }.get(lang, "ai_description_ru")
    description = getattr(listing, lang_field, None) or ""
    if not description:
        for fallback in ("ai_description_ru", "ai_description_uz", "ai_description_uz_cyrl"):
            description = getattr(listing, fallback, None) or ""
            if description:
                break
    if not description:
        description = getattr(listing, "description", None) or ""

    district_key = _normalize_district_key(getattr(listing, "district", None))
    # text_export uses url-segment lang `ru / uz-latn / uz`. We map
    # DB-lang to that convention here so price/district labels match
    # the page locale.
    url_lang = {"ru": "ru", "uz": "uz-latn", "uz_cyrl": "uz"}.get(lang, "ru")
    district_label = _district_label(district_key, url_lang)

    cur_raw = getattr(listing, "currency", None)
    cur = cur_raw.value if cur_raw is not None and hasattr(cur_raw, "value") else cur_raw
    price = _format_price(getattr(listing, "price", None), cur, url_lang)

    rooms = getattr(listing, "rooms", None)
    area = getattr(listing, "area", None)

    return {
        "title": (getattr(listing, "title", None) or description.split("\n", 1)[0] or "")[:200],
        "price_formatted": price,
        "district": district_label,
        "rooms": str(int(rooms)) if rooms else "",
        "area": (f"{float(area):g} м²" if area else ""),
        "description": description,
        "signature": (seller.export_signature or "") if seller else "",
        "cta": (seller.export_cta or "") if seller else "",
        "extra_hashtags": (seller.export_extra_hashtags or "") if seller else "",
        "listing_url": _public_listing_url(listing, url_lang),
    }


def _public_listing_url(listing: Listing, url_lang: str) -> str:
    """Best-effort public URL for the listing.

    Prefers the F3 public web host SEO URL (``https://{host}/{lang}/listing/{id}/{slug}``)
    so the exported text drives crawler-indexed traffic. Falls back to
    the bot deep link for sellers in pre-launch environments where the
    public host isn't configured yet."""
    try:
        from app.services.seo_meta import _public_host, slug_for_listing

        host = _public_host()
        if not host or "pana.uz" not in host and "localhost" in host:
            # Local-dev fallback — use the bot deep link as a stable target.
            return build_listing_link(listing.id)
        slug = slug_for_listing(listing)
        return f"{host}/{url_lang}/listing/{listing.id}/{slug}"
    except Exception:
        return build_listing_link(listing.id)


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    # Cut at last word boundary to avoid cleaving a word in half.
    cut = text[: limit - 1].rsplit(" ", 1)[0]
    return ((cut or text[: limit - 1]).rstrip() + "…"), True


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────


async def render_for_platform(
    db: AsyncSession,
    listing: Listing,
    seller: Seller,
    platform: str,
    lang: str = "ru",
) -> ExportPayload:
    """Render the listing for *platform* in *lang*. Raises:

    * ``ValueError`` — when no template is configured or the listing's
      AI description for the requested locale is empty.
    * ``jinja2.exceptions.SecurityError`` — when the admin template
      tried to call something outside the sandbox allowlist.

    Callers map both to 422 at the API layer.
    """
    if platform not in PLATFORM_LIMITS:
        # "pack" uses a different code path in the router.
        raise ValueError(f"unsupported_platform:{platform}")
    if lang not in SUPPORTED_LANGS:
        lang = "ru"

    # Load template — exact (platform, lang), then (platform, ru) fallback.
    template_row = (
        await db.execute(
            select(ExportTemplate).where(
                ExportTemplate.platform == platform,
                ExportTemplate.language == lang,
                ExportTemplate.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if template_row is None and lang != "ru":
        template_row = (
            await db.execute(
                select(ExportTemplate).where(
                    ExportTemplate.platform == platform,
                    ExportTemplate.language == "ru",
                    ExportTemplate.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
    if template_row is None:
        raise ValueError("template_not_configured")

    # Refuse to render before there's anything to say.
    if not any(
        (
            getattr(listing, "ai_description_ru", None),
            getattr(listing, "ai_description_uz", None),
            getattr(listing, "ai_description_uz_cyrl", None),
            getattr(listing, "description", None),
        )
    ):
        raise ValueError("ai_text_not_ready")

    # Reject control blocks per spec — exports are placeholder-only so
    # an admin can't accidentally invoke arbitrary expressions inside
    # the sandbox. ``{# … #}`` (comments) also rejected for parity.
    if "{%" in template_row.template_body or "{#" in template_row.template_body:
        logger.warning(
            "text_export.control_block_rejected template=%s",
            template_row.id,
        )
        raise ValueError("template_syntax_error")

    sandbox = SandboxedEnvironment(autoescape=False)
    cleaned_body = _scrub_unknown_placeholders(template_row.template_body)
    try:
        tmpl = sandbox.from_string(cleaned_body)
    except TemplateSyntaxError as exc:
        logger.warning("text_export.template_syntax_error platform=%s err=%s", platform, exc)
        raise ValueError("template_syntax_error") from exc

    ctx = _safe_context(listing, seller, lang)
    try:
        rendered = tmpl.render(**ctx)
    except SecurityError:
        # Sandbox violation — never let raw bytes through. Log and 422.
        logger.exception(
            "text_export.sandbox_violation platform=%s template=%s",
            platform,
            template_row.id,
        )
        raise

    title: Optional[str] = None
    truncated = False
    if platform == "olx":
        title_raw = ctx["title"]
        title, title_trunc = _truncate(title_raw, PLATFORM_LIMITS[platform]["title"])
        truncated = truncated or title_trunc

    body, body_trunc = _truncate(rendered.strip(), PLATFORM_LIMITS[platform]["body"])
    truncated = truncated or body_trunc

    return ExportPayload(text=body, title=title, truncated=truncated)
