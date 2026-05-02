"""Comment schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import UTCDateTime


class CommentAuthorResponse(BaseModel):
    """Comment author response schema."""

    id: UUID
    first_name: str
    last_name: Optional[str]
    username: Optional[str]
    avatar_url: Optional[str]

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    """Schema for creating a comment."""

    text: str = Field(..., min_length=1, max_length=2000)
    parent_id: Optional[UUID] = None


class CommentUpdate(BaseModel):
    """Schema for updating a comment."""

    text: str = Field(..., min_length=1, max_length=2000)


class CommentResponse(BaseModel):
    """Comment response schema."""

    id: UUID
    listing_id: UUID
    user_id: UUID
    text: str
    created_at: UTCDateTime
    updated_at: UTCDateTime
    author: CommentAuthorResponse
    replies_count: int = 0
    likes_count: int = 0
    is_liked: bool = False

    model_config = {"from_attributes": True}


class CommentWithReplies(CommentResponse):
    """Comment response with replies."""

    replies: list["CommentResponse"] = []
