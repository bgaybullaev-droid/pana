"""Block F V2.0 F4a — admin CRUD for export_templates.

Three endpoints under ``/admin/export-templates``:
    GET    /admin/export-templates              — list all rows
    POST   /admin/export-templates              — create (initially inactive)
    PATCH  /admin/export-templates/{id}         — update body + flip active
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_admin
from app.db.database import get_db
from app.db.models import ExportTemplate, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/export-templates", tags=["Admin Export Templates"])


class ExportTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    platform: str
    language: str
    template_body: str
    is_active: bool
    updated_at: datetime


class ExportTemplateCreate(BaseModel):
    platform: str = Field(..., max_length=32)
    language: str = Field(..., max_length=8)
    template_body: str = Field(..., min_length=1)


class ExportTemplateUpdate(BaseModel):
    template_body: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("", response_model=list[ExportTemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> list[ExportTemplateResponse]:
    rows = list(
        (
            await db.execute(
                select(ExportTemplate).order_by(
                    ExportTemplate.platform.asc(),
                    ExportTemplate.language.asc(),
                    ExportTemplate.updated_at.desc(),
                )
            )
        )
        .scalars()
        .all()
    )
    return [ExportTemplateResponse.model_validate(r) for r in rows]


@router.post(
    "",
    response_model=ExportTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    payload: ExportTemplateCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> ExportTemplateResponse:
    row = ExportTemplate(
        platform=payload.platform,
        language=payload.language,
        template_body=payload.template_body,
        is_active=False,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info(
        "admin.export_template_created id=%s platform=%s lang=%s by_admin=%s",
        row.id,
        row.platform,
        row.language,
        admin.id,
    )
    return ExportTemplateResponse.model_validate(row)


@router.patch(
    "/{template_id}", response_model=ExportTemplateResponse
)
async def update_template(
    template_id: UUID,
    payload: ExportTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> ExportTemplateResponse:
    target = (
        await db.execute(
            select(ExportTemplate).where(ExportTemplate.id == template_id)
        )
    ).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "template_not_found"},
        )

    # Plain field update.
    if payload.template_body is not None:
        target.template_body = payload.template_body

    # Activation: atomic flip across the (platform, language) group via
    # one UPDATE so the partial unique index never sees two active rows.
    if payload.is_active is True:
        await db.execute(
            ExportTemplate.__table__.update()
            .where(
                ExportTemplate.platform == target.platform,
                ExportTemplate.language == target.language,
            )
            .values(
                is_active=case(
                    (ExportTemplate.id == template_id, True), else_=False
                )
            )
        )
    elif payload.is_active is False:
        target.is_active = False

    await db.commit()
    await db.refresh(target)
    logger.info(
        "admin.export_template_updated id=%s active=%s by_admin=%s",
        target.id,
        target.is_active,
        admin.id,
    )
    return ExportTemplateResponse.model_validate(target)
