"""Abstract PaymentGatewayAdapter and normalized transaction DTOs."""

import hashlib
import hmac
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class PaymentInitRequest(BaseModel):
    booking_id: str
    booking_reference: str
    amount: Decimal
    currency: str = "USD"
    customer_name: str
    customer_email: str
    customer_phone: str | None = None
    idempotency_key: str
    return_url: str | None = None


class PaymentSessionResult(BaseModel):
    gateway: str
    gateway_transaction_id: str
    checkout_url: str | None = None
    status: str = "PENDING"
    is_sandbox: bool = True
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PaymentVerifyResult(BaseModel):
    gateway: str
    gateway_transaction_id: str
    verified: bool
    amount: Decimal
    currency: str
    status: str
    is_sandbox: bool = True
    raw_response: dict[str, Any] = Field(default_factory=dict)


class GatewayRefundResult(BaseModel):
    gateway: str
    gateway_refund_id: str
    status: str
    amount: Decimal
    currency: str
    is_sandbox: bool = True
    raw_response: dict[str, Any] = Field(default_factory=dict)


class PaymentGatewayAdapter(ABC):
    """Unified payment interface for SSLCommerz, bKash, Nagad, Stripe, and Sandbox."""

    gateway_name: str
    is_sandbox: bool = True

    @abstractmethod
    async def initiate_payment(self, request: PaymentInitRequest) -> PaymentSessionResult:
        """Create a hosted/tokenized payment session (never touches raw card/CVV)."""

    @abstractmethod
    async def verify_payment(
        self,
        *,
        gateway_transaction_id: str,
        expected_amount: Decimal,
        currency: str,
    ) -> PaymentVerifyResult:
        """Verify payment completion directly with the gateway server."""

    @abstractmethod
    async def refund_payment(
        self,
        *,
        gateway_transaction_id: str,
        amount: Decimal,
        currency: str,
        reason: str | None = None,
    ) -> GatewayRefundResult:
        """Issue a full or partial refund via the gateway."""

    @staticmethod
    def verify_hmac_signature(*, payload: bytes, signature: str, secret: str) -> bool:
        """Constant-time HMAC-SHA256 webhook signature verification."""
        if not signature or not secret:
            return False
        expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        provided = signature.replace("sha256=", "").strip()
        return hmac.compare_digest(expected, provided)
