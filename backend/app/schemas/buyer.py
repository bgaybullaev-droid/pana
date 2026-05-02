"""Buyer-specific schemas for TikTok-style UI."""

from typing import List, Optional

from pydantic import BaseModel


class BuyerListingImage(BaseModel):
    """Image schema for buyer listings."""

    imageUrl: str


class BuyerListing(BaseModel):
    """Listing schema optimized for TikTok-style buyer UI."""

    id: str
    name: str
    price: int
    description: str
    images: List[BuyerListingImage]
    sellerUserName: str
    sellerImage: str
    likes: int
    isLiked: bool


class BuyerListingsResponse(BaseModel):
    """Paginated response for buyer listings."""

    listings: List[BuyerListing]
    listingsCount: int
    currentPageNumber: int
    nextPageNumber: Optional[int] = None


class LikeToggleResponse(BaseModel):
    """Response for like toggle endpoint."""

    liked: bool
