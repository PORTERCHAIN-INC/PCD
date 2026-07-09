"""Merchant vertical slugs — aligned with website `SOLUTION_VERTICAL_SLUGS` (§8.1.12)."""

from __future__ import annotations

MERCHANT_VERTICAL_SLUGS: tuple[str, ...] = (
    "construction",
    "medical",
    "food-beverage",
    "wholesale",
)

VERTICAL_LABELS: dict[str, str] = {
    "construction": "Construction & industrial supply",
    "medical": "Medical & pharmacy",
    "food-beverage": "Food & beverage",
    "wholesale": "Wholesale & e-commerce fulfillment",
}

VERTICAL_INDUSTRY: dict[str, str] = {
    "construction": "construction-materials",
    "medical": "pharmacy-medical",
    "food-beverage": "coffee-roasters",
    "wholesale": "ecommerce",
}


def is_valid_merchant_vertical(slug: str) -> bool:
    return slug in MERCHANT_VERTICAL_SLUGS
