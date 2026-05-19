"""C3 PR3 — admin wallet endpoints.

Single endpoint per decision-pass / WALLET_LIFECYCLE.md §7:
- ``POST /admin/wallets/{user_id}/adjust`` — admin balance grant /
  correction with mandatory reason.

All operations write AuditLog rows in the same DB transaction as the
balance change. Auth is admin-only.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_admin
from app.core.exceptions import BadRequestException, NotFoundException
from app.db.database import get_db
from app.db.models import User, Wallet
from app.services.wallet import (
    InsufficientFunds,
    admin_adjust,
    get_or_create_wallet,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class AdjustBalanceIn(BaseModel):
    """Body for ``POST /admin/wallets/{user_id}/adjust``."""

    type: str = Field(..., pattern="^(grant|correction)$")
    amount: int = Field(..., description="Smallest currency unit; signed integer")
    reason: str = Field(..., min_length=1, max_length=500)
    idempotency_key: Optional[str] = Field(default=None, max_length=64)

    @field_validator("amount")
    @classmethod
    def _amount_nonzero(cls, v: int) -> int:
        if v == 0:
            raise ValueError("amount cannot be zero")
        return v


class WalletResponse(BaseModel):
    """Compact wallet read."""

    id: str
    user_id: str
    current_balance: int
    currency: str
    version: int


class AdjustResponse(BaseModel):
    wallet: WalletResponse
    transaction_id: str
    new_balance: int


@router.get(
    "/wallets/{user_id}",
    response_model=WalletResponse,
    summary="Read wallet for a user (admin only)",
)
async def get_user_wallet(
    user_id: UUID,
    _admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lazy-creates the wallet on first read so admin tooling is
    always able to look up a user's balance even if no transaction
    has happened yet."""
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise NotFoundException("User", str(user_id))

    wallet = await get_or_create_wallet(db, user_id)
    await db.commit()
    return WalletResponse(
        id=str(wallet.id),
        user_id=str(wallet.user_id),
        current_balance=wallet.current_balance,
        currency=wallet.currency.value,
        version=wallet.version or 0,
    )


@router.post(
    "/wallets/{user_id}/adjust",
    response_model=AdjustResponse,
    summary="Admin balance adjustment with mandatory reason",
)
async def adjust_user_balance(
    user_id: UUID,
    body: AdjustBalanceIn,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin grants or corrects a user's wallet balance.

    Per WALLET_LIFECYCLE §7: single endpoint with type discriminator,
    reason mandatory, AuditLog row written. Idempotency-key optional;
    if absent, generated server-side.

    Sign convention:
        type=grant       → amount > 0 increases balance
        type=correction  → amount can be ±; negative reduces balance
    """
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()
    if user is None:
        raise NotFoundException("User", str(user_id))

    # Sign-check for grant type — must be positive credit.
    if body.type == "grant" and body.amount < 0:
        raise BadRequestException("grant requires amount > 0")

    key = body.idempotency_key or f"admin_adjust:{admin.id}:{uuid4()}"

    try:
        tx = await admin_adjust(
            db,
            user_id=user_id,
            amount=body.amount,
            reason=body.reason,
            actor_id=admin.id,
            idempotency_key=key,
        )
    except InsufficientFunds as e:
        await db.rollback()
        raise BadRequestException(
            f"Adjustment would underflow balance: {e}"
        )
    except ValueError as e:
        await db.rollback()
        raise BadRequestException(str(e))

    # Re-read the wallet for the response (the admin_adjust call
    # already updated the locked row in the same transaction).
    wallet = (
        await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
    ).scalar_one()
    await db.commit()

    return AdjustResponse(
        wallet=WalletResponse(
            id=str(wallet.id),
            user_id=str(wallet.user_id),
            current_balance=wallet.current_balance,
            currency=wallet.currency.value,
            version=wallet.version or 0,
        ),
        transaction_id=str(tx.id),
        new_balance=wallet.current_balance,
    )
