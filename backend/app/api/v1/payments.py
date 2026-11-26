"""Payment initiation, verification, and signed gateway webhook endpoints."""

import json
import uuid

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, require_active_agency_or_api_key
from app.core.database import get_db_session
from app.schemas.transactions import PaymentInitiateRequest, PaymentRead
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.post(
    "/initiate",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate an idempotent customer payment session",
)
async def initiate_payment(
    payload: PaymentInitiateRequest,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:write")),
    session: AsyncSession = Depends(get_db_session),
) -> PaymentRead:
    assert ctx.agency is not None
    return await TransactionService(session, ctx.agency).initiate_payment(payload, actor=ctx.user)


@router.post(
    "/{payment_id}/verify",
    response_model=PaymentRead,
    summary="Verify payment completion with the payment gateway adapter",
)
async def verify_payment(
    payment_id: uuid.UUID,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:write")),
    session: AsyncSession = Depends(get_db_session),
) -> PaymentRead:
    assert ctx.agency is not None
    return await TransactionService(session, ctx.agency).verify_payment(payment_id, actor=ctx.user)


@router.post(
    "/webhooks/{gateway}",
    response_model=PaymentRead,
    summary="Process HMAC-signed payment gateway webhook callback",
)
async def payment_webhook(
    gateway: str,
    request: Request,
    x_webhook_signature: str | None = Header(default=None, alias="X-Webhook-Signature"),
    session: AsyncSession = Depends(get_db_session),
) -> PaymentRead:
    raw_body = await request.body()
    payload_dict = json.loads(raw_body.decode("utf-8"))
    return await TransactionService(session, None).process_signed_webhook(
        gateway=gateway,
        raw_body=raw_body,
        signature=x_webhook_signature,
        payload_dict=payload_dict,
    )
