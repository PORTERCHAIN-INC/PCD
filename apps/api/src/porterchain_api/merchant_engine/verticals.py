"""Merchant vertical slugs (§8.1.12) plus GTA small-vehicle verticals (2026-10 research).

Every merchant type maps to one slug: labs and pharmacies are medical, plumbing, electrical
and HVAC dealers are construction, traders are wholesale, warehouses are 3pl.

The 2026-10 additions are Toronto supply-chain (150 km) businesses that ship by sedan/SUV,
pickup or van and are allowed in Phase 0 (no storage, no alcohol, limited-quantity DG only).
Regulated types (cannabis, tobacco/vape, firearms, controlled drugs, lead-acid batteries,
bulk paint/solvents) are deliberately NOT here; they are open owner questions.
"""

from __future__ import annotations

MERCHANT_VERTICAL_SLUGS: tuple[str, ...] = (
    "wholesale",
    "medical",
    "construction",
    "3pl",
    "food-beverage",
    # 2026-10 GTA small-vehicle verticals
    "automotive",
    "print-signage",
    "florist-garden",
    "office-it",
    "furniture-appliance",
    "industrial-mro",
    "legal-documents",
    "event-rentals",
)

#: Verticals present before the 2026-10 research (the website solution pages cover these).
WEBSITE_SOLUTION_SLUGS: frozenset[str] = frozenset({"wholesale", "medical", "construction", "3pl", "food-beverage"})

VERTICAL_LABELS: dict[str, str] = {
    "wholesale": "Shopify store, e-commerce or trader",
    "medical": "Pharmacy, lab or medical",
    "construction": "Construction, plumbing or electrical supply",
    "3pl": "Warehouse or 3PL",
    "food-beverage": "Food & beverage",
    "automotive": "Auto parts, dealership or repair shop",
    "print-signage": "Print shop, signage or promotional products",
    "florist-garden": "Florist, nursery or garden centre",
    "office-it": "Office supplies, IT or electronics",
    "furniture-appliance": "Furniture, mattress or appliance retailer",
    "industrial-mro": "Industrial, MRO, tools or fasteners",
    "legal-documents": "Law firm, finance or real-estate documents",
    "event-rentals": "Event, AV or party rentals (same-day return)",
}

VERTICAL_INDUSTRY: dict[str, str] = {
    "wholesale": "ecommerce",
    "medical": "pharmacy-medical",
    "construction": "construction-materials",
    "3pl": "ecommerce",
    "food-beverage": "coffee-roasters",
    "automotive": "automotive-parts",
    "print-signage": "printing-signage",
    "florist-garden": "florist-garden",
    "office-it": "office-it",
    "furniture-appliance": "furniture-appliance",
    "industrial-mro": "industrial-mro",
    "legal-documents": "professional-services",
    "event-rentals": "event-rentals",
}

#: Booking defaults per vertical (merchant can change every booking). vehicle_class ids are
#: the pricing catalog's (sedan_suv | pickup | cargo_van | sprinter_van). Phase 0 dolly is $20.
VERTICAL_DEFAULTS: dict[str, dict[str, object]] = {
    "wholesale": {"vehicle_class": "cargo_van", "dolly": False},
    "medical": {"vehicle_class": "sedan_suv", "dolly": False},
    "construction": {"vehicle_class": "pickup", "dolly": False},
    "3pl": {"vehicle_class": "cargo_van", "dolly": True},
    "food-beverage": {"vehicle_class": "cargo_van", "dolly": False},
    "automotive": {"vehicle_class": "pickup", "dolly": False},
    "print-signage": {"vehicle_class": "cargo_van", "dolly": False},
    "florist-garden": {"vehicle_class": "cargo_van", "dolly": False},
    "office-it": {"vehicle_class": "sedan_suv", "dolly": False},
    "furniture-appliance": {"vehicle_class": "sprinter_van", "dolly": True},
    "industrial-mro": {"vehicle_class": "pickup", "dolly": True},
    "legal-documents": {"vehicle_class": "sedan_suv", "dolly": False},
    "event-rentals": {"vehicle_class": "cargo_van", "dolly": True},
}

#: Phase-0 handling notes shown to ops (not enforced here; DG/alcohol rules live in booking checks).
VERTICAL_NOTES: dict[str, str] = {
    "automotive": "No lead-acid batteries, fuel or bulk fluids (DG). Limited-quantity aerosols only.",
    "print-signage": "Large signs may need a cargo van or pickup; declare dimensions.",
    "florist-garden": "Live plants: same-day only; no fertiliser or pesticide DG beyond limited quantity.",
    "office-it": "Declared-value cover locked until G-INS; electronics travel at standard liability.",
    "furniture-appliance": "Two-person / white-glove not offered in Phase 0; dolly $20.",
    "industrial-mro": "No compressed gas cylinders or bulk solvents; limited-quantity DG only.",
    "legal-documents": "Recipient contact is email only (no masked calls/SMS in Phase 0).",
    "event-rentals": "Same-day out and return; no overnight holding or storage.",
}


def is_valid_merchant_vertical(slug: str) -> bool:
    return slug in MERCHANT_VERTICAL_SLUGS


def vertical_option(slug: str) -> dict[str, object]:
    return {
        "slug": slug,
        "label": VERTICAL_LABELS[slug],
        "default_vehicle_class": VERTICAL_DEFAULTS[slug]["vehicle_class"],
        "note": VERTICAL_NOTES.get(slug),
    }
