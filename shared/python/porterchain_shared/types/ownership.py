"""Database ownership boundaries — Porterchain vs Fleetbase."""

from enum import StrEnum


class DataOwnership(StrEnum):
    PORTERCHAIN = "porterchain"
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
    }
)

FLEETBASE_OWNED: frozenset[str] = frozenset(
    {
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
