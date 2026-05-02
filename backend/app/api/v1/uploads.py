"""Uploads API endpoints - Local file storage."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.db.models import User

router = APIRouter()

# Allowed file types
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Upload directory
UPLOAD_DIR = Path(settings.upload_dir if hasattr(settings, "upload_dir") else "uploads")


def ensure_upload_dir():
    """Ensure upload directory exists."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class UploadResponse(BaseModel):
    """Response after successful file upload."""

    original_url: str
    thumbnail_url: str
    medium_url: str
    large_url: str
    key: str


class MultiUploadResponse(BaseModel):
    """Response for multiple file uploads."""

    images: list[UploadResponse]
    failed: int


@router.post("/image", response_model=UploadResponse)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a single image file to local storage.

    Returns URLs for the uploaded image.
    """
    ensure_upload_dir()

    # Validate file type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise BadRequestException(
            f"Invalid file type '{file.content_type}'. Allowed: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )

    # Check file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise BadRequestException(
            f"Invalid file extension '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content to check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise BadRequestException(
            f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
        )

    # Generate unique filename
    unique_id = uuid4()
    filename = f"{unique_id}{ext}"
    user_dir = UPLOAD_DIR / "listings" / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = user_dir / filename
    with open(file_path, "wb") as f:
        f.write(content)

    # Build URLs - use the request's base URL
    base_url = str(request.base_url).rstrip("/")
    key = f"listings/{current_user.id}/{filename}"

    # For now, all URLs point to the same file (no image processing)
    # In the future, you could add image processing to create thumbnails
    image_url = f"{base_url}/uploads/{key}"

    return UploadResponse(
        original_url=image_url,
        thumbnail_url=image_url,  # Same as original for now
        medium_url=image_url,  # Same as original for now
        large_url=image_url,  # Same as original for now
        key=key,
    )


@router.post("/images", response_model=MultiUploadResponse)
async def upload_multiple_images(
    request: Request,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Upload multiple image files to local storage.

    Returns URLs for all successfully uploaded images.
    """
    ensure_upload_dir()

    if len(files) > 10:
        raise BadRequestException("Maximum 10 images allowed per upload")

    uploaded_images: list[UploadResponse] = []
    failed_count = 0

    base_url = str(request.base_url).rstrip("/")
    user_dir = UPLOAD_DIR / "listings" / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        try:
            # Validate file type
            if file.content_type not in ALLOWED_CONTENT_TYPES:
                failed_count += 1
                continue

            # Check file extension
            ext = Path(file.filename or "").suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                failed_count += 1
                continue

            # Read file content
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                failed_count += 1
                continue

            # Generate unique filename
            unique_id = uuid4()
            filename = f"{unique_id}{ext}"

            # Save file
            file_path = user_dir / filename
            with open(file_path, "wb") as f:
                f.write(content)

            # Build URLs
            key = f"listings/{current_user.id}/{filename}"
            image_url = f"{base_url}/uploads/{key}"

            uploaded_images.append(
                UploadResponse(
                    original_url=image_url,
                    thumbnail_url=image_url,
                    medium_url=image_url,
                    large_url=image_url,
                    key=key,
                )
            )
        except Exception:
            failed_count += 1
            continue

    return MultiUploadResponse(
        images=uploaded_images,
        failed=failed_count,
    )


@router.delete("/{key:path}")
async def delete_image(
    key: str,
    current_user: User = Depends(get_current_user),
):
    """
    Delete an uploaded image.

    Only the owner can delete their images.
    """
    # Validate key belongs to user
    expected_prefix = f"listings/{current_user.id}/"
    if not key.startswith(expected_prefix):
        raise BadRequestException("You can only delete your own images")

    file_path = UPLOAD_DIR / key
    if file_path.exists():
        file_path.unlink()
        return {"message": "Image deleted"}

    raise BadRequestException("Image not found")
