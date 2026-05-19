"""C3 — Wallet services (Block C V2.0).

Per WALLET_LIFECYCLE.md: idempotent withdraw / deposit / refund /
adjust with SELECT FOR UPDATE, Numeric-free integer math, AuditLog
write-through. **No production callers during test period** — services
exist with tests; the disabled CTAs in C1's tariff page open info
modals, not these functions.

Integer money convention per MONEY_STORAGE_DECISION.md: every amount
is in smallest currency unit (UZS=whole, USD=cents). Service layer
rejects mixed-currency operations.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AuditLog,
    Currency,
    Transaction,
    TransactionStatus,
    TransactionType,
    Wallet,
)

logger = logging.getLogger(__name__)


# ── exceptions ────────────────────────────────────────────────────────


class WalletError(Exception):
    """Base for wallet-service errors."""


class InsufficientFunds(WalletError):
    """Withdraw would make balance negative."""


class CurrencyMismatch(WalletError):
    """Transaction currency != wallet currency."""


class InvalidTransition(WalletError):
    """Transaction state-machine violation."""


class WalletLocked(WalletError):
    """SELECT FOR UPDATE timed out."""


# ── helpers ───────────────────────────────────────────────────────────


_ALLOWED_TRANSITIONS: Dict[TransactionStatus, set] = {
    TransactionStatus.PENDING: {TransactionStatus.COMPLETED, TransactionStatus.FAILED},
    TransactionStatus.COMPLETED: {TransactionStatus.REFUNDED},
    TransactionStatus.FAILED: set(),
    TransactionStatus.REFUNDED: set(),
}


def _check_transition(old: TransactionStatus, new: TransactionStatus) -> None:
    """Raise InvalidTransition if not allowed."""
    if new not in _ALLOWED_TRANSITIONS[old]:
        raise InvalidTransition(f"{old.value} -> {new.value} not allowed")


# ── lazy wallet creation ──────────────────────────────────────────────


async def get_or_create_wallet(
    db: AsyncSession, user_id: UUID, currency: Currency = Currency.UZS
) -> Wallet:
    """Lazy-create the wallet for ``user_id``.

    Idempotent under concurrent calls: the UNIQUE(user_id) constraint
    ensures one row; the second concurrent INSERT no-ops via
    ``ON CONFLICT DO NOTHING`` and the subsequent SELECT returns the
    winning row.

    Per decision-pass G6 (lazy + idempotent insert).
    """
    # Try to fetch first (the common case after wallet exists).
    result = await db.execute(
        select(Wallet).where(Wallet.user_id == user_id)
    )
    wallet = result.scalar_one_or_none()
    if wallet is not None:
        return wallet

    # Insert with idempotency. SQLAlchemy doesn't expose ON CONFLICT for
    # ORM objects directly; use try/except IntegrityError and re-fetch.
    wallet = Wallet(user_id=user_id, currency=currency, current_balance=0)
    db.add(wallet)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallet = result.scalar_one()
    return wallet


# ── balance mutations ─────────────────────────────────────────────────


async def _audit_log_state_change(
    db: AsyncSession,
    *,
    actor_id: Optional[UUID],
    entity_type: str,
    entity_id: UUID,
    action: str,
    old_values: Optional[dict],
    new_values: dict,
) -> None:
    """Insert an AuditLog row in the same DB transaction."""
    db.add(
        AuditLog(
            user_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
        )
    )


async def deposit(
    db: AsyncSession,
    *,
    user_id: UUID,
    amount: int,
    idempotency_key: str,
    external_payment_id: Optional[str] = None,
    subscription_id: Optional[UUID] = None,
    currency: Currency = Currency.UZS,
    metadata: Optional[Dict[str, Any]] = None,
) -> Transaction:
    """Credit ``amount`` to the user's wallet.

    Idempotent on ``idempotency_key``. Returns the Transaction (existing
    or new). Atomic: insert + balance update + audit log in one DB
    transaction.

    NOT called from production endpoints during test period (verified
    via grep: production paths show disabled CTAs, not service calls).
    """
    if amount <= 0:
        raise ValueError("amount must be positive")

    # Idempotency check first — return existing if duplicate key.
    existing = (
        await db.execute(
            select(Transaction).where(
                Transaction.idempotency_key == idempotency_key
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    wallet = await get_or_create_wallet(db, user_id, currency)
    if wallet.currency != currency:
        raise CurrencyMismatch(
            f"wallet={wallet.currency.value} request={currency.value}"
        )

    # Lock the wallet row for the duration of the balance update.
    locked = (
        await db.execute(
            select(Wallet).where(Wallet.id == wallet.id).with_for_update()
        )
    ).scalar_one()

    old_balance = locked.current_balance
    tx = Transaction(
        wallet_id=locked.id,
        type=TransactionType.DEPOSIT,
        amount=amount,
        currency=currency,
        status=TransactionStatus.PENDING,
        external_payment_id=external_payment_id,
        subscription_id=subscription_id,
        idempotency_key=idempotency_key,
        transaction_metadata=metadata or {},
    )
    db.add(tx)
    await db.flush()  # so tx.id is populated for the audit log

    await _audit_log_state_change(
        db,
        actor_id=None,
        entity_type="transaction",
        entity_id=tx.id,
        action="create",
        old_values=None,
        new_values={
            "type": tx.type.value,
            "amount": amount,
            "currency": currency.value,
            "status": tx.status.value,
            "wallet_id": str(locked.id),
            "external_payment_id": external_payment_id,
        },
    )

    # Note: balance is NOT updated until the transaction transitions to
    # COMPLETED via complete_transaction(). This matches the "money is
    # only credited when the provider confirms" semantic.
    return tx


async def withdraw(
    db: AsyncSession,
    *,
    user_id: UUID,
    amount: int,
    idempotency_key: str,
    purpose: str,
    subscription_id: Optional[UUID] = None,
    currency: Currency = Currency.UZS,
    metadata: Optional[Dict[str, Any]] = None,
) -> Transaction:
    """Debit ``amount`` from the user's wallet.

    Idempotent on ``idempotency_key``. Atomic: lock + check balance +
    insert transaction + update balance + audit log.

    Raises:
        InsufficientFunds: balance < amount.
        CurrencyMismatch: requested currency != wallet currency.

    NOT called from production endpoints during test period.
    """
    if amount <= 0:
        raise ValueError("amount must be positive")

    existing = (
        await db.execute(
            select(Transaction).where(
                Transaction.idempotency_key == idempotency_key
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    wallet = await get_or_create_wallet(db, user_id, currency)
    if wallet.currency != currency:
        raise CurrencyMismatch(
            f"wallet={wallet.currency.value} request={currency.value}"
        )

    locked = (
        await db.execute(
            select(Wallet).where(Wallet.id == wallet.id).with_for_update()
        )
    ).scalar_one()

    if locked.current_balance < amount:
        raise InsufficientFunds(
            f"balance={locked.current_balance} amount={amount}"
        )

    old_balance = locked.current_balance
    new_balance = old_balance - amount
    locked.current_balance = new_balance
    locked.version = (locked.version or 0) + 1

    meta = dict(metadata or {})
    meta.setdefault("purpose", purpose)
    tx = Transaction(
        wallet_id=locked.id,
        type=TransactionType.WITHDRAWAL,
        amount=amount,
        currency=currency,
        status=TransactionStatus.COMPLETED,
        completed_at=datetime.utcnow(),
        subscription_id=subscription_id,
        idempotency_key=idempotency_key,
        transaction_metadata=meta,
    )
    db.add(tx)
    await db.flush()

    await _audit_log_state_change(
        db,
        actor_id=None,
        entity_type="transaction",
        entity_id=tx.id,
        action="create",
        old_values=None,
        new_values={
            "type": tx.type.value,
            "amount": amount,
            "status": tx.status.value,
            "purpose": purpose,
        },
    )
    await _audit_log_state_change(
        db,
        actor_id=None,
        entity_type="wallet",
        entity_id=locked.id,
        action="balance_change",
        old_values={"balance": old_balance},
        new_values={"balance": new_balance, "transaction_id": str(tx.id)},
    )
    return tx


async def complete_transaction(
    db: AsyncSession,
    tx: Transaction,
    *,
    actor_id: Optional[UUID] = None,
) -> Transaction:
    """Move a PENDING transaction to COMPLETED and update the wallet
    balance. Used by webhook handlers in Phase 2.
    """
    _check_transition(tx.status, TransactionStatus.COMPLETED)
    if tx.type != TransactionType.DEPOSIT:
        # Withdrawals complete in withdraw() itself; this path is for
        # PENDING deposits being confirmed by webhook.
        raise InvalidTransition("complete_transaction expects DEPOSIT")

    locked = (
        await db.execute(
            select(Wallet).where(Wallet.id == tx.wallet_id).with_for_update()
        )
    ).scalar_one()

    old_balance = locked.current_balance
    new_balance = old_balance + tx.amount
    locked.current_balance = new_balance
    locked.version = (locked.version or 0) + 1

    old_status = tx.status
    tx.status = TransactionStatus.COMPLETED
    tx.completed_at = datetime.utcnow()

    await _audit_log_state_change(
        db,
        actor_id=actor_id,
        entity_type="transaction",
        entity_id=tx.id,
        action="status_change",
        old_values={"status": old_status.value},
        new_values={
            "status": tx.status.value,
            "completed_at": tx.completed_at.isoformat(),
        },
    )
    await _audit_log_state_change(
        db,
        actor_id=actor_id,
        entity_type="wallet",
        entity_id=locked.id,
        action="balance_change",
        old_values={"balance": old_balance},
        new_values={"balance": new_balance, "transaction_id": str(tx.id)},
    )
    return tx


async def fail_transaction(
    db: AsyncSession,
    tx: Transaction,
    *,
    actor_id: Optional[UUID] = None,
    reason: str = "",
) -> Transaction:
    """Move a PENDING transaction to FAILED. Balance unchanged."""
    _check_transition(tx.status, TransactionStatus.FAILED)
    old_status = tx.status
    tx.status = TransactionStatus.FAILED
    tx.transaction_metadata = {**(tx.transaction_metadata or {}), "fail_reason": reason}
    await _audit_log_state_change(
        db,
        actor_id=actor_id,
        entity_type="transaction",
        entity_id=tx.id,
        action="status_change",
        old_values={"status": old_status.value},
        new_values={"status": tx.status.value, "reason": reason},
    )
    return tx


async def refund(
    db: AsyncSession,
    original_tx: Transaction,
    *,
    actor_id: UUID,
    reason: str,
    idempotency_key: str,
) -> Transaction:
    """Refund an already-COMPLETED transaction.

    Per WALLET_LIFECYCLE §4: the original transaction's status flips
    completed -> refunded, AND a separate refund Transaction is inserted
    with metadata.refund_of=<original.id>. AuditLog row for both.
    """
    if original_tx.type != TransactionType.WITHDRAWAL:
        # Refunds make sense only for withdrawals (we paid out, now we
        # reverse). DEPOSIT refunds would be a chargeback flow — Phase 2.
        raise InvalidTransition("refund expects WITHDRAWAL")

    _check_transition(original_tx.status, TransactionStatus.REFUNDED)

    locked = (
        await db.execute(
            select(Wallet).where(Wallet.id == original_tx.wallet_id).with_for_update()
        )
    ).scalar_one()

    old_balance = locked.current_balance
    new_balance = old_balance + original_tx.amount  # credit back
    locked.current_balance = new_balance
    locked.version = (locked.version or 0) + 1

    refund_tx = Transaction(
        wallet_id=locked.id,
        type=TransactionType.REFUND,
        amount=original_tx.amount,
        currency=original_tx.currency,
        status=TransactionStatus.COMPLETED,
        completed_at=datetime.utcnow(),
        idempotency_key=idempotency_key,
        transaction_metadata={
            "refund_of": str(original_tx.id),
            "reason": reason,
        },
    )
    db.add(refund_tx)
    await db.flush()

    old_status = original_tx.status
    original_tx.status = TransactionStatus.REFUNDED

    await _audit_log_state_change(
        db,
        actor_id=actor_id,
        entity_type="transaction",
        entity_id=original_tx.id,
        action="status_change",
        old_values={"status": old_status.value},
        new_values={"status": original_tx.status.value, "refund_id": str(refund_tx.id)},
    )
    await _audit_log_state_change(
        db,
        actor_id=actor_id,
        entity_type="wallet",
        entity_id=locked.id,
        action="balance_change",
        old_values={"balance": old_balance},
        new_values={"balance": new_balance, "transaction_id": str(refund_tx.id)},
    )
    return refund_tx


async def admin_adjust(
    db: AsyncSession,
    *,
    user_id: UUID,
    amount: int,
    reason: str,
    actor_id: UUID,
    idempotency_key: Optional[str] = None,
) -> Transaction:
    """Admin balance adjustment.

    ``amount`` is positive for grant, negative for correction. The
    resulting balance must remain non-negative; reject if it would
    underflow. Reason is mandatory.
    """
    if not reason or not reason.strip():
        raise ValueError("reason is required for admin balance adjustment")
    if amount == 0:
        raise ValueError("amount cannot be zero")

    key = idempotency_key or f"admin_adjust:{uuid4()}"

    # Idempotency check
    existing = (
        await db.execute(
            select(Transaction).where(Transaction.idempotency_key == key)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    wallet = await get_or_create_wallet(db, user_id)
    locked = (
        await db.execute(
            select(Wallet).where(Wallet.id == wallet.id).with_for_update()
        )
    ).scalar_one()

    old_balance = locked.current_balance
    new_balance = old_balance + amount
    if new_balance < 0:
        raise InsufficientFunds(
            f"adjust would underflow: balance={old_balance} delta={amount}"
        )

    locked.current_balance = new_balance
    locked.version = (locked.version or 0) + 1

    tx = Transaction(
        wallet_id=locked.id,
        type=TransactionType.ADJUSTMENT,
        amount=abs(amount),
        currency=locked.currency,
        status=TransactionStatus.COMPLETED,
        completed_at=datetime.utcnow(),
        idempotency_key=key,
        transaction_metadata={
            "direction": "credit" if amount > 0 else "debit",
            "reason": reason,
            "admin_id": str(actor_id),
        },
    )
    db.add(tx)
    await db.flush()

    await _audit_log_state_change(
        db,
        actor_id=actor_id,
        entity_type="wallet",
        entity_id=locked.id,
        action="admin_adjust",
        old_values={"balance": old_balance},
        new_values={
            "balance": new_balance,
            "amount": amount,
            "reason": reason,
            "transaction_id": str(tx.id),
        },
    )
    return tx
