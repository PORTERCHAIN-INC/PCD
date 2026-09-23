"""CSV/JSON row → stop dicts for route import."""

from __future__ import annotations

import re
from typing import Any

from porterchain_api.merchant_engine.address_normalize import compose_raw_from_parts, normalize_address
from porterchain_api.merchant_engine.stop_cargo import clean_packages, legacy_cargo, write_legacy_cargo

_KG_PER_LB = 0.45359237
_CM_PER_IN = 2.54
_CM_PER_FT = 30.48


def optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def to_kg(weight: float, unit: str) -> float:
    if unit == "lbs":
        return round(weight * _KG_PER_LB, 3)
    return round(weight, 3)


def to_cm(value: float, unit: str) -> float:
    if unit == "in":
        return round(value * _CM_PER_IN, 3)
    if unit == "ft":
        return round(value * _CM_PER_FT, 3)
    return round(value, 3)


def packages_from_row(row: dict[str, Any], sequence: int) -> list[dict[str, Any]]:
    sku = optional_text(row.get("sku"))
    weight = optional_float(row.get("weight"))
    length = optional_float(row.get("length"))
    width = optional_float(row.get("width"))
    height = optional_float(row.get("height"))
    if weight is None and length is None and width is None and height is None and not sku:
        return []

    dim_unit = (str(row.get("dimensions_unit") or "cm").strip().lower())
    if dim_unit in ("inch", "inches"):
        dim_unit = "in"
    if dim_unit not in ("in", "ft", "cm"):
        dim_unit = "cm"
    weight_unit = str(row.get("weight_unit") or "kg").strip().lower()
    if weight_unit in ("lb", "pound", "pounds"):
        weight_unit = "lbs"
    if weight_unit not in ("lbs", "kg"):
        weight_unit = "kg"

    qty = 1
    try:
        qty = max(1, int(float(row.get("quantity") or 1)))
    except (TypeError, ValueError):
        qty = 1
    qty = min(qty, 100)

    spec = (
        f"{length or 0}x{width or 0}x{height or 0} {dim_unit}, "
        f"{weight or 0} {weight_unit}"
    )
    packages: list[dict[str, Any]] = []
    for copy in range(qty):
        packages.append(
            {
                "id": f"csv-{sequence}-{sku or 'parcel'}-{copy + 1}",
                "name": sku or "Parcel",
                "sku": sku,
                "quantity": 1,
                "weight_kg": to_kg(weight or 0, weight_unit),
                "length_cm": to_cm(length or 0, dim_unit),
                "width_cm": to_cm(width or 0, dim_unit),
                "height_cm": to_cm(height or 0, dim_unit),
                "dimensions": spec,
            }
        )
    return packages


