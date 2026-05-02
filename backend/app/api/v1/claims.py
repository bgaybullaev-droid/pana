"""Claims API endpoints."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_seller
from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.security import generate_otp
from app.db.database import get_db
from app.db.models import (
    ClaimStatus,
    Listing,
    ListingClaim,
    Seller,
    SourceType,
    VerificationMethod,
)
from app.db.redis import CacheKeys, get_redis
from app.schemas.listing import ListingClaimRequest, ListingClaimVerifyRequest
from app.utils.phone import normalize_phone

router = APIRouter()

# Constants
MAX_CLAIMS_PER_DAY = 5
MAX_OTP_ATTEMPTS = 3
OTP_EXPIRY_MINUTES = 10


@router.post("", response_model=dict, status_code=201)
async def initiate_claim(
    data: ListingClaimRequest,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate a claim on a parsed listing.

    If seller's phone matches listing phone, claim is auto-approved.
    Otherwise, OTP verification is required.
    """
    # Check daily claim limit
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    claims_today_query = select(func.count()).where(
        ListingClaim.seller_id == seller.id,
        ListingClaim.created_at >= today_start,
    )
    claims_today_result = await db.execute(claims_today_query)
    claims_today = claims_today_result.scalar() or 0

    if claims_today >= MAX_CLAIMS_PER_DAY:
        raise BadRequestException(
            f"Maximum {MAX_CLAIMS_PER_DAY} claims per day exceeded"
        )

    # Get listing
    listing_query = select(Listing).where(
        Listing.id == data.listing_id,
        Listing.deleted_at.is_(None),
    )
    listing_result = await db.execute(listing_query)
    listing = listing_result.scalar_one_or_none()

    if not listing:
        raise NotFoundException("Listing", str(data.listing_id))

    # Check if listing is already claimed
    if listing.source_type != SourceType.PARSED:
        raise BadRequestException("Only parsed listings can be claimed")

    if listing.seller_id is not None:
        raise BadRequestException("Listing is already claimed")

    # Check for existing pending claim
    existing_claim_query = select(ListingClaim).where(
        ListingClaim.listing_id == data.listing_id,
        ListingClaim.status == ClaimStatus.PENDING,
    )
    existing_claim_result = await db.execute(existing_claim_query)
    existing_claim = existing_claim_result.scalar_one_or_none()

    if existing_claim and existing_claim.seller_id != seller.id:
        raise BadRequestException("Listing has a pending claim by another seller")

    # Normalize phones for comparison
    seller_phone = normalize_phone(seller.phone)
    listing_phone = normalize_phone(listing.phone or "")

    # Auto-approve if phones match
    if seller_phone and listing_phone and seller_phone == listing_phone:
        # Create approved claim
        claim = ListingClaim(
            listing_id=listing.id,
            seller_id=seller.id,
            status=ClaimStatus.VERIFIED,
            verification_method=VerificationMethod.PHONE_MATCH,
        )
        db.add(claim)

        # Update listing
        listing.seller_id = seller.id
        listing.source_type = SourceType.CLAIMED
        listing.claimed_at = datetime.now(timezone.utc)

        # Update seller stats
        seller.listings_count += 1

        await db.commit()

        return {
            "claim_id": str(claim.id),
            "status": "verified",
            "verification_method": "phone_match",
            "message": "Claim auto-approved - phone numbers match",
        }

    # Otherwise, require OTP verification
    if not listing_phone:
        raise BadRequestException("Listing has no phone number for verification")

    # Create or update pending claim
    if existing_claim:
        claim = existing_claim
        claim.otp_attempts = 0
    else:
        claim = ListingClaim(
            listing_id=listing.id,
            seller_id=seller.id,
            status=ClaimStatus.PENDING,
            otp_phone=listing.phone,
        )
        db.add(claim)

    # Generate and store OTP
    otp_code = generate_otp()
    claim.otp_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=OTP_EXPIRY_MINUTES
    )

    # Store OTP in Redis
    redis = await get_redis()
    await redis.setex(
        CacheKeys.otp(listing.phone),
        OTP_EXPIRY_MINUTES * 60,
        otp_code,
    )

    await db.commit()

    # TODO: Send OTP via SMS
    # For now, return OTP in response (development only)
    return {
        "claim_id": str(claim.id),
        "status": "pending",
        "verification_method": "otp",
        "message": f"OTP sent to {listing.phone[:4]}****{listing.phone[-2:]}",
        "otp_expires_in": OTP_EXPIRY_MINUTES * 60,
        # Development only - remove in production
        "_dev_otp": otp_code if settings.debug else None,
    }


