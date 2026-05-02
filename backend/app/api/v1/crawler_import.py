"""Crawler import and read endpoints — public, no authentication required."""

import math
import os
import shutil
import uuid as uuid_mod
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import OLXListing, TelegramListing
from app.schemas.crawler import (
    CrawlerImportResult,
    OLXBulkImport,
    OLXListingResponse,
    TelegramBulkImport,
    TelegramListingResponse,
)
from app.services.crawler_service import import_olx_bulk, import_telegram_bulk

router = APIRouter()

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads"))
BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL", "http://localhost:8001")


# =============================================================================
# Telegram Crawler Endpoints
# =============================================================================


@router.post(
    "/telegram/import",
    response_model=CrawlerImportResult,
    status_code=201,
    summary="Import Telegram listings",
)
async def import_telegram_listings(
    body: TelegramBulkImport,
    db: AsyncSession = Depends(get_db),
):
    """Bulk import listings from the Telegram crawler."""
    return await import_telegram_bulk(body.listings, db)


@router.get(
    "/telegram/listings",
    summary="List Telegram listings",
)
async def list_telegram_listings(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    property_type: Optional[str] = Query(None),
    listing_type: Optional[str] = Query(None),
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None),
    rooms: Optional[int] = Query(None, ge=0),
    district: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|price|area_sqm)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    """List Telegram crawler listings with pagination and filters."""
    query = select(TelegramListing)
    count_query = select(func.count()).select_from(TelegramListing)

    # Apply filters
    if property_type:
        query = query.where(TelegramListing.property_type == property_type)
        count_query = count_query.where(TelegramListing.property_type == property_type)
    if listing_type:
        query = query.where(TelegramListing.listing_type == listing_type)
        count_query = count_query.where(TelegramListing.listing_type == listing_type)
    if price_min is not None:
        query = query.where(TelegramListing.price >= price_min)
        count_query = count_query.where(TelegramListing.price >= price_min)
    if price_max is not None:
        query = query.where(TelegramListing.price <= price_max)
        count_query = count_query.where(TelegramListing.price <= price_max)
    if rooms is not None:
        query = query.where(TelegramListing.rooms == rooms)
        count_query = count_query.where(TelegramListing.rooms == rooms)
    if district:
        query = query.where(TelegramListing.district == district)
        count_query = count_query.where(TelegramListing.district == district)

    # Sort
    sort_column = getattr(TelegramListing, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Count total
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [TelegramListingResponse.model_validate(item) for item in items],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": math.ceil(total / per_page) if total > 0 else 0,
    }


@router.get(
    "/telegram/listings/{listing_id}",
    response_model=TelegramListingResponse,
    summary="Get Telegram listing by ID",
)
async def get_telegram_listing(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single Telegram crawler listing by ID."""
    result = await db.execute(
        select(TelegramListing).where(TelegramListing.id == listing_id)
    )
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Telegram listing not found")
    return listing


# =============================================================================
# OLX Crawler Endpoints
# =============================================================================


@router.post(
    "/olx/import",
    response_model=CrawlerImportResult,
    status_code=201,
    summary="Import OLX listings",
)
async def import_olx_listings(
    body: OLXBulkImport,
    db: AsyncSession = Depends(get_db),
):
    """Bulk import listings from the OLX crawler."""
    return await import_olx_bulk(body.listings, db)


@router.get(
    "/olx/listings",
    summary="List OLX listings",
)
async def list_olx_listings(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    property_type: Optional[str] = Query(None),
    listing_type: Optional[str] = Query(None),
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None),
    rooms: Optional[int] = Query(None, ge=0),
    district: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|price|area_sqm)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    """List OLX crawler listings with pagination and filters."""
    query = select(OLXListing)
    count_query = select(func.count()).select_from(OLXListing)

    # Apply filters
    if property_type:
        query = query.where(OLXListing.property_type == property_type)
        count_query = count_query.where(OLXListing.property_type == property_type)
    if listing_type:
        query = query.where(OLXListing.listing_type == listing_type)
        count_query = count_query.where(OLXListing.listing_type == listing_type)
    if price_min is not None:
        query = query.where(OLXListing.price >= price_min)
        count_query = count_query.where(OLXListing.price >= price_min)
    if price_max is not None:
        query = query.where(OLXListing.price <= price_max)
        count_query = count_query.where(OLXListing.price <= price_max)
    if rooms is not None:
        query = query.where(OLXListing.rooms == rooms)
        count_query = count_query.where(OLXListing.rooms == rooms)
    if district:
        query = query.where(OLXListing.district == district)
        count_query = count_query.where(OLXListing.district == district)

    # Sort
    sort_column = getattr(OLXListing, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Count total
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": [OLXListingResponse.model_validate(item) for item in items],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": math.ceil(total / per_page) if total > 0 else 0,
    }


@router.get(
    "/olx/listings/{listing_id}",
    response_model=OLXListingResponse,
    summary="Get OLX listing by ID",
)
async def get_olx_listing(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single OLX crawler listing by ID."""
    result = await db.execute(select(OLXListing).where(OLXListing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="OLX listing not found")
    return listing


# =============================================================================
# Image Upload Endpoint
# =============================================================================


@router.post(
    "/images/upload",
    summary="Upload crawler images",
    status_code=201,
)
async def upload_crawler_images(
    source: str = Form(..., pattern="^(telegram|olx)$"),
    listing_ref: str = Form(""),
    files: List[UploadFile] = File(...),
):
    """Upload image files for crawler listings.

    Returns a list of public URLs where the images are served.

    - **source**: ``telegram`` or ``olx``
    - **listing_ref**: optional sub-directory (e.g. OLX listing ID)
    - **files**: one or more image files
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Build target directory
    target_dir = UPLOAD_DIR / "crawler" / source
    if listing_ref:
        target_dir = target_dir / listing_ref
    target_dir.mkdir(parents=True, exist_ok=True)

    urls: list[str] = []
    for upload_file in files:
        # Generate a unique filename to avoid collisions
        ext = Path(upload_file.filename or "image.jpg").suffix or ".jpg"
        unique_name = f"{uuid_mod.uuid4().hex[:12]}{ext}"
        dest = target_dir / unique_name

        with open(dest, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)

        # Build public URL
        rel = dest.relative_to(UPLOAD_DIR)
        url = f"{BACKEND_BASE_URL}/uploads/{rel}"
        urls.append(url)

    return {"urls": urls}