def collapse_parcel_rows(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rows that share a sequence are one stop with many parcels."""
    grouped: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for stop in stops:
        key = str(stop.get("sequence"))
        packages = list(stop.get("packages") or [])
        if key not in grouped:
            grouped[key] = stop
            order.append(key)
            continue
        existing = grouped[key]
        if not existing.get("address") and stop.get("address"):
            existing["address"] = stop.get("address")
        existing["packages"] = list(existing.get("packages") or []) + packages
    return [grouped[key] for key in order if grouped[key].get("address")]


_REGION_WORDS = frozenset({"on", "ont", "ontario", "canada", "ca"})


def _same_address_key(raw: str) -> str:
    """Same place typed two ways ("91 Breton Ave, Mississauga" / "91 breton avenue
    mississauga") gives the same key."""
    query = normalize_address(raw).geocode_query.lower()
    words = re.sub(r"[^\w\s]", " ", query).split()
    seen: list[str] = []
    for word in words:
        if word not in _REGION_WORDS and word not in seen:
            seen.append(word)
    return " ".join(seen)


def _is_pair_sheet(mapped_rows: list[dict[str, Any]]) -> bool:
    return any(optional_text(r.get("pickup_address")) or optional_text(r.get("dropoff_address")) for r in mapped_rows)


def _merchant_sequence(row: dict[str, Any]) -> int | None:
    try:
        return int(float(row["sequence"])) if row.get("sequence") not in (None, "") else None
    except (TypeError, ValueError):
        return None


def pair_rows_to_stops(mapped_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row = pickup cell + dropoff cell. Every row shares one pickup; drops merge by
    sequence (when given) or by the same dropoff address."""
    pickup: dict[str, Any] | None = None
    pickup_key: str | None = None
    drops: dict[str, dict[str, Any]] = {}
    first_seen: dict[str, tuple[int, int]] = {}

    for i, row in enumerate(mapped_rows):
        pickup_raw = optional_text(row.get("pickup_address"))
        if pickup_raw:
            key = _same_address_key(pickup_raw)
            if pickup is None:
                pickup = {
                    "sequence": 1,
                    "row": i + 2,
                    "stop_type": "pickup",
                    "address": pickup_raw,
                    "packages": [],
                }
                pickup_key = key
            elif key != pickup_key:
                raise ValueError("route_import_multiple_pickups")

        drop_raw = optional_text(row.get("dropoff_address"))
        if not drop_raw:
            continue
        seq = _merchant_sequence(row)
        drop_key = f"seq:{seq}" if seq is not None else f"addr:{_same_address_key(drop_raw)}"
        packages = packages_from_row(row, i + 2)
        if drop_key in drops:
            drops[drop_key]["packages"].extend(packages)
            continue
        first_seen[drop_key] = (seq if seq is not None else i, i)
        drops[drop_key] = {
            "row": i + 2,
            "stop_type": "drop",
            "address": drop_raw,
            "unit": row.get("unit"),
            "city": row.get("city"),
            "province": row.get("province"),
            "postal": row.get("postal"),
            "contact_name": row.get("contact_name"),
            "contact_phone": row.get("contact_phone"),
            "external_ref": row.get("external_ref"),
            "notes": row.get("notes"),
            "lat": None,
            "lng": None,
            "packages": packages,
        }

    if pickup is None:
        return list(drops.values())
    ordered = sorted(drops, key=lambda k: first_seen[k])
    stops = [pickup]
    for n, key in enumerate(ordered, start=2):
        drops[key]["sequence"] = n
        stops.append(drops[key])
    return stops


def rows_to_stops(mapped_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if _is_pair_sheet(mapped_rows):
        return pair_rows_to_stops(mapped_rows)
    stops: list[dict[str, Any]] = []
    for i, row in enumerate(mapped_rows):
        address = compose_raw_from_parts(row)
        stop_type = str(row.get("stop_type") or "").strip().lower()
        if stop_type in ("pickup", "pick", "pu", "origin"):
            st = "pickup"
        elif stop_type in ("drop", "dropoff", "delivery", "do", "dest"):
            st = "drop"
        else:
            st = "pickup" if i == 0 else "drop"
        seq = row.get("sequence")
        try:
            sequence = int(seq) if seq not in (None, "") else i + 1
        except (TypeError, ValueError):
            sequence = i + 1
        lat = lng = None
        try:
            if row.get("lat") not in (None, ""):
                lat = float(row["lat"])
            if row.get("lng") not in (None, ""):
                lng = float(row["lng"])
        except (TypeError, ValueError):
            lat = lng = None
        packages = packages_from_row(row, sequence)
        if not address and not packages:
            continue
        stops.append(
            {
                "sequence": sequence,
                "row": i + 2,
                "stop_type": st,
                "address": address,
                "unit": row.get("unit"),
                "city": row.get("city"),
                "province": row.get("province"),
                "postal": row.get("postal"),
                "contact_name": row.get("contact_name"),
                "contact_phone": row.get("contact_phone"),
                "external_ref": row.get("external_ref"),
                "notes": row.get("notes"),
                "lat": lat,
                "lng": lng,
                "packages": packages,
            }
        )
    stops.sort(key=lambda s: int(s.get("sequence") or 0))
    stops = collapse_parcel_rows(stops)
    pickups = [s for s in stops if s["stop_type"] == "pickup"]
    if not pickups and stops:
        stops[0]["stop_type"] = "pickup"
    elif len(pickups) > 1:
        first = True
        for s in stops:
            if s["stop_type"] == "pickup":
                if first:
                    first = False
                else:
                    s["stop_type"] = "drop"
    return stops


def legacy_cargo_from_stops(stops: list[dict[str, Any]]) -> tuple[float | None, str | None]:
    return legacy_cargo(stops)


def write_legacy_cargo_cfg(cfg: dict[str, Any], stops: list[dict[str, Any]]) -> None:
    write_legacy_cargo(cfg, stops)


def packages_clean(raw: Any) -> list[dict[str, Any]]:
    return clean_packages(raw)
