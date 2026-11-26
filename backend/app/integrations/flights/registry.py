"""Flight supplier adapter registry selecting configured providers with sandbox fallback."""

import os

from app.integrations.flights.amadeus import AmadeusFlightAdapter
from app.integrations.flights.base import FlightSupplierAdapter
from app.integrations.flights.duffel import DuffelFlightAdapter
from app.integrations.flights.sandbox import SandboxFlightAdapter


def get_flight_supplier_adapter(supplier: str | None = None) -> FlightSupplierAdapter:
    """Resolve a FlightSupplierAdapter by name, falling back to SandboxFlightAdapter."""
    target = (supplier or "").lower().strip()

    if target == "amadeus" or (
        not target and os.getenv("AMADEUS_CLIENT_ID") and os.getenv("AMADEUS_CLIENT_SECRET")
    ):
        client_id = os.getenv("AMADEUS_CLIENT_ID", "")
        client_secret = os.getenv("AMADEUS_CLIENT_SECRET", "")
        if client_id and client_secret:
            return AmadeusFlightAdapter(client_id=client_id, client_secret=client_secret)

    if target == "duffel" or (not target and os.getenv("DUFFEL_ACCESS_TOKEN")):
        token = os.getenv("DUFFEL_ACCESS_TOKEN", "")
        if token:
            return DuffelFlightAdapter(access_token=token)

    return SandboxFlightAdapter()
