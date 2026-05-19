"""Phase-2 — seller CRM (clients pipeline) CRUD.

Lightweight prospect tracker scoped to the authenticated seller. Each
``seller_client`` carries a name / phone / notes + a 6-stage pipeline
(``new`` / ``contacted`` / ``viewing`` / ``negotiating`` / ``won`` /
``lost``); listings can be pinned to a client via the
``/seller/clients/{id}/attach/{listing_id}`` endpoints to support
"send these three options to Aziz" flows.

All endpoints check ownership: the operated-on ``seller_client`` and
any attached listing must both belong to the current seller. Cross-
seller reads / writes are 404'd to avoid leaking existence.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_seller
from app.db.database import get_db
from app.db.models import Listing, Seller, SellerClient, SellerClientListing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seller/clients", tags=["Seller Clients (CRM)"])


PIPELINE_STAGES = {
    "new",
    "contacted",
    "viewing",
    "negotiating",
    "won",
    "lost",
}


class SellerClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seller_id: UUID
    name: str
    phone: Optional[str]
    notes: Optional[str]
    pipeline_stage: str
    created_at: datetime
    updated_at: datetime


class AttachedListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    listing_id: UUID
    added_at: datetime


class SellerClientDetailResponse(SellerClientResponse):
    listings: list[AttachedListingResponse]


class SellerClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=30)
    notes: Optional[str] = None
    pipeline_stage: str = Field(default="new", max_length=32)


class SellerClientUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=30)
    notes: Optional[str] = None
    pipeline_stage: Optional[str] = Field(default=None, max_length=32)


def _validate_stage(stage: str) -> None:
    if stage not in PIPELINE_STAGES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "invalid_pipeline_stage",
                "allowed": sorted(PIPELINE_STAGES),
            },
        )


async def _load_client_for_seller(
    db: AsyncSession, *, client_id: UUID, seller_id: UUID
) -> SellerClient:
    row = (
        await db.execute(
            select(SellerClient).where(
                SellerClient.id == client_id,
                SellerClient.seller_id == seller_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "client_not_found"},
        )
    return row


@router.get("", response_model=list[SellerClientResponse])
async def list_clients(
    pipeline_stage: Optional[str] = Query(default=None, max_length=32),
    page: int = Query(default=1, ge=1, le=10_000),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
) -> list[SellerClientResponse]:
    stmt = (
        select(SellerClient)
        .where(SellerClient.seller_id == seller.id)
        .order_by(SellerClient.updated_at.desc())
    )
    if pipeline_stage:
        _validate_stage(pipeline_stage)
        stmt = stmt.where(SellerClient.pipeline_stage == pipeline_stage)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = list((await db.execute(stmt)).scalars().all())
    return [SellerClientResponse.model_validate(r) for r in rows]


@router.post(
    "", response_model=SellerClientResponse, status_code=status.HTTP_201_CREATED
)
async def create_client(
    payload: SellerClientCreate,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
) -> SellerClientResponse:
    _validate_stage(payload.pipeline_stage)
    row = SellerClient(
        seller_id=seller.id,
        name=payload.name,
        phone=payload.phone,
        notes=payload.notes,
        pipeline_stage=payload.pipeline_stage,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info(
        "seller.client.created id=%s seller=%s stage=%s",
        row.id,
        seller.id,
        row.pipeline_stage,
    )
    return SellerClientResponse.model_validate(row)


@router.get("/{client_id}", response_model=SellerClientDetailResponse)
async def get_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
) -> SellerClientDetailResponse:
    row = await _load_client_for_seller(
        db, client_id=client_id, seller_id=seller.id
    )
    attached = list(
        (
            await db.execute(
                select(SellerClientListing)
                .where(SellerClientListing.client_id == client_id)
                .order_by(SellerClientListing.added_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return SellerClientDetailResponse(
        id=row.id,
        seller_id=row.seller_id,
        name=row.name,
        phone=row.phone,
        notes=row.notes,
        pipeline_stage=row.pipeline_stage,
        created_at=row.created_at,
        updated_at=row.updated_at,
        listings=[
            AttachedListingResponse(
                listing_id=link.listing_id, added_at=link.added_at
            )
            for link in attached
        ],
    )


@router.patch("/{client_id}", response_model=SellerClientResponse)
async def update_client(
    client_id: UUID,
    payload: SellerClientUpdate,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
) -> SellerClientResponse:
    row = await _load_client_for_seller(
        db, client_id=client_id, seller_id=seller.id
    )
    if payload.name is not None:
        row.name = payload.name
    if payload.phone is not None:
        row.phone = payload.phone
    if payload.notes is not None:
        row.notes = payload.notes
    if payload.pipeline_stage is not None:
        _validate_stage(payload.pipeline_stage)
        row.pipeline_stage = payload.pipeline_stage
    await db.commit()
    await db.refresh(row)
    return SellerClientResponse.model_validate(row)


@router.delete(
    "/{client_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    row = await _load_client_for_seller(
        db, client_id=client_id, seller_id=seller.id
    )
    await db.delete(row)
    await db.commit()
    logger.info("seller.client.deleted id=%s seller=%s", client_id, seller.id)


@router.post(
    "/{client_id}/attach/{listing_id}",
    response_model=AttachedListingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def attach_listing(
    client_id: UUID,
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
) -> AttachedListingResponse:
    """Link a listing to a CRM client. Listing must belong to the seller."""
    await _load_client_for_seller(
        db, client_id=client_id, seller_id=seller.id
    )
    listing = (
        await db.execute(
            select(Listing.id).where(
                Listing.id == listing_id, Listing.seller_id == seller.id
            )
        )
    ).first()
    if listing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "listing_not_found_or_not_yours"},
        )

    existing = (
        await db.execute(
            select(SellerClientListing).where(
                SellerClientListing.client_id == client_id,
                SellerClientListing.listing_id == listing_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return AttachedListingResponse(
            listing_id=existing.listing_id, added_at=existing.added_at
        )

    link = SellerClientListing(client_id=client_id, listing_id=listing_id)
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return AttachedListingResponse(
        listing_id=link.listing_id, added_at=link.added_at
    )


@router.delete(
    "/{client_id}/attach/{listing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def detach_listing(
    client_id: UUID,
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
    seller: Seller = Depends(get_current_seller),
):
    await _load_client_for_seller(
        db, client_id=client_id, seller_id=seller.id
    )
    result = await db.execute(
        delete(SellerClientListing).where(
            SellerClientListing.client_id == client_id,
            SellerClientListing.listing_id == listing_id,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "attachment_not_found"},
        )
    await db.commit()
