"""Payme payment-provider stub (C3 — Phase 2 will implement).

Public Payme API uses HMAC for webhook signature verification.
Activation conditions mirror Click: settings populated, webhook
URL registered, production traffic warrants it.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from .base import (
    CallbackResult,
    CallbackVerificationError,
    InvoiceResponse,
    PaymentProvider,
)


class PaymeProvider:
    """PaymentProvider implementation for Payme.uz — Phase 2 stub."""

    name = "payme"

    async def create_invoice(
        self,
        *,
        user_id: UUID,
        amount: int,
        currency: str,
        return_url: Optional[str] = None,
    ) -> InvoiceResponse:
        raise NotImplementedError(
            "Payme integration: deferred to Phase 2. "
            "See decision-pass/WALLET_LIFECYCLE.md §5."
        )

    async def verify_callback(
        self, payload: Dict[str, Any], signature: str
    ) -> CallbackResult:
        raise NotImplementedError(
            "Payme webhook verification: deferred to Phase 2."
        )
