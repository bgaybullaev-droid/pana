"""Block F V2.0 (F4a) — seller-side cabinet exports.

Endpoints:
    GET   /seller/exports/{listing_id}/{platform}?lang=…  — render export
    GET   /seller/exports/settings                        — fetch overrides
    PATCH /seller/exports/settings                        — update overrides

All routes gate on Block D4's ``check_active_subscription(CABINET)``;
free users see 402 instead of the rendered payload.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_seller
from app.core.exceptions import NotFoundException
from app.db.database import get_db
from app.db.models import Listing, Seller, SubscriptionType
from app.services.subscriptions import check_active_subscription
from app.services.text_export import (
    PLATFORM_LIMITS,
    SUPPORTED_LANGS,
    SUPPORTED_PLATFORMS,
    ExportPayload,
    render_for_platform,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seller/exports", tags=["Seller Exports (F4)"])


# ─────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────


class ExportItem(BaseModel):
    platform: str
    text: str
    title: Optional[str] = None
    truncated: bool = False


class ExportResponse(BaseModel):
    """Single-platform response."""

    platform: str
    text: str
    title: Optional[str] = None
    truncated: bool = False


class ExportPackResponse(BaseModel):
    """Pack response: all three real platforms in one call."""

    items: list[ExportItem]


class ExportSettings(BaseModel):
    signature: Optional[str] = Field(default=None, max_length=500)
    cta: Optional[str] = Field(default=None, max_length=500)
    extra_hashtags: Optional[str] = Field(default=None, max_length=500)


# Reject Jinja2 placeholder syntax in seller-supplied fields.
_PLACEHOLDER_RE = re.compile(r"\{\{|\}\}|\{%|%\}")


def _reject_jinja(value: Optional[str]) -> None:
    if value is None:
        return
    if _PLACEHOLDER_RE.search(value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "jinja_placeholders_not_allowed"},
        )


# ─────────────────────────────────────────────────────────────────────
# Render endpoint
# ─────────────────────────────────────────────────────────────────────


@router.get(
    "/{listing_id}/{platform}",
    response_model=None,
    summary="Render listing for a platform (subscription-gated)",
)
async def render_export(
    listing_id: UUID,
    platform: str,
    lang: str = Query("ru", max_length=8),
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "unsupported_platform"},
        )
    if lang not in SUPPORTED_LANGS:
        lang = "ru"

    # Subscription gate first — fast-fail without DB read on the listing.
    allowed = await check_active_subscription(
        db, seller.user_id, sub_type=SubscriptionType.CABINET
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={"error": "subscription_required"},
        )

    listing = (
        await db.execute(
            select(Listing).where(
                Listing.id == listing_id,
                Listing.seller_id == seller.id,
                Listing.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if listing is None:
        raise NotFoundException("Listing", str(listing_id))

    try:
        if platform == "pack":
            items: list[ExportItem] = []
            for p in ("olx", "telegram_channel", "instagram"):
                payload = await render_for_platform(db, listing, seller, p, lang)
                items.append(
                    ExportItem(
                        platform=p,
                        text=payload.text,
                        title=payload.title,
                        truncated=payload.truncated,
                    )
                )
            return ExportPackResponse(items=items)

        payload: ExportPayload = await render_for_platform(
            db, listing, seller, platform, lang
        )
        return ExportResponse(
            platform=platform,
            text=payload.text,
            title=payload.title,
            truncated=payload.truncated,
        )
    except ValueError as exc:
        msg = str(exc)
        if msg == "ai_text_not_ready":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "ai_text_not_ready"},
            ) from exc
        if msg == "template_not_configured":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "template_not_configured"},
            ) from exc
        if msg == "template_syntax_error":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "template_syntax_error"},
            ) from exc
        raise


# ─────────────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────────────


@router.get("/settings", response_model=ExportSettings)
async def get_export_settings(
    seller: Seller = Depends(get_current_seller),
) -> ExportSettings:
    return ExportSettings(
        signature=seller.export_signature,
        cta=seller.export_cta,
        extra_hashtags=seller.export_extra_hashtags,
    )


@router.patch("/settings", response_model=ExportSettings)
async def update_export_settings(
    payload: ExportSettings,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> ExportSettings:
    _reject_jinja(payload.signature)
    _reject_jinja(payload.cta)
    _reject_jinja(payload.extra_hashtags)

    if payload.signature is not None:
        seller.export_signature = payload.signature.strip() or None
    if payload.cta is not None:
        seller.export_cta = payload.cta.strip() or None
    if payload.extra_hashtags is not None:
        seller.export_extra_hashtags = payload.extra_hashtags.strip() or None
    await db.commit()
    await db.refresh(seller)
    logger.info("export.settings_updated seller=%s", seller.id)
    return ExportSettings(
        signature=seller.export_signature,
        cta=seller.export_cta,
        extra_hashtags=seller.export_extra_hashtags,
    )


# Expose limits for the FE.
@router.get("/limits", include_in_schema=False)
async def get_limits():
    return PLATFORM_LIMITS
