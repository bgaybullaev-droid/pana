"""Block D (FU3) — admin CRUD for the bot rate-limit settings.

Two endpoints under ``/admin/bot-rate-limits``:
    GET  /admin/bot-rate-limits   — current settings (defaults if unseeded)
    PUT  /admin/bot-rate-limits   — update the singleton row + warm the cache

The bot enforces these limits through a short-TTL Redis cache; ``PUT``
write-throughs that cache so an edit takes effect immediately instead of
waiting out the TTL.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.api.v1.deps import get_current_admin
from app.bot.rate_limit import RateLimitConfig, publish_config_cache
from app.db.database import get_db
from app.db.models import BotRateLimitSettings, User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/bot-rate-limits", tags=["Admin — Bot Rate Limits (D/FU3)"]
)

_DEFAULTS = RateLimitConfig()


class BotRateLimitSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    search_enabled: bool
    search_limit: int
    search_window_sec: int
    inline_enabled: bool
    inline_limit: int
    inline_window_sec: int
    limit_message_ru: str
    limit_message_uz: str
    limit_message_uz_cyrl: str
    updated_at: Optional[datetime] = None


class BotRateLimitSettingsUpdate(BaseModel):
    search_enabled: bool
    search_limit: int = Field(..., ge=1, le=10_000)
    search_window_sec: int = Field(..., ge=1, le=3_600)
    inline_enabled: bool
    inline_limit: int = Field(..., ge=1, le=10_000)
    inline_window_sec: int = Field(..., ge=1, le=3_600)
    limit_message_ru: str = Field(..., min_length=1, max_length=500)
    limit_message_uz: str = Field(..., min_length=1, max_length=500)
    limit_message_uz_cyrl: str = Field(..., min_length=1, max_length=500)


def _config_from_row(row: BotRateLimitSettings) -> RateLimitConfig:
    return RateLimitConfig(
        search_enabled=row.search_enabled,
        search_limit=row.search_limit,
        search_window_sec=row.search_window_sec,
        inline_enabled=row.inline_enabled,
        inline_limit=row.inline_limit,
        inline_window_sec=row.inline_window_sec,
        limit_message_ru=row.limit_message_ru,
        limit_message_uz=row.limit_message_uz,
        limit_message_uz_cyrl=row.limit_message_uz_cyrl,
    )


@router.get("", response_model=BotRateLimitSettingsResponse)
async def get_bot_rate_limits(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> BotRateLimitSettingsResponse:
    row = (
        await db.execute(
            select(BotRateLimitSettings).where(BotRateLimitSettings.id == 1)
        )
    ).scalar_one_or_none()
    if row is None:
        # Unseeded (e.g. migration not yet applied) — surface defaults so the
        # form still renders pre-filled instead of erroring.
        return BotRateLimitSettingsResponse(
            search_enabled=_DEFAULTS.search_enabled,
            search_limit=_DEFAULTS.search_limit,
            search_window_sec=_DEFAULTS.search_window_sec,
            inline_enabled=_DEFAULTS.inline_enabled,
            inline_limit=_DEFAULTS.inline_limit,
            inline_window_sec=_DEFAULTS.inline_window_sec,
            limit_message_ru=_DEFAULTS.limit_message_ru,
            limit_message_uz=_DEFAULTS.limit_message_uz,
            limit_message_uz_cyrl=_DEFAULTS.limit_message_uz_cyrl,
        )
    return BotRateLimitSettingsResponse.model_validate(row)


@router.put("", response_model=BotRateLimitSettingsResponse)
async def update_bot_rate_limits(
    payload: BotRateLimitSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> BotRateLimitSettingsResponse:
    data = payload.model_dump()
    update_values = {**data, "updated_by_admin_id": admin.id, "updated_at": func.now()}
    stmt = (
        pg_insert(BotRateLimitSettings)
        .values(id=1, **data, updated_by_admin_id=admin.id)
        .on_conflict_do_update(index_elements=["id"], set_=update_values)
        .returning(BotRateLimitSettings)
    )
    row = (await db.execute(stmt)).scalar_one()
    await db.commit()

    # Write-through the bot's Redis cache so the change applies immediately;
    # cache failure is non-fatal (the TTL fallback re-reads the DB).
    try:
        await publish_config_cache(_config_from_row(row))
    except Exception:
        logger.warning("admin.bot_rate_limits: cache warm failed", exc_info=True)

    logger.info("admin.bot_rate_limits.updated by_admin=%s", admin.id)
    return BotRateLimitSettingsResponse.model_validate(row)