@router.post("/{claim_id}/verify", response_model=dict)
async def verify_claim(
    claim_id: UUID,
    data: ListingClaimVerifyRequest,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify claim with OTP code.
    """
    # Get claim
    claim_query = select(ListingClaim).where(
        ListingClaim.id == claim_id,
        ListingClaim.seller_id == seller.id,
    )
    claim_result = await db.execute(claim_query)
    claim = claim_result.scalar_one_or_none()

    if not claim:
        raise NotFoundException("Claim", str(claim_id))

    if claim.status != ClaimStatus.PENDING:
        raise BadRequestException(f"Claim is already {claim.status.value}")

    # Check OTP attempts
    if claim.otp_attempts >= MAX_OTP_ATTEMPTS:
        claim.status = ClaimStatus.REJECTED
        await db.commit()
        raise BadRequestException("Maximum OTP attempts exceeded. Claim rejected.")

    # Check OTP expiry
    if claim.otp_expires_at and datetime.now(timezone.utc) > claim.otp_expires_at:
        claim.status = ClaimStatus.EXPIRED
        await db.commit()
        raise BadRequestException("OTP has expired. Please initiate a new claim.")

    # Verify OTP
    redis = await get_redis()
    stored_otp = await redis.get(CacheKeys.otp(claim.otp_phone))

    claim.otp_attempts += 1

    if not stored_otp or stored_otp != data.otp_code:
        remaining_attempts = MAX_OTP_ATTEMPTS - claim.otp_attempts
        await db.commit()
        raise BadRequestException(
            f"Invalid OTP code. {remaining_attempts} attempts remaining."
        )

    # OTP verified - approve claim
    claim.status = ClaimStatus.VERIFIED
    claim.verification_method = VerificationMethod.OTP

    # Get and update listing
    listing_query = select(Listing).where(Listing.id == claim.listing_id)
    listing_result = await db.execute(listing_query)
    listing = listing_result.scalar_one_or_none()

    if listing:
        listing.seller_id = seller.id
        listing.source_type = SourceType.CLAIMED
        listing.claimed_at = datetime.now(timezone.utc)
        seller.listings_count += 1

    # Clear OTP from Redis
    await redis.delete(CacheKeys.otp(claim.otp_phone))

    await db.commit()

    return {
        "claim_id": str(claim.id),
        "status": "verified",
        "verification_method": "otp",
        "message": "Claim verified successfully",
    }


@router.get("/{claim_id}", response_model=dict)
async def get_claim_status(
    claim_id: UUID,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
):
    """
    Get claim status.
    """
    claim_query = select(ListingClaim).where(
        ListingClaim.id == claim_id,
        ListingClaim.seller_id == seller.id,
    )
    claim_result = await db.execute(claim_query)
    claim = claim_result.scalar_one_or_none()

    if not claim:
        raise NotFoundException("Claim", str(claim_id))

    return {
        "claim_id": str(claim.id),
        "listing_id": str(claim.listing_id),
        "status": claim.status.value,
        "verification_method": (
            claim.verification_method.value if claim.verification_method else None
        ),
        "otp_attempts": claim.otp_attempts,
        "created_at": claim.created_at.isoformat(),
    }
