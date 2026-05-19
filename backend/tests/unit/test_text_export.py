"""Block F V2.0 F4a — text_export service unit tests.

Validates placeholder substitution, signature/CTA injection,
per-platform truncation, missing-AI-text rejection, control-block
rejection, and unknown-placeholder scrubbing.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.text_export import (
    ALLOWED_PLACEHOLDERS,
    PLATFORM_LIMITS,
    _scrub_unknown_placeholders,
    render_for_platform,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


def _listing(*, ai_ru: str = "Просторная квартира в Чиланзаре, 65 м².", title: str = ""):
    return SimpleNamespace(
        id=uuid4(),
        rooms=3,
        district="chilonzor",
        region="toshkent_shahri",
        area=65.0,
        price=35000,
        currency="USD",
        property_type="apartment",
        type="sell",
        title=title or None,
        ai_description_ru=ai_ru,
        ai_description_uz="Chilonzor tumanida kvartira.",
        ai_description_uz_cyrl="Чилонзор туманидаги квартира.",
        description=None,
        images=[],
        address=None,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 5, 1),
    )


def _seller(*, signature=None, cta=None, hashtags=None):
    return SimpleNamespace(
        id=uuid4(),
        export_signature=signature,
        export_cta=cta,
        export_extra_hashtags=hashtags,
    )


def _db_with_template(body: str, *, platform: str = "olx", lang: str = "ru"):
    async def fake_execute(stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = SimpleNamespace(
            id=uuid4(),
            platform=platform,
            language=lang,
            template_body=body,
            is_active=True,
        )
        return result

    db = MagicMock()
    db.execute = AsyncMock(side_effect=fake_execute)
    return db


class TestScrubPlaceholders:
    def test_allowed_passes_through(self):
        body = "Hi {{ title }} and {{ description }}."
        assert _scrub_unknown_placeholders(body) == body

    def test_unknown_replaced_with_empty(self):
        body = "Hi {{ title }} {{ secret_key }} done."
        out = _scrub_unknown_placeholders(body)
        assert "{{ secret_key }}" not in out
        assert "{{ title }}" in out

    def test_placeholder_whitespace_robust(self):
        for variant in ALLOWED_PLACEHOLDERS:
            body = f"{{{{{variant}}}}} {{{{ {variant} }}}}"
            out = _scrub_unknown_placeholders(body)
            assert variant in out


class TestRenderPlatform:
    async def test_simple_substitution(self):
        db = _db_with_template("{{ title }} — {{ price_formatted }}")
        listing = _listing(title="3-room flat")
        seller = _seller()
        payload = await render_for_platform(db, listing, seller, "olx", "ru")
        assert "3-room flat" in payload.text
        # ``_format_price`` joins with a thin-space (U+202F) per
        # Cyrillic typography; assert both digit clusters appear in
        # order rather than coupling the test to the separator char.
        assert "35" in payload.text and "000" in payload.text
        assert "у.е." in payload.text
        assert payload.truncated is False

    async def test_signature_and_cta_injected(self):
        db = _db_with_template("Body. {{ cta }} — {{ signature }}")
        listing = _listing()
        seller = _seller(signature="Best sellers ever", cta="Call us")
        payload = await render_for_platform(db, listing, seller, "olx", "ru")
        assert "Call us" in payload.text
        assert "Best sellers ever" in payload.text

    async def test_olx_title_truncation_flag(self):
        long_title = "T" * 200
        db = _db_with_template("{{ title }}")
        listing = _listing(title=long_title)
        seller = _seller()
        payload = await render_for_platform(db, listing, seller, "olx", "ru")
        assert payload.title is not None
        assert len(payload.title) <= PLATFORM_LIMITS["olx"]["title"]
        assert payload.truncated is True

    async def test_instagram_body_truncation_flag(self):
        body_text = "X" * (PLATFORM_LIMITS["instagram"]["body"] + 100)
        db = _db_with_template(body_text)
        listing = _listing()
        seller = _seller()
        payload = await render_for_platform(db, listing, seller, "instagram", "ru")
        assert payload.truncated is True
        assert len(payload.text) <= PLATFORM_LIMITS["instagram"]["body"]

    async def test_missing_ai_text_raises(self):
        db = _db_with_template("{{ description }}")
        listing = _listing(ai_ru="")
        # Force all AI fields empty too.
        listing.ai_description_ru = None
        listing.ai_description_uz = None
        listing.ai_description_uz_cyrl = None
        listing.description = None
        seller = _seller()
        with pytest.raises(ValueError) as exc_info:
            await render_for_platform(db, listing, seller, "olx", "ru")
        assert "ai_text_not_ready" in str(exc_info.value)

    async def test_control_block_rejected(self):
        db = _db_with_template("{% if title %}{{ title }}{% endif %}")
        listing = _listing()
        seller = _seller()
        with pytest.raises(ValueError) as exc_info:
            await render_for_platform(db, listing, seller, "olx", "ru")
        assert "template_syntax_error" in str(exc_info.value)

    async def test_unknown_placeholder_renders_empty(self):
        db = _db_with_template("Hi {{ title }} and {{ secret_method }}!")
        listing = _listing(title="Cosy flat")
        seller = _seller()
        payload = await render_for_platform(db, listing, seller, "olx", "ru")
        assert "Cosy flat" in payload.text
        assert "secret_method" not in payload.text
