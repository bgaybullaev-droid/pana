"""API v1 module."""

from fastapi import APIRouter

from app.api.v1 import (
    activity_log,
    admin,
    admin_ai,
    admin_export_templates,
    admin_sources,
    admin_suspicions,
    admin_synonyms,
    admin_wallets,
    ai_feedback,
    analytics,
    banners,
    promotions,
    seller_clients,
    seller_exports,
    auth,
    autopost,
    buyer,
    claims,
    comments,
    crawler_import,
    deep_links,
    favorites,
    housing_complexes,
    listings,
    notification_settings,
    notifications,
    preferences,
    referrals,
    saved_searches,
    seller_phones,
    sellers,
    tariffs,
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
router.include_router(
    admin_sources.router, prefix="/admin", tags=["Admin — Sources (A8)"]
)
router.include_router(
    admin_wallets.router, prefix="/admin", tags=["Admin — Wallets (C3)"]
)
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
router.include_router(tariffs.router, prefix="/tariffs", tags=["Tariffs"])
router.include_router(
    seller_phones.router,
    prefix="/sellers/me/phones",
    tags=["Seller Phones (C4)"],
)
router.include_router(
    deep_links.router,
    prefix="/deep-links",
    tags=["Deep Links (D3)"],
)
router.include_router(
    autopost.router,
    prefix="/seller/autopost",
    tags=["Seller Autopost (D4)"],
)
# Block F V2.0 F5b — AI quality management.
router.include_router(ai_feedback.router)  # /ai-feedback (seller-side)
router.include_router(admin_ai.router)  # /admin/ai/*
# Block F V2.0 F2 — synonym dictionary admin CRUD.
router.include_router(admin_synonyms.router)  # /admin/synonyms
# Block F V2.0 F4a — cabinet text exports.
router.include_router(seller_exports.router)
router.include_router(admin_export_templates.router)

# Block phase-2 — promotions + banners (PRS).
router.include_router(promotions.router, prefix="/seller/listings", tags=["Seller Promotions (PRS)"])
router.include_router(banners.public_router, prefix="/banners", tags=["Banners (PRS)"])
router.include_router(banners.admin_router, prefix="/admin", tags=["Admin — Banners (PRS)"])

# Block phase-2 — admin analytics (price-index).
router.include_router(analytics.router)

# Block phase-2 — CRM + suspicions (PRU). Anchors are unique so other
# agents can append after without collision.
router.include_router(seller_clients.router)  # /seller/clients/* (CRM)
router.include_router(admin_suspicions.router)  # /admin/suspicions/*

# Block phase-2 — referral program (PRT).
router.include_router(referrals.router)  # /seller/referrals + /seller/referrals/regenerate
