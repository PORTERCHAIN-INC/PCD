"""Business types and capability packs (doc 70 §2.1, §2.2, §4).

A new business type that reuses existing capabilities is config only: add a row
here. A new capability or document is a new module with its own code and tests.
"""

from __future__ import annotations

from typing import Any

ROLE_SHIPPER = "shipper"
ROLE_PARTNER = "partner"

PICKUP_MODES = ("scheduled_daily", "on_demand", "recurring_route", "hub_dropoff", "dock_appointment", "multi_location")
TRACKING_MODES = ("ours", "theirs", "both")
LABEL_MODES = ("ours", "theirs", "both")
BARCODE_FORMATS = ("code128", "qr", "gs1_128")
REF_TYPES = ("order", "shipment", "sku", "parcel", "customer", "po", "container")

# Every capability the platform knows. A capability not in this list does not exist.
CAPABILITIES: dict[str, str] = {
    "shopify_app": "Shopify app",
    "carrier_rates": "Shopify carrier rates",
    "parcel": "Parcels",
    "invoicing_interac": "Invoices paid by Interac e-Transfer",
    "webhooks": "Webhooks",
    "multi_location": "Multiple locations",
    "dock_appointment": "Dock appointments",
    "pallet": "Pallets",
    "csv_import": "CSV import",
    "api": "API",
    "their_label_accept": "Accept their labels",
    "storage_partner": "Storage partner",
    "on_demand": "On-demand pickups",
    "same_day": "Same-day",
    "fragile_handling": "Fragile handling",
    "perishable_handling": "Perishable handling",
    "simple_portal": "Simple portal",
    "email_to_order": "Email to order",
    "partner_portal": "Partner portal",
    "job_accept": "Accept jobs",
    "pod_upload": "Proof of delivery upload",
    "rate_card_inbound": "Partner rate card",
    "coi_required": "Certificate of insurance required",
    "edi_lite": "EDI-lite",
    "cvor_required": "CVOR required",
    "linehaul": "Linehaul",
    "recurring_route": "Recurring routes",
    "sla_contract": "SLA contract",
    "port_rail_pickup": "Port / rail pickup",
    "bonded_note": "Bonded note",
    "document_pack": "Customs document pack",
    "web_booking": "Web / app booking",
    "rx_delivery": "Prescription delivery",
    "food_handling": "Food handling",
    "upright": "Keep upright",
    "heat_sensitive": "Heat sensitive (summer advisory)",
    "heavy_bags": "Heavy bag weight bands",
}

BUSINESS_TYPES: dict[str, dict[str, Any]] = {
    "shopify_merchant": {
        "label_en": "Shopify merchant", "label_fr": "Marchand Shopify", "roles": [ROLE_SHIPPER],
        "capabilities": ["shopify_app", "carrier_rates", "parcel", "invoicing_interac", "webhooks"],
        "profile": {"pickup_mode": "scheduled_daily", "pickup_params": {"cutoff": "14:00"}, "label_mode": "ours", "tracking_mode": "both"},
        "price_card": "b2b_standard",
    },
    "warehouse_3pl": {
        "label_en": "Warehouse / 3PL", "label_fr": "Entrepôt / 3PL", "roles": [ROLE_SHIPPER, ROLE_PARTNER],
        "capabilities": ["multi_location", "dock_appointment", "pallet", "csv_import", "api", "their_label_accept", "storage_partner"],
        "profile": {"pickup_mode": "dock_appointment", "pickup_params": {"slot_minutes": 30}, "label_mode": "both", "tracking_mode": "both",
                    "relabel_rule": {"when": "unreadable_or_unsupported"}},
        "price_card": "pallet_route",
    },
    "small_shop": {
        "label_en": "Small shop", "label_fr": "Petit commerce", "roles": [ROLE_SHIPPER],
        "capabilities": ["on_demand", "same_day", "fragile_handling", "perishable_handling", "simple_portal", "email_to_order"],
        "profile": {"pickup_mode": "on_demand", "pickup_params": {}, "label_mode": "ours", "tracking_mode": "ours"},
        "price_card": "small_shop",
        "subtypes": ["pet_food", "flowers", "pharmacy", "bakery_cake", "gift", "candles", "other"],
    },
    "courier_partner": {
        "label_en": "Courier partner", "label_fr": "Partenaire de messagerie", "roles": [ROLE_PARTNER],
        "capabilities": ["partner_portal", "job_accept", "pod_upload", "rate_card_inbound", "coi_required"],
        "profile": {"pickup_mode": "on_demand", "pickup_params": {}, "label_mode": "both", "tracking_mode": "theirs"},
        "price_card": "partner_cost",
    },
    "logistics_partner": {
        "label_en": "Logistics partner", "label_fr": "Partenaire logistique", "roles": [ROLE_PARTNER, ROLE_SHIPPER],
        "capabilities": ["partner_portal", "edi_lite", "cvor_required", "pallet", "linehaul"],
        "profile": {"pickup_mode": "recurring_route", "pickup_params": {}, "label_mode": "theirs", "tracking_mode": "both"},
        "price_card": "partner_cost",
    },
    "supply_chain": {
        "label_en": "Supply chain", "label_fr": "Chaîne d'approvisionnement", "roles": [ROLE_SHIPPER],
        "capabilities": ["api", "recurring_route", "multi_location", "sla_contract", "edi_lite"],
        "profile": {"pickup_mode": "recurring_route", "pickup_params": {}, "label_mode": "both", "tracking_mode": "both"},
        "price_card": "contract",
    },
    "import_export_cha": {
        "label_en": "Import / export (CHA)", "label_fr": "Import / export (courtier en douane)", "roles": [ROLE_SHIPPER, ROLE_PARTNER],
        "capabilities": ["port_rail_pickup", "bonded_note", "document_pack", "edi_lite"],
        "profile": {"pickup_mode": "dock_appointment", "pickup_params": {}, "label_mode": "theirs", "tracking_mode": "theirs"},
        "price_card": "contract",
    },
    "retail_customer": {
        "label_en": "Retail customer", "label_fr": "Client particulier", "roles": [ROLE_SHIPPER],
        "capabilities": ["web_booking"],
        "profile": {"pickup_mode": "on_demand", "pickup_params": {}, "label_mode": "ours", "tracking_mode": "ours"},
        "price_card": "retail",
    },
}

