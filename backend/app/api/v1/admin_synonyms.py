"""Block F V2.0 F2 — admin synonym dictionary CRUD.

Three endpoints under ``/admin/synonyms``:
    GET    /admin/synonyms          — paginated browse with filters
    POST   /admin/synonyms          — bulk insert with ON CONFLICT DO NOTHING
    DELETE /admin/synonyms/{id}     — remove one row

Designed for CSV-paste bulk import: the POST endpoint accepts a list
of entries, deduplicates against the existing dictionary via the
unique index, and returns whatever survived.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_admin
from app.db.database import get_db
from app.db.models import SynonymEntry, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/synonyms", tags=["Admin Synonyms"])


class SynonymEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parameter_key: str
    parameter_value: Optional[str]
    surface_form: str
    language: str
    polarity: str
    created_at: datetime


class SynonymEntryCreate(BaseModel):
    parameter_key: str = Field(..., min_length=1, max_length=64)
    parameter_value: Optional[str] = Field(default=None, max_length=64)
    surface_form: str = Field(..., min_length=1, max_length=128)
    language: str = Field(..., min_length=1, max_length=8)
    polarity: str = Field(default="positive", pattern="^(positive|negative)$")


class SynonymBulkCreate(BaseModel):
    entries: list[SynonymEntryCreate]


class SynonymBulkResponse(BaseModel):
    inserted: int
    skipped: int
    items: list[SynonymEntryResponse]


@router.get("", response_model=list[SynonymEntryResponse])
async def list_synonyms(
    parameter_key: Optional[str] = Query(default=None, max_length=64),
    language: Optional[str] = Query(default=None, max_length=8),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> list[SynonymEntryResponse]:
    stmt = select(SynonymEntry).order_by(
        SynonymEntry.parameter_key.asc(),
        SynonymEntry.language.asc(),
        SynonymEntry.surface_form.asc(),
    )
    if parameter_key:
        stmt = stmt.where(SynonymEntry.parameter_key == parameter_key)
    if language:
        stmt = stmt.where(SynonymEntry.language == language)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = list((await db.execute(stmt)).scalars().all())
    return [SynonymEntryResponse.model_validate(r) for r in rows]


@router.post(
    "",
    response_model=SynonymBulkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_synonyms(
    payload: SynonymBulkCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> SynonymBulkResponse:
    """Insert (or skip on duplicate) a batch of synonym entries.

    Conflict resolution is ``ON CONFLICT DO NOTHING`` against the
    composite unique index (`parameter_key`, COALESCE(``parameter_value``),
    `surface_form`, `language`). Returns the new rows actually inserted
    — duplicates are silently skipped.
    """
    if not payload.entries:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "no_entries"},
        )

    values = [
        {
            "parameter_key": e.parameter_key,
            "parameter_value": e.parameter_value,
            "surface_form": e.surface_form,
            "language": e.language,
            "polarity": e.polarity,
        }
        for e in payload.entries
    ]

    stmt = (
        pg_insert(SynonymEntry)
        .values(values)
        .on_conflict_do_nothing(
            index_elements=None,  # rely on the explicit unique index
        )
        .returning(SynonymEntry)
    )
    inserted_rows = list((await db.execute(stmt)).scalars().all())
    await db.commit()
    logger.info(
        "admin.synonym.bulk_created inserted=%d skipped=%d by_admin=%s",
        len(inserted_rows),
        len(payload.entries) - len(inserted_rows),
        admin.id,
    )
    return SynonymBulkResponse(
        inserted=len(inserted_rows),
        skipped=len(payload.entries) - len(inserted_rows),
        items=[SynonymEntryResponse.model_validate(r) for r in inserted_rows],
    )


@router.delete(
    "/{entry_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_synonym(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        delete(SynonymEntry).where(SynonymEntry.id == entry_id)
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "synonym_not_found"},
        )
    await db.commit()
    logger.info(
        "admin.synonym.deleted entry=%s by_admin=%s", entry_id, admin.id
    )
