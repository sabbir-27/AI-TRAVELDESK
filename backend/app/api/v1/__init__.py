"""Version 1 API router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    agencies,
    agency,
    agent,
    auth,
    bookings,
    flights,
    health,
    payments,
    widget,
    workspace,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(agencies.router, prefix="/agencies", tags=["agencies"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(agency.router, prefix="/agency", tags=["agency"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(flights.router, prefix="/flights", tags=["flights"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(widget.router, prefix="/widget", tags=["widget"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