# Subtype rules (doc 70 §2.1) — extra capabilities switched on by the subtype.
SUBTYPE_CAPABILITIES: dict[str, list[str]] = {
    "pharmacy": ["rx_delivery"],
    "bakery_cake": ["food_handling", "upright"],
    "flowers": ["perishable_handling", "upright"],
    "pet_food": ["heavy_bags"],
    "candles": ["heat_sensitive"],
}

# Documents matrix (doc 70 §2.2): A always, C conditional, absent = off.
DOCUMENTS = ("bol", "pallet_manifest", "customs_docs", "pod", "rx_custody_log", "cold_chain_log", "tdg", "packing_slip", "signature_id", "dolly", "pallets", "bulk_api")
_DOC_MATRIX: dict[str, dict[str, str]] = {
    "shopify_merchant": {"bol": "C1", "pod": "A", "cold_chain_log": "C6", "packing_slip": "C8", "signature_id": "C10", "dolly": "C11", "bulk_api": "A"},
    "warehouse_3pl": {"bol": "C1", "pallet_manifest": "C2", "pod": "A", "cold_chain_log": "C6", "tdg": "C7", "packing_slip": "C8", "signature_id": "C10", "dolly": "C11", "pallets": "C3", "bulk_api": "A"},
    "small_shop:bakery_cake": {"pod": "A", "cold_chain_log": "C6"},
    "small_shop:flowers": {"pod": "A"},
    "small_shop:pet_food": {"pod": "A", "packing_slip": "C8", "dolly": "C11"},
    "small_shop:pharmacy": {"pod": "A", "rx_custody_log": "A", "cold_chain_log": "C6", "signature_id": "A"},
    "small_shop": {"pod": "A", "packing_slip": "C8", "signature_id": "C10"},
    "supply_chain": {"bol": "C1", "pallet_manifest": "C2", "customs_docs": "C4", "pod": "A", "cold_chain_log": "C6", "tdg": "C7", "packing_slip": "C8", "signature_id": "C10", "dolly": "C11", "pallets": "C3", "bulk_api": "A"},
    "import_export_cha": {"bol": "C1", "pallet_manifest": "C2", "customs_docs": "C4", "pod": "A", "tdg": "C7", "packing_slip": "C8", "signature_id": "C10", "dolly": "C11", "pallets": "C3", "bulk_api": "C12"},
    "courier_partner": {"bol": "C1", "pod": "A", "rx_custody_log": "C5", "cold_chain_log": "C6", "signature_id": "C10", "bulk_api": "A"},
    "logistics_partner": {"bol": "C1", "pallet_manifest": "C2", "pod": "A", "tdg": "C7", "pallets": "C3", "bulk_api": "A"},
    "retail_customer": {"pod": "A"},
}


def business_type(code: str) -> dict[str, Any]:
    bt = BUSINESS_TYPES.get(code)
    if bt is None:
        raise ValueError(f"unknown_business_type:{code}")
    return bt


def default_capabilities(code: str, subtype: str | None = None) -> list[str]:
    bt = business_type(code)
    if subtype and subtype not in bt.get("subtypes", [subtype]):
        raise ValueError(f"unknown_subtype:{subtype}")
    caps = list(bt["capabilities"]) + SUBTYPE_CAPABILITIES.get(subtype or "", [])
    return list(dict.fromkeys(caps))


def default_profile(code: str) -> dict[str, Any]:
    p = dict(business_type(code)["profile"])
    p.setdefault("barcode_formats", ["code128", "qr"] + (["gs1_128"] if p["pickup_mode"] == "dock_appointment" else []))
    p.setdefault("ref_schema", {"order": "Order #"})
    p.setdefault("relabel_rule", None)
    return p


def documents_for(code: str, subtype: str | None = None) -> dict[str, str]:
    """Which documents this org sees: {doc: 'A'|'Cn'}. Off documents are absent."""
    business_type(code)
    key = f"{code}:{subtype}" if subtype else code
    return dict(_DOC_MATRIX.get(key) or _DOC_MATRIX.get(code) or {})


def validate_profile(p: dict[str, Any]) -> None:
    if p.get("pickup_mode") not in PICKUP_MODES:
        raise ValueError("invalid_pickup_mode")
    if p.get("tracking_mode") not in TRACKING_MODES:
        raise ValueError("invalid_tracking_mode")
    if p.get("label_mode") not in LABEL_MODES:
        raise ValueError("invalid_label_mode")
    bad = [b for b in p.get("barcode_formats") or [] if b not in BARCODE_FORMATS]
    if bad:
        raise ValueError(f"invalid_barcode_format:{bad[0]}")
    bad_refs = [r for r in (p.get("ref_schema") or {}) if r not in REF_TYPES]
    if bad_refs:
        raise ValueError(f"invalid_ref_type:{bad_refs[0]}")
