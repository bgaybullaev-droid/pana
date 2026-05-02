"""Pydantic schemas for request/response models."""

from app.schemas.auth import RefreshTokenRequest, TelegramAuthRequest, TokenResponse
from app.schemas.comment import (
    CommentAuthorResponse,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    CommentWithReplies,
)
from app.schemas.common import (
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
)
from app.schemas.listing import (
    ListingCreate,
    ListingFilters,
    ListingListResponse,
    ListingResponse,
    ListingUpdate,
    SellerListingListResponse,
)
from app.schemas.notification import (
    NotificationActorResponse,
    NotificationMarkReadRequest,
    NotificationResponse,
)
from app.schemas.seller import (
    SellerCreate,
    SellerPublicResponse,
    SellerResponse,
    SellerUpdate,
)
from app.schemas.user import UserCreate, UserInDB, UserResponse, UserUpdate

__all__ = [
    # Auth
    "TelegramAuthRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserInDB",
    # Seller
    "SellerCreate",
    "SellerUpdate",
    "SellerResponse",
    "SellerPublicResponse",
    # Listing
    "ListingCreate",
    "ListingUpdate",
    "ListingResponse",
    "ListingListResponse",
    "SellerListingListResponse",
    "ListingFilters",
    # Common
    "PaginationParams",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    # Comment
    "CommentCreate",
    "CommentUpdate",
    "CommentResponse",
    "CommentAuthorResponse",
    "CommentWithReplies",
    # Notification
    "NotificationResponse",
    "NotificationActorResponse",
    "NotificationMarkReadRequest",
]
