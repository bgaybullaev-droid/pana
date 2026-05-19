"""Payment-provider protocol (C3).

Per decision-pass / WALLET_LIFECYCLE.md §6: signature verification is
provider-specific (Click MD5 + secret, Payme HMAC). The Protocol
accepts the raw signature; per-adapter implementation owns the
algorithm.

Money values are integers in smallest currency unit (per
MONEY_STORAGE_DECISION). For UZS that's whole UZS; for USD it's cents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, runtime_checkable
from uuid import UUID


@dataclass
class InvoiceResponse:
    """Returned from create_invoice — typed shape so callers don't
    couple to provider-specific dicts.
    """

    provider: str  # 'click' | 'payme'
    external_invoice_id: str
    payment_url: Optional[str]  # redirect URL for the user, if applicable
    raw: Dict[str, Any]  # provider-specific extras for forensic logging


@dataclass
class CallbackResult:
    """Returned from verify_callback — the parsed, signature-verified
    payload. Signature failure raises CallbackVerificationError.
    """

    external_payment_id: str
    amount: int  # smallest currency unit
    currency: str  # 'UZS' | 'USD'
    status: str  # provider-mapped status; service layer reconciles
    raw: Dict[str, Any]


class CallbackVerificationError(Exception):
    """Raised by verify_callback if the signature is invalid."""


@runtime_checkable
class PaymentProvider(Protocol):
    """Adapter Protocol for payment providers."""

    name: str  # 'click' | 'payme'

    async def create_invoice(
        self,
        *,
        user_id: UUID,
        amount: int,
        currency: str,
        return_url: Optional[str] = None,
    ) -> InvoiceResponse:
        """Create a payment invoice for the user. Phase-2 implementation."""
        ...

    async def verify_callback(
        self, payload: Dict[str, Any], signature: str
    ) -> CallbackResult:
        """Verify and parse a webhook payload. Phase-2 implementation.

        Raises CallbackVerificationError if the signature is invalid.
        """
        ...
