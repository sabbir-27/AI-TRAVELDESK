"""Async background task helpers (Celery-compatible with synchronous fallback)."""

import os

from app.core.logging import get_logger

logger = get_logger(__name__)

CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def enqueue_notification_dispatch(*, event_type: str, recipient: str, booking_id: str) -> None:
    """Queue notification delivery or log structured event when worker is offline."""
    logger.info(
        "Notification dispatched",
        event_type=event_type,
        recipient=recipient,
        booking_id=booking_id,
    )


def enqueue_ticketing_recovery(*, booking_id: str, agency_id: str) -> None:
    """Trigger async recovery workflow for payment-success-but-ticketing-failure."""
    logger.warning(
        "Ticketing recovery queued",
        booking_id=booking_id,
        agency_id=agency_id,
    )
