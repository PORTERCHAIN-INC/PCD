"""Database ownership boundaries — PorterChain owns dispatch, GPS, and proof."""

from enum import StrEnum


class DataOwnership(StrEnum):
    PORTERCHAIN = "porterchain"


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
