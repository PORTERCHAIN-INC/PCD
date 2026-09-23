"""Customer parcel presets, fit checks, and the distance-only price card.

Merchant FSA and rate-card rows never enter this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LB_TO_KG = 0.45359237
IN_TO_CM = 2.54

SEDAN_PRESETS = ("small", "medium", "large", "other")
ALL_PRESETS = ("small", "medium", "large", "extra_large", "skid", "furniture", "other")

DEFAULT_PRESETS: list[dict[str, Any]] = [
    {"id": "small", "label": "Small", "length_in": 10, "width_in": 10, "height_in": 8, "weight_lb": 10, "manual": False},
    {"id": "medium", "label": "Medium", "length_in": 16, "width_in": 12, "height_in": 12, "weight_lb": 25, "manual": False},
    {"id": "large", "label": "Large", "length_in": 24, "width_in": 18, "height_in": 18, "weight_lb": 40, "manual": False},
    {"id": "extra_large", "label": "Extra large", "length_in": 36, "width_in": 24, "height_in": 24, "weight_lb": 70, "manual": False},
    {"id": "skid", "label": "Skid", "length_in": 48, "width_in": 40, "height_in": 48, "weight_lb": 100, "manual": False},
    {"id": "furniture", "label": "Furniture", "length_in": 80, "width_in": 36, "height_in": 30, "weight_lb": 80, "manual": False},
    {"id": "other", "label": "Other", "length_in": None, "width_in": None, "height_in": None, "weight_lb": None, "manual": True},
]

# Fleet and old forms. A generic box truck becomes 16 ft until a person changes it.
VEHICLE_ALIASES = {
    "sedan": "sedan_suv",
    "suv": "sedan_suv",
    "sedansuv": "sedan_suv",
    "sedan_suv": "sedan_suv",
    "cargovan": "cargo_van",
    "cargo_van": "cargo_van",
    "pickup": "pickup",
    "pickuptruck": "pickup",
    "highroof": "sprinter_van",
    "high_roof": "sprinter_van",
    "sprinter": "sprinter_van",
    "sprintervan": "sprinter_van",
    "sprinter_van": "sprinter_van",
    "box16": "box_16",
    "box_16": "box_16",
    "boxtruck": "box_16",
    "box_truck": "box_16",
    "box20": "box_20",
    "box_20": "box_20",
}


def canonical_vehicle_id(raw: str) -> str:
    key = (raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    compact = key.replace("_", "")
    return VEHICLE_ALIASES.get(key) or VEHICLE_ALIASES.get(compact) or key


def default_vehicle_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": "sedan_suv",
            "label": "Sedan / SUV",
            "capacity_kg": 80,
            "max_length_cm": 120,
            "max_width_cm": 90,
            "max_height_cm": 80,
            "booking_enabled": True,
            "retail_enabled": True,
            "merchant_enabled": True,
            "whole_vehicle_enabled": True,
            "allowed_presets": list(SEDAN_PRESETS),
            "sort_order": 1,
        },
        {
            "id": "pickup",
            "label": "Pickup",
            "capacity_kg": 500,
            "max_length_cm": 180,
            "max_width_cm": 150,
            "max_height_cm": 60,
            "booking_enabled": True,
            "retail_enabled": True,
            "merchant_enabled": True,
            "whole_vehicle_enabled": True,
            "allowed_presets": list(ALL_PRESETS),
            "sort_order": 2,
        },
        {
            "id": "cargo_van",
            "label": "Cargo van",
            "capacity_kg": 900,
            "max_length_cm": 300,
            "max_width_cm": 170,
            "max_height_cm": 160,
            "booking_enabled": True,
            "retail_enabled": True,
            "merchant_enabled": True,
            "whole_vehicle_enabled": True,
            "allowed_presets": list(ALL_PRESETS),
            "sort_order": 3,
        },
        {
            "id": "sprinter_van",
            "label": "Sprinter / high-roof",
            "capacity_kg": 1200,
            "max_length_cm": 330,
            "max_width_cm": 170,
            "max_height_cm": 180,
            "booking_enabled": True,
            "retail_enabled": False,
            "merchant_enabled": True,
            "whole_vehicle_enabled": False,
            "allowed_presets": list(ALL_PRESETS),
            "sort_order": 4,
            "description": "Fleet only. Retail booking stays off.",
        },
        {
            "id": "box_16",
            "label": "16 ft box",
            "capacity_kg": 3000,
            "max_length_cm": 480,
            "max_width_cm": 240,
            "max_height_cm": 240,
            "booking_enabled": True,
            "retail_enabled": True,
            "merchant_enabled": True,
            "whole_vehicle_enabled": True,
            "allowed_presets": list(ALL_PRESETS),
            "sort_order": 5,
        },
        {
            "id": "box_20",
            "label": "20 ft box",
            "capacity_kg": 4500,
            "max_length_cm": 600,
            "max_width_cm": 240,
            "max_height_cm": 240,
            "booking_enabled": True,
            "retail_enabled": True,
            "merchant_enabled": True,
            "whole_vehicle_enabled": True,
            "allowed_presets": list(ALL_PRESETS),
            "sort_order": 6,
        },
    ]


def default_customer_pricing() -> dict[str, Any]:
    from porterchain_pricing.gta_rate import default_customer_distance_dict

    card = default_customer_distance_dict()
    card["parcel_presets"] = [dict(row) for row in DEFAULT_PRESETS]
    return card


@dataclass
class ResolvedLoad:
    booking_mode: str
    items: list[dict[str, Any]]
    weight_kg: float | None
    volume_cm3: float | None
    dimensions: str | None
    package_type: str


def presets_from_card(card: dict[str, Any] | None) -> list[dict[str, Any]]:
    raw = card.get("parcel_presets") if isinstance(card, dict) else None
    if not isinstance(raw, list) or not raw:
        return [dict(row) for row in DEFAULT_PRESETS]
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in raw:
        if not isinstance(row, dict):
            continue
        preset_id = str(row.get("id") or "").strip()
        if not preset_id or preset_id in seen:
            continue
        seen.add(preset_id)
        manual = bool(row.get("manual")) or preset_id == "other"
        out.append(
            {
                "id": preset_id,
                "label": str(row.get("label") or preset_id),
                "length_in": row.get("length_in"),
                "width_in": row.get("width_in"),
                "height_in": row.get("height_in"),
                "weight_lb": row.get("weight_lb"),
                "manual": manual,
            }
        )
    if "other" not in seen:
        out.append(dict(DEFAULT_PRESETS[-1]))
    return out


def vehicle_row(catalog: list[Any], vehicle_id: str) -> dict[str, Any] | None:
    want = canonical_vehicle_id(vehicle_id)
    for row in catalog:
        if isinstance(row, dict) and canonical_vehicle_id(str(row.get("id") or "")) == want:
            return row
    return None


def _num(value: Any, field: str) -> float:
    if value is None or value == "":
        raise ValueError(f"{field}_required")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}_invalid") from exc
    if number < 0:
        raise ValueError(f"{field}_invalid")
    return number


def resolve_load(
    *,
    booking_mode: str,
    parcels: list[Any] | None,
    vehicle_id: str,
    catalog: list[Any],
    presets: list[dict[str, Any]],
    fallback_weight_kg: float | None = None,
    fallback_dimensions: str | None = None,
) -> ResolvedLoad:
    mode = "vehicle" if booking_mode == "vehicle" else "parcels"
    row = vehicle_row(catalog, vehicle_id)
    if mode == "vehicle":
        if row is not None and row.get("whole_vehicle_enabled") is False:
            raise ValueError("whole_vehicle_not_available")
        return ResolvedLoad(
            booking_mode="vehicle",
            items=[],
            weight_kg=None,
            volume_cm3=None,
            dimensions=None,
            package_type="whole_vehicle",
        )

    preset_by_id = {str(p["id"]): p for p in presets}
    allowed = None
    if row is not None and isinstance(row.get("allowed_presets"), list) and row["allowed_presets"]:
        allowed = {str(x) for x in row["allowed_presets"]}
    elif canonical_vehicle_id(vehicle_id) == "sedan_suv":
        allowed = set(SEDAN_PRESETS)
    incoming = list(parcels or [])
    if not incoming and fallback_weight_kg is None and not fallback_dimensions:
        raise ValueError("parcels_required")

    items: list[dict[str, Any]] = []
    if incoming:
        for raw in incoming:
            data = raw if isinstance(raw, dict) else raw.model_dump()
            qty = int(data.get("quantity") or 1)
            if qty < 1 or qty > 50:
                raise ValueError("parcel_quantity_invalid")
            preset_id = str(data.get("preset_id") or "other")
            preset = preset_by_id.get(preset_id)
            if preset is None:
                raise ValueError("parcel_preset_unknown")
            if allowed is not None and preset_id not in allowed:
                raise ValueError("parcel_not_allowed")
            manual = bool(preset.get("manual"))
            if manual:
                length_in = _num(data.get("length_in"), "length_in")
                width_in = _num(data.get("width_in"), "width_in")
                height_in = _num(data.get("height_in"), "height_in")
                weight_lb = _num(data.get("weight_lb"), "weight_lb")
            else:
                length_in = _num(preset.get("length_in"), "length_in")
                width_in = _num(preset.get("width_in"), "width_in")
                height_in = _num(preset.get("height_in"), "height_in")
                weight_lb = _num(preset.get("weight_lb"), "weight_lb")
            length_cm = length_in * IN_TO_CM
            width_cm = width_in * IN_TO_CM
            height_cm = height_in * IN_TO_CM
            weight_kg = weight_lb * LB_TO_KG
            _fit_piece(row, length_cm, width_cm, height_cm)
            instructions = str(data.get("instructions") or "").strip() or None
            for _ in range(qty):
                items.append(
                    {
                        "preset_id": preset_id,
                        "preset_label": preset.get("label") or preset_id,
                        "instructions": instructions,
                        "length_cm": round(length_cm, 2),
                        "width_cm": round(width_cm, 2),
                        "height_cm": round(height_cm, 2),
                        "weight_kg": round(weight_kg, 3),
                        "name": preset.get("label") or preset_id,
                    }
                )
    else:
        # Older clients send one weight and one dimension string.
        items.append(
            {
                "preset_id": "other",
                "preset_label": "Parcel",
                "instructions": None,
                "weight_kg": fallback_weight_kg,
                "dimensions": fallback_dimensions,
                "name": "Parcel",
            }
        )

    if row is not None and row.get("capacity_kg") is not None:
        total = sum(float(item.get("weight_kg") or 0) for item in items)
        if total > float(row["capacity_kg"]):
            raise ValueError("load_too_big")

    weight = sum(float(item.get("weight_kg") or 0) for item in items)
    volume = 0.0
    largest = 0.0
    largest_label = None
    for item in items:
        if item.get("length_cm") and item.get("width_cm") and item.get("height_cm"):
            cube = float(item["length_cm"]) * float(item["width_cm"]) * float(item["height_cm"])
            volume += cube
            if cube >= largest:
                largest = cube
                largest_label = (
                    f"{item['length_cm']:.0f}x{item['width_cm']:.0f}x{item['height_cm']:.0f} cm"
                )
    return ResolvedLoad(
        booking_mode="parcels",
        items=items,
        weight_kg=round(weight, 3) if items else fallback_weight_kg,
        volume_cm3=round(volume, 1) if volume else None,
        dimensions=largest_label or fallback_dimensions,
        package_type=str(items[0]["preset_id"]) if len(items) == 1 else "multi_parcel",
    )


def _fit_piece(row: dict[str, Any] | None, length_cm: float, width_cm: float, height_cm: float) -> None:
    if row is None:
        return
    limits = (
        ("max_length_cm", length_cm),
        ("max_width_cm", width_cm),
        ("max_height_cm", height_cm),
    )
    for key, value in limits:
        limit = row.get(key)
        if limit is None or limit == "":
            continue
        if value > float(limit):
            raise ValueError("load_too_big")


def normalize_customer_pricing(raw: dict[str, Any]) -> dict[str, Any]:
    from porterchain_pricing.gta_rate import customer_gta_from_dict

    card = customer_gta_from_dict(raw)
    stored = card.to_dict()
    stored["strict_vehicles"] = True
    for key in (
        "weight_threshold_kg",
        "weight_cents_per_kg",
        "volume_threshold_cm3",
        "cents_per_10k_cm3",
        "declared_value_threshold_cents",
        "declared_value_rate",
    ):
        if raw.get(key) is not None and raw.get(key) != "":
            stored[key] = raw[key]
    for number_key in (
        "base_km_limit",
        "downtown_fee_cad",
        "upper_zone_fee_cad",
        "weight_threshold_kg",
        "volume_threshold_cm3",
        "declared_value_rate",
    ):
        if stored.get(number_key) is not None and float(stored[number_key]) < 0:
            raise ValueError("invalid_config_value")
    for int_key in ("weight_cents_per_kg", "cents_per_10k_cm3", "declared_value_threshold_cents"):
        if stored.get(int_key) is not None and int(stored[int_key]) < 0:
            raise ValueError("invalid_config_value")
    vehicles = stored.get("vehicles") or {}
    for rates in vehicles.values():
        if not isinstance(rates, dict):
            continue
        for amount in rates.values():
            if float(amount) < 0:
                raise ValueError("invalid_config_value")
    stored["parcel_presets"] = presets_from_card(raw)
    for preset in stored["parcel_presets"]:
        if preset.get("manual"):
            continue
        for field in ("length_in", "width_in", "height_in", "weight_lb"):
            if preset.get(field) is None or float(preset[field]) < 0:
                raise ValueError("invalid_config_value")
    return stored


def goods_line(meta: dict[str, Any] | None) -> dict[str, Any]:
    """Short summary for track, dashboard, and history."""
    payload = meta.get("parcels") if isinstance(meta, dict) and isinstance(meta.get("parcels"), dict) else {}
    mode = payload.get("booking_mode") or (meta or {}).get("booking_mode")
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    if mode == "vehicle":
        summary = "Whole vehicle"
        count = 0
    elif items:
        count = len(items)
        summary = f"{count} parcel" if count == 1 else f"{count} parcels"
    else:
        count = 0
        summary = None
    return {
        "vehicle_class": (meta or {}).get("vehicle_class") if isinstance(meta, dict) else None,
        "booking_mode": mode,
        "parcel_count": count,
        "goods_summary": summary,
        "declared_value_cents": payload.get("declared_value_cents"),
        "parcels": items,
    }


def parcels_payload(load: ResolvedLoad, declared_value_cents: int | None) -> dict[str, Any]:
    return {
        "booking_mode": load.booking_mode,
        "items": load.items,
        "declared_value_cents": declared_value_cents,
    }
