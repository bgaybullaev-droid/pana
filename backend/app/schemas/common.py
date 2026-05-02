"""Common schemas used across the application."""

from datetime import datetime, timezone
from typing import Annotated, Dict, Generic, List, TypeVar
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, PlainSerializer

# Naive datetimes in the DB are stored as Asia/Tashkent local (Postgres
# server TZ + SQLAlchemy DateTime without timezone=True). Attach that
# zone before converting to UTC, otherwise the client sees a time off by
# +5h and misgroups "today" as "earlier".
_DB_NAIVE_TZ = ZoneInfo("Asia/Tashkent")


def serialize_datetime_utc(dt: datetime) -> str:
    """Serialize datetime as UTC ISO format with Z suffix."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_DB_NAIVE_TZ)
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# Custom datetime type that always serializes as UTC with Z suffix
UTCDateTime = Annotated[
    datetime, PlainSerializer(serialize_datetime_utc, return_type=str)
]

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: List[T]
    page: int
    per_page: int
    total: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        per_page: int,
    ) -> "PaginatedResponse[T]":
        """Create paginated response."""
        total_pages = (total + per_page - 1) // per_page
        return cls(
            items=items,
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        )


class ErrorDetail(BaseModel):
    """Error detail for field-specific errors."""

    field: str
    error: str


class ErrorBody(BaseModel):
    """Error body structure."""

    code: str
    message: str
    details: List[ErrorDetail] = []


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorBody


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
    success: bool = True


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    environment: str
    services: Dict[str, str] = {}
