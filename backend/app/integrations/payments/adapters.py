"""Payment gateway adapters: Sandbox, SSLCommerz, bKash, Nagad, and Stripe."""

import hashlib
import os
from decimal import Decimal

from app.integrations.payments.base import (
    GatewayRefundResult,
    PaymentGatewayAdapter,
    PaymentInitRequest,
    PaymentSessionResult,
    PaymentVerifyResult,
)


class SandboxPaymentAdapter(PaymentGatewayAdapter):
    """Deterministic sandbox payment adapter clearly marked is_sandbox=True."""

    def __init__(self, gateway_name: str = "sandbox") -> None:
        self.gateway_name = gateway_name
        self.is_sandbox = True

    async def initiate_payment(self, request: PaymentInitRequest) -> PaymentSessionResult:
        digest = hashlib.sha256(
            f"{self.gateway_name}:{request.booking_id}:{request.idempotency_key}".encode()
        ).hexdigest()
        txn_id = f"SBX-{self.gateway_name.upper()}-{digest[:12].upper()}"
        return PaymentSessionResult(
            gateway=self.gateway_name,
            gateway_transaction_id=txn_id,
            checkout_url=f"https://sandbox.aitraveldesk.local/pay/{self.gateway_name}/{txn_id}",
            status="PENDING",
            is_sandbox=True,
            raw_response={"sandbox": True, "txn_id": txn_id, "amount": str(request.amount)},
        )

    async def verify_payment(
        self,
        *,
        gateway_transaction_id: str,
        expected_amount: Decimal,
        currency: str,
    ) -> PaymentVerifyResult:
        return PaymentVerifyResult(
            gateway=self.gateway_name,
            gateway_transaction_id=gateway_transaction_id,
            verified=True,
            amount=expected_amount,
            currency=currency,
            status="CONFIRMED_SANDBOX",
            is_sandbox=True,
            raw_response={
                "sandbox": True,
                "gateway": self.gateway_name,
                "gateway_transaction_id": gateway_transaction_id,
                "verified": True,
            },
        )

    async def refund_payment(
        self,
        *,
        gateway_transaction_id: str,
        amount: Decimal,
        currency: str,
        reason: str | None = None,
    ) -> GatewayRefundResult:
        digest = hashlib.sha256(
            f"refund:{gateway_transaction_id}:{amount}".encode()
        ).hexdigest()
        ref_id = f"SBX-REF-{digest[:10].upper()}"
        return GatewayRefundResult(
            gateway=self.gateway_name,
            gateway_refund_id=ref_id,
            status="REFUNDED_SANDBOX",
            amount=amount,
            currency=currency,
            is_sandbox=True,
            raw_response={"sandbox": True, "refund_id": ref_id, "reason": reason},
        )


def get_payment_gateway_adapter(gateway: str) -> PaymentGatewayAdapter:
    """Resolve gateway adapter for sslcommerz, bkash, nagad, stripe, or sandbox."""
    normalized = gateway.lower().strip()
    if normalized not in {"sslcommerz", "bkash", "nagad", "stripe", "sandbox"}:
        raise ValueError(f"Unsupported payment gateway: {gateway}")
    # Until live merchant keys are configured in Phase 9/prod, use sandbox mode cleanly.
    return SandboxPaymentAdapter(gateway_name=normalized)


def get_webhook_secret(gateway: str) -> str:
    """Resolve gateway webhook signing secret from environment with dev fallback."""
    env_key = f"{gateway.upper().strip()}_WEBHOOK_SECRET"
    return os.getenv(env_key) or "dev-webhook-signing-secret-change-in-production"
