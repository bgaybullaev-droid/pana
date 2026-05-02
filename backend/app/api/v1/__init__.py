"""API v1 module."""

from fastapi import APIRouter

from app.api.v1 import (
    activity_log,
    admin,
    auth,
    buyer,
    claims,
    comments,
    crawler_import,
    favorites,
    housing_complexes,
    listings,
    notification_settings,
    notifications,
    preferences,
    saved_searches,
    sellers,
    uploads,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(listings.router, prefix="/listings", tags=["Listings"])
router.include_router(favorites.router, prefix="/favorites", tags=["Favorites"])
router.include_router(comments.router, tags=["Comments"])
router.include_router(sellers.router, prefix="/sellers", tags=["Sellers"])
router.include_router(claims.router, prefix="/claims", tags=["Claims"])
router.include_router(
    notifications.router, prefix="/notifications", tags=["Notifications"]
)
router.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
router.include_router(admin.router, prefix="/admin", tags=["Admin"])
router.include_router(buyer.router, prefix="/buyer", tags=["Buyer"])
router.include_router(crawler_import.router, prefix="/crawler", tags=["Crawler Import"])
router.include_router(preferences.router, prefix="/me", tags=["User Preferences"])
router.include_router(
    notification_settings.router,
    prefix="/notification-settings",
    tags=["Notification Settings"],
)
router.include_router(
    saved_searches.router,
    prefix="/saved-searches",
    tags=["Saved Searches"],
)
router.include_router(
    housing_complexes.router,
    prefix="/housing-complexes",
    tags=["Housing Complexes"],
)
router.include_router(
    activity_log.router,
    prefix="/activity-log",
    tags=["Activity Log"],
)
