"""Export all ORM models so SQLAlchemy metadata and Alembic autogenerate discover them."""

from app.models.base import Base
from app.models.billing import Invoice, Subscription, SubscriptionPlan
from app.models.engagement import (
    AuditLog,
    Conversation,
    HumanAssignment,
    Message,
    Notification,
    SupportTicket,
)
from app.models.identity import (
    Agency,
    AgencyMember,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
)
from app.models.integration import (
    AgencyIntegration,
    AgentConfiguration,
    ApiUsage,
    IntegrationCredential,
)
from app.models.transaction import Cancellation, Payment, Refund, Ticket
from app.models.travel import (
    Booking,
    BookingPassenger,
    Customer,
    FlightOffer,
    Passenger,
    SupplierTransaction,
)

__all__ = [
    "Agency",
    "AgencyIntegration",
    "AgencyMember",
    "AgentConfiguration",
    "ApiUsage",
    "AuditLog",
    "Base",
    "Booking",
    "BookingPassenger",
    "Cancellation",
    "Conversation",
    "Customer",
    "FlightOffer",
    "HumanAssignment",
    "IntegrationCredential",
    "Invoice",
    "Message",
    "Notification",
    "Passenger",
    "Payment",
    "Permission",
    "RefreshToken",
    "Refund",
    "Role",
    "RolePermission",
    "Subscription",
    "SubscriptionPlan",
    "SupplierTransaction",
    "SupportTicket",
    "Ticket",
    "User",
]
