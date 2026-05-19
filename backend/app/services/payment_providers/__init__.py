"""Payment provider adapters (C3 — Phase 1 stubs).

Per decision-pass / WALLET_LIFECYCLE.md §11, §6: the adapter Protocol
is committed today. Concrete implementations (Click, Payme) raise
``NotImplementedError`` until Phase 2 activates them. The framework
calls ``get_provider(name)`` to obtain an adapter; provider-specific
algorithms (Click MD5+secret, Payme HMAC) live inside each adapter,
not in the framework.
"""

from .base import PaymentProvider, InvoiceResponse, CallbackResult
from .click import ClickProvider
from .payme import PaymeProvider


def get_provider(name: str) -> PaymentProvider:
    """Resolve provider by name. Raises ValueError on unknown."""
    if name == "click":
        return ClickProvider()
    if name == "payme":
        return PaymeProvider()
    raise ValueError(f"Unknown payment provider: {name}")


__all__ = [
    "PaymentProvider",
    "InvoiceResponse",
    "CallbackResult",
    "ClickProvider",
    "PaymeProvider",
    "get_provider",
]
