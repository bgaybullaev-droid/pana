"""Real Estate API - Main Application."""

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as api_v1_router
from app.api.v1 import seo
from app.core.config import settings
from app.core.exceptions import RealEstateException
from app.db.redis import close_redis
from app.schemas.common import HealthResponse


def datetime_encoder(obj: Any) -> Any:
    """Custom JSON encoder that serializes datetimes as UTC ISO format with Z suffix."""
    if isinstance(obj, datetime):
        # If naive datetime, assume it's UTC
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        # Convert to UTC and format with Z suffix
        utc_dt = obj.astimezone(timezone.utc)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class UTCJSONResponse(JSONResponse):
    """Custom JSON response that serializes datetimes as UTC with Z suffix."""

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=datetime_encoder,
        ).encode("utf-8")


# Upload directory — resolve relative to the backend package root so
# the path works regardless of the process cwd (local dev, Docker,
# systemd, etc.). Absolute paths in settings are honoured as-is.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_upload_cfg = settings.upload_dir if hasattr(settings, "upload_dir") else "uploads"
UPLOAD_DIR = (
    Path(_upload_cfg)
    if Path(_upload_cfg).is_absolute()
    else _BACKEND_ROOT / _upload_cfg
)

# Initialize Sentry
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=0.1 if settings.app_env == "production" else 1.0,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown
    await close_redis()


# Create FastAPI application
app = FastAPI(
    title="Real Estate API",
    description="PropTech Aggregator API for Uzbekistan's Real Estate Market",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
    default_response_class=UTCJSONResponse,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RealEstateException)
async def realestate_exception_handler(request: Request, exc: RealEstateException):
    """Handle custom Real Estate exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    import traceback

    error_detail = traceback.format_exc()
    print(f"ERROR: {error_detail}")  # Log to console

    if settings.debug:
        # In debug mode, return full error details
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(exc),
                    "details": error_detail.split("\n"),
                }
            },
        )

    # Log to Sentry in production
    sentry_sdk.capture_exception(exc)

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": [],
            }
        },
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns application health status and version.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.app_env,
        services={
            "api": "healthy",
        },
    )


# Include API routes
#
# ORDER MATTERS — DO NOT REORDER WITHOUT BLOCK F R3 REVIEW.
#
# 1. ``api_v1_router`` is registered first under ``/api/v1`` so it
#    always matches before anything else. Critical: the F3 SEO router
#    is mounted at the **root**, and although its routes use literal
#    prefixes like ``/{lang}/listing/...`` that wouldn't collide
#    syntactically with ``/api/v1/...``, registering the API router
#    first is a defence-in-depth measure against any future
#    catch-all SEO route accidentally shadowing the API.
# 2. ``/uploads`` static mount — narrow, prefix-scoped, can't collide.
# 3. ``seo_router`` (Block F V2.0 F3b) — root-level SSR routes for
#    ``/robots.txt``, ``/sitemap*``, and ``/{lang}/...`` content pages.
#    Includes the TWA-UA bounce + dedicated read-only DB pool so a
#    crawler burst can't starve the API pool.
app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

# Mount static files for uploads
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Block F V2.0 F3b — SSR routes for SEO traffic. Registered last so
# more-specific API + static-file paths always match first.
app.include_router(seo.router)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Real Estate API",
        "version": "1.0.0",
        "description": "PropTech Aggregator for Uzbekistan",
        "docs_url": "/docs" if settings.debug else None,
        "health_url": "/health",
    }
