"""View / contact / share event helpers and the self-view guard.

Single home for the rules that decide whether a listing-side counter or
event row should be written. Every increment site must call
:func:`is_self_view` before mutating state — see
``spec-kit/partial/EXECUTION_PLAN.md`` §0.1.
"""

from __future__ import annotations

from typing import Optional

from app.db.models import Listing, User


def is_self_view(user: Optional[User], listing: Listing) -> bool:
    """True iff the listing belongs to the user.

    A listing's own seller should never inflate its view, contact, or
    share counters by previewing their own ad. Crawled listings without a
    claimed seller (``seller_id IS NULL``) have no owner to compare, so
    the call returns ``False`` even for an authenticated user — those
    views legitimately count.
    """
    if user is None or listing.seller_id is None:
        return False
    seller = getattr(listing, "seller", None)
    if seller is None:
        # Eager-load was skipped; be defensive — without the seller row
        # we can't prove self-view, so default to "not self".
        return False
    return seller.user_id == user.id
