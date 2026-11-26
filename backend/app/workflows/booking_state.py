"""Deterministic state-machine transitions for the flight booking lifecycle."""

from app.models.enums import BookingStatus

ALLOWED_BOOKING_TRANSITIONS: dict[BookingStatus, set[BookingStatus]] = {
    BookingStatus.REQUESTED: {
        BookingStatus.FLIGHT_SEARCHED,
        BookingStatus.SEARCH_FAILED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.FLIGHT_SEARCHED: {
        BookingStatus.OFFER_SELECTED,
        BookingStatus.OFFER_EXPIRED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.OFFER_SELECTED: {
        BookingStatus.PRICE_REVALIDATED,
        BookingStatus.OFFER_EXPIRED,
        BookingStatus.PRICE_CHANGED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.PRICE_REVALIDATED: {
        BookingStatus.PASSENGER_DETAILS_COLLECTED,
        BookingStatus.OFFER_EXPIRED,
        BookingStatus.PRICE_CHANGED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.PASSENGER_DETAILS_COLLECTED: {
        BookingStatus.BOOKING_APPROVED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.BOOKING_APPROVED: {
        BookingStatus.RESERVATION_CREATED,
        BookingStatus.RESERVATION_FAILED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.RESERVATION_CREATED: {
        BookingStatus.PAYMENT_PENDING,
        BookingStatus.CANCELLED,
    },
    BookingStatus.PAYMENT_PENDING: {
        BookingStatus.PAYMENT_CONFIRMED,
        BookingStatus.PAYMENT_FAILED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.PAYMENT_CONFIRMED: {
        BookingStatus.TICKETING_PENDING,
        BookingStatus.REFUND_PENDING,
    },
    BookingStatus.TICKETING_PENDING: {
        BookingStatus.TICKETED,
        BookingStatus.TICKETING_FAILED,
    },
    BookingStatus.TICKETING_FAILED: {
        BookingStatus.TICKETING_PENDING,
        BookingStatus.REFUND_PENDING,
    },
    BookingStatus.TICKETED: {
        BookingStatus.COMPLETED,
        BookingStatus.CANCELLED,
        BookingStatus.REFUND_PENDING,
    },
    BookingStatus.REFUND_PENDING: {
        BookingStatus.CANCELLED,
    },
    BookingStatus.PRICE_CHANGED: {
        BookingStatus.PRICE_REVALIDATED,
        BookingStatus.CANCELLED,
    },
    BookingStatus.PAYMENT_FAILED: {
        BookingStatus.PAYMENT_PENDING,
        BookingStatus.CANCELLED,
    },
    BookingStatus.RESERVATION_FAILED: {
        BookingStatus.CANCELLED,
    },
    BookingStatus.SEARCH_FAILED: set(),
    BookingStatus.OFFER_EXPIRED: set(),
    BookingStatus.COMPLETED: set(),
    BookingStatus.CANCELLED: set(),
}


class InvalidBookingTransitionError(ValueError):
    """Raised when an invalid booking lifecycle transition is attempted."""


def assert_valid_transition(current: BookingStatus, target: BookingStatus) -> BookingStatus:
    """Validate and return the next BookingStatus, raising on illegal transitions."""
    if current == target:
        return target
    allowed = ALLOWED_BOOKING_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidBookingTransitionError(
            f"Illegal booking transition: {current.value} -> {target.value}"
        )
    return target
