"""Block phase-2 — marketing banners (public read + admin CRUD).

Two sub-routers in one module:

* ``public_router`` — mounted at ``/banners``. Buyer pages call:
    - ``GET /banners/active?placement=&lang=``
    - ``POST /banners/active/{id}/click``

* ``admin_router`` — mounted at ``/admin/banners``. Admin console calls:
    - ``GET /admin/banners``
    - ``POST /admin/banners``
    - ``PATCH /admin/banners/{id}``
    - ``DELETE /admin/banners/{id}`` (soft delete: ``is_active=False``)

Impression counters are bumped best-effort on the public list endpoint.
A failure to bump impressions never breaks the read response.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_admin
from app.core.exceptions import NotFoundException
from app.db.database import get_db
from app.db.models import Banner, User

logger = logging.getLogger(__name__)

public_router = APIRouter()
admin_router = APIRouter()


# ── allowed placements / languages ──────────────────────────────────
ALLOWED_PLACEMENTS = {"home_top", "home_inline", "listing_inline"}
ALLOWED_LANGUAGES = {"ru", "uz", "uz_cyrl", "*"}


# ── schemas ─────────────────────────────────────────────────────────


class BannerOut(BaseModel):
    """Public-safe banner shape."""

    id: str
    title: str
    image_url: str
    target_url: str
    placement: str
    language: str
    is_active: bool
    starts_at: datetime
    ends_at: Optional[datetime]
    impressions: int
    clicks: int
    created_at: datetime


class BannerPublicOut(BaseModel):
    """Compact shape returned to public buyer pages."""

    id: str
    title: str
    image_url: str
    target_url: str
    placement: str
    language: str


class BannerCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    image_url: str = Field(..., min_length=1, max_length=500)
    target_url: str = Field(..., min_length=1, max_length=500)
    placement: str = Field(..., pattern="^(home_top|home_inline|listing_inline)$")
    language: str = Field(..., pattern="^(ru|uz|uz_cyrl|\\*)$")
    is_active: bool = True
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class BannerUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    image_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    target_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    placement: Optional[str] = Field(
        default=None, pattern="^(home_top|home_inline|listing_inline)$"
    )
    language: Optional[str] = Field(
        default=None, pattern="^(ru|uz|uz_cyrl|\\*)$"
    )
    is_active: Optional[bool] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


# ── helpers ─────────────────────────────────────────────────────────


def _serialize(b: Banner) -> BannerOut:
    return BannerOut(
        id=str(b.id),
        title=b.title,
        image_url=b.image_url,
        target_url=b.target_url,
        placement=b.placement,
        language=b.language,
        is_active=b.is_active,
        starts_at=b.starts_at,
        ends_at=b.ends_at,
        impressions=b.impressions or 0,
        clicks=b.clicks or 0,
        created_at=b.created_at,
    )


# ── public endpoints ────────────────────────────────────────────────


@public_router.get(
    "/active",
    response_model=List[BannerPublicOut],
    summary="List active banners for a placement (public, no auth)",
)
async def list_active_banners(
    placement: str = Query(...),
    lang: str = Query("ru"),
    db: AsyncSession = Depends(get_db),
) -> List[BannerPublicOut]:
    """Return active, in-window banners for ``placement`` + ``lang``.

    Includes wildcard-language rows (``language='*'``) so admins can ship
    multilingual creative without duplicating rows. Best-effort impression
    counter bump on each returned row.
    """
    if placement not in ALLOWED_PLACEMENTS:
        return []
    now = datetime.utcnow()
    result = await db.execute(
        select(Banner)
        .where(
            Banner.is_active.is_(True),
            Banner.placement == placement,
            or_(Banner.language == lang, Banner.language == "*"),
            Banner.starts_at <= now,
            or_(Banner.ends_at.is_(None), Banner.ends_at > now),
        )
        .order_by(Banner.created_at.desc())
    )
    rows = list(result.scalars().all())

    # Best-effort impression bump. Wrapped to never fail the response.
    if rows:
        try:
            ids = [r.id for r in rows]
            await db.execute(
                update(Banner)
                .where(Banner.id.in_(ids))
                .values(impressions=Banner.impressions + 1)
            )
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("banner impression bump failed: %s", exc)
            await db.rollback()

    return [
        BannerPublicOut(
            id=str(r.id),
            title=r.title,
            image_url=r.image_url,
            target_url=r.target_url,
            placement=r.placement,
            language=r.language,
        )
        for r in rows
    ]


@public_router.post(
    "/active/{banner_id}/click",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Record a banner click (public, no auth)",
)
async def record_banner_click(
    banner_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Increment the click counter. Best-effort — silent 204 either way
    so a hostile/missing banner id doesn't leak through to the buyer UX."""
    try:
        await db.execute(
            update(Banner)
            .where(Banner.id == banner_id)
            .values(clicks=Banner.clicks + 1)
        )
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("banner click bump failed: %s", exc)
        await db.rollback()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── admin endpoints ─────────────────────────────────────────────────


@admin_router.get(
    "/banners",
    response_model=List[BannerOut],
    summary="List all banners (admin)",
)
async def admin_list_banners(
    placement: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> List[BannerOut]:
    stmt = select(Banner).order_by(Banner.created_at.desc())
    if placement:
        stmt = stmt.where(Banner.placement == placement)
    stmt = stmt.limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize(b) for b in rows]


@admin_router.post(
    "/banners",
    response_model=BannerOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a banner (admin)",
)
async def admin_create_banner(
    body: BannerCreate,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> BannerOut:
    banner = Banner(
        title=body.title,
        image_url=body.image_url,
        target_url=body.target_url,
        placement=body.placement,
        language=body.language,
        is_active=body.is_active,
        starts_at=body.starts_at or datetime.utcnow(),
        ends_at=body.ends_at,
    )
    db.add(banner)
    await db.commit()
    await db.refresh(banner)
    return _serialize(banner)


@admin_router.patch(
    "/banners/{banner_id}",
    response_model=BannerOut,
    summary="Update a banner (admin)",
)
async def admin_update_banner(
    banner_id: UUID,
    body: BannerUpdate,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> BannerOut:
    banner = (
        await db.execute(select(Banner).where(Banner.id == banner_id))
    ).scalar_one_or_none()
    if banner is None:
        raise NotFoundException("Banner", str(banner_id))

    updates = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(banner, k, v)
    await db.commit()
    await db.refresh(banner)
    return _serialize(banner)


@admin_router.delete(
    "/banners/{banner_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete (deactivate) a banner (admin)",
)
async def admin_delete_banner(
    banner_id: UUID,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    banner = (
        await db.execute(select(Banner).where(Banner.id == banner_id))
    ).scalar_one_or_none()
    if banner is None:
        raise NotFoundException("Banner", str(banner_id))
    banner.is_active = False
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
