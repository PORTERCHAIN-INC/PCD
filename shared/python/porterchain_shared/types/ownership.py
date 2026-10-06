"""Database ownership boundaries — PorterChain owns dispatch, GPS, and proof."""

from enum import StrEnum


class DataOwnership(StrEnum):
    PORTERCHAIN = "porterchain"
    # Kept for older imports. Empty FLEETBASE_OWNED below.
    FLEETBASE = "fleetbase"


PORTERCHAIN_OWNED: frozenset[str] = frozenset(
    {
        "users",
        "merchants",
        "visitors",
        "quotes",
        "contracts",
        "pricing",
        "invoices",
        "billing",
        "crm",
        "notifications",
        "analytics",
        "reports",
        "leads",
        "abandoned_checkouts",
        "domain_events",
        "vehicles",
        "drivers",
        "orders",
        "dispatch",
        "routes",
        "gps",
        "waypoints",
        "tracking",
        "proof_of_delivery",
    }
)

# Kept so older imports still load. Dispatch, GPS, and proof are PorterChain.
FLEETBASE_OWNED: frozenset[str] = frozenset()
