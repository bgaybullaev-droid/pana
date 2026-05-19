"""Click payment-provider stub (C3 — Phase 2 will implement).

Public Click API uses MD5 + shared secret for webhook signature
verification. The concrete implementation lands in Phase 2 when:
- ``settings.click_merchant_id`` and ``settings.click_secret`` are
  populated via secret manager.
- The webhook URL is registered with Click.
- Production traffic justifies the integration.

For now, every method raises NotImplementedError. The Protocol contract
is committed; the implementation slot is reserved.
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


class ClickProvider:
    """PaymentProvider implementation for Click.uz — Phase 2 stub."""

    name = "click"

    async def create_invoice(
        self,
        *,
        user_id: UUID,
        amount: int,
        currency: str,
        return_url: Optional[str] = None,
    ) -> InvoiceResponse:
        raise NotImplementedError(
            "Click integration: deferred to Phase 2. "
            "See decision-pass/WALLET_LIFECYCLE.md §5."
        )

    async def verify_callback(
        self, payload: Dict[str, Any], signature: str
    ) -> CallbackResult:
        raise NotImplementedError(
            "Click webhook verification: deferred to Phase 2."
        )
