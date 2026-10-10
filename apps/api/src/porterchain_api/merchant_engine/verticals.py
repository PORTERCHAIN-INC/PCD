"""Merchant vertical slugs — a subset of website `SOLUTION_VERTICAL_SLUGS` (§8.1.12).

Every merchant type maps to one slug: labs and pharmacies are medical, plumbing and
electrical dealers are construction, traders are wholesale, warehouses are 3pl.
"""

from __future__ import annotations

MERCHANT_VERTICAL_SLUGS: tuple[str, ...] = (
    "wholesale",
    "medical",
    "construction",
    "3pl",
    "food-beverage",
)

VERTICAL_LABELS: dict[str, str] = {
    "wholesale": "Shopify store, e-commerce or trader",
    "medical": "Pharmacy, lab or medical",
    "construction": "Construction, plumbing or electrical supply",
    "3pl": "Warehouse or 3PL",
    "food-beverage": "Food & beverage",
}

VERTICAL_INDUSTRY: dict[str, str] = {
    "wholesale": "ecommerce",
    "medical": "pharmacy-medical",
    "construction": "construction-materials",
    "3pl": "ecommerce",
    "food-beverage": "coffee-roasters",
}


def is_valid_merchant_vertical(slug: str) -> bool:
    return slug in MERCHANT_VERTICAL_SLUGS
