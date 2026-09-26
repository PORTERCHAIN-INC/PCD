"""Address and payload mappers — Porterchain models → Fleetbase API payloads."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID


def _mysql_uuid_or_none(value: Any) -> str | None:
    """Fleetbase MySQL FKs need the row uuid, not a public_id like vehicle_abc."""
    if not value or not isinstance(value, str):
        return None
    try:
        return str(UUID(value))
    except ValueError:
        return None


def place_from_address(addr: dict[str, Any]) -> dict[str, Any]:
    """Map Porterchain address JSON to Fleetbase place payload."""
    loc = addr.get("location") if isinstance(addr.get("location"), dict) else {}
    lat = addr.get("lat") or loc.get("lat")
    lng = addr.get("lng") or loc.get("lon") or loc.get("lng")

    place: dict[str, Any] = {
        "name": (
            addr.get("name")
            or addr.get("formatted")
            or addr.get("formatted_address")
            or addr.get("address")
            or "Stop"
        ),
        "street1": (
            addr.get("street")
            or addr.get("address_line1")
            or addr.get("line1")
            or addr.get("formatted")
            or addr.get("formatted_address")
            or ""
        ),
        "city": addr.get("city") or "",
        "province": addr.get("province") or addr.get("state") or "",
        "postal_code": addr.get("postal_code") or addr.get("zip") or "",
        "country": addr.get("country") or "CA",
    }
    if lat is not None and lng is not None:
        place["location"] = {"type": "Point", "coordinates": [float(lng), float(lat)]}
    return place


def _normalize_stops(order: dict[str, Any]) -> list[dict[str, Any]]:
    """Canonical stop list for any supported order type.

    Accepts a rich ``stops`` list (typed, sequenced, with time windows / POD /
    per-stop packages) or synthesizes one from the legacy pickup + dropoff +
    additional_stops shape. Legacy additional stops are intermediate dropoffs.
    """
    rich = order.get("stops")
    if isinstance(rich, list) and rich:
        stops = [s for s in rich if isinstance(s, dict)]
        return sorted(stops, key=lambda s: int(s.get("sequence") or 0))

    stops: list[dict[str, Any]] = []
    if isinstance(order.get("pickup"), dict) and order["pickup"]:
        stops.append({"type": "pickup", "sequence": 0, **order["pickup"]})
    extras = order.get("additional_stops") or order.get("waypoints") or []
    if isinstance(extras, list):
        for i, stop in enumerate(extras):
            if isinstance(stop, dict):
                stops.append({"type": "dropoff", "sequence": i + 1, **stop})
    if isinstance(order.get("dropoff"), dict) and order["dropoff"]:
        stops.append({"type": "dropoff", "sequence": len(stops), **order["dropoff"]})
    return stops


def _split_stops(
    stops: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[dict[str, Any]]]:
    """Fleetbase payload semantics: first pickup + last dropoff + ordered
    intermediate waypoints. Untyped endpoints default to first=pickup,
    last=dropoff so hub-spoke and multi-pickup/multi-delivery both fit."""
    if not stops:
        return None, None, []
    pickup = next((s for s in stops if s.get("type") == "pickup"), None)
    dropoff = next((s for s in reversed(stops) if s.get("type") == "dropoff"), None)
    if pickup is None:
        pickup = stops[0]
    if dropoff is None:
        dropoff = stops[-1]
    intermediate = [s for s in stops if s is not pickup and s is not dropoff]
    return pickup, dropoff, intermediate


def _waypoint_from_stop(stop: dict[str, Any], index: int) -> dict[str, Any]:
    """Fleetbase waypoint entry: place fields + sequencing/import keys.

    Array position is the authoritative sequence (upstream assigns `order` by
    index); `_import_id` lets entities resolve their destination waypoint.
    Extra fields (type, time windows, service_time, pod) persist on Fleetbase
    versions that support them and are otherwise ignored harmlessly — the
    full-fidelity record always round-trips via meta.stops.
    """
    waypoint = place_from_address(stop.get("address") if isinstance(stop.get("address"), dict) else stop)
    if stop.get("id"):
        waypoint["_import_id"] = stop["id"]
    waypoint["type"] = stop.get("type") or "dropoff"
    waypoint["order"] = index
    for src, dest in (
        ("time_window_start", "time_window_start"),
        ("time_window_end", "time_window_end"),
        ("service_time_seconds", "service_time"),
        ("notes", "notes"),
    ):
        if stop.get(src) is not None:
            waypoint[dest] = stop[src]
    if stop.get("pod_required") is not None:
        waypoint["pod_required"] = stop["pod_required"]
    return waypoint


def _dims_from_package(pkg: dict[str, Any]) -> tuple[float | None, float | None, float | None, str]:
    """Extract L/W/H + unit for Fleetbase Entity (volume → VROOM capacity litres)."""
    dims = pkg.get("dimensions") if isinstance(pkg.get("dimensions"), dict) else {}
    length = (
        pkg.get("length")
        or pkg.get("length_cm")
        or dims.get("length")
        or dims.get("length_cm")
    )
    width = (
        pkg.get("width")
        or pkg.get("width_cm")
        or dims.get("width")
        or dims.get("width_cm")
    )
    height = (
        pkg.get("height")
        or pkg.get("height_cm")
        or dims.get("height")
        or dims.get("height_cm")
    )
    unit = (
        pkg.get("dimensions_unit")
        or dims.get("unit")
        or dims.get("dimensions_unit")
        or (
            "cm"
            if any(k in pkg or k in dims for k in ("length_cm", "width_cm", "height_cm"))
            else "cm"
        )
    )
    try:
        l = float(length) if length is not None else None
        w = float(width) if width is not None else None
        h = float(height) if height is not None else None
    except (TypeError, ValueError):
        return None, None, None, str(unit)
    return l, w, h, str(unit)


def _entity_from_package(pkg: dict[str, Any], *, stop_id: Any = None) -> dict[str, Any]:
    length, width, height, dim_unit = _dims_from_package(pkg)
    meta: dict[str, Any] = {
        k: v for k, v in {"porterchain_package_id": pkg.get("id")}.items() if v
    }
    entity: dict[str, Any] = {
        "name": pkg.get("name") or pkg.get("package_type") or "Parcel",
        "description": pkg.get("description"),
        "quantity": pkg.get("quantity") or 1,
        "weight": pkg.get("weight_kg") or pkg.get("weight"),
        "weight_unit": pkg.get("weight_unit") or "kg",
        "length": length,
        "width": width,
        "height": height,
        "dimensions_unit": dim_unit if any(v is not None for v in (length, width, height)) else None,
        "meta": meta,
    }
    if stop_id:
        # Stock Fleetbase: destination_uuid is a places.uuid FK. PC stop ids
        # (UUIDs or import keys like "pc-stop-1" / "s1") are NOT place rows —
        # sending them 500s with entities_destination_uuid_foreign.
        # Pin via meta + waypoint `_import_id` only; never set destination_uuid
        # at create time (we do not have Fleetbase place UUIDs yet).
        meta["destination_import_id"] = str(stop_id)
        meta["porterchain_stop_id"] = str(stop_id)
    return {k: v for k, v in entity.items() if v is not None and v != {}}


def _entities_from_stops(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-stop packages → Fleetbase entities pinned to their waypoint.

    Prefer waypoint `_import_id` + entity meta.destination_import_id. Never emit
    destination_uuid for PC stop ids (places FK).
    """
    entities: list[dict[str, Any]] = []
    for stop in stops:
        stop_id = stop.get("id")
        packages = stop.get("packages")
        if not isinstance(packages, list):
            continue
        for pkg in packages:
            if not isinstance(pkg, dict):
                continue
            entities.append(_entity_from_package(pkg, stop_id=stop_id))
    return entities


def _entities_from_order_packages(
    packages: list[Any], *, dropoff_stop_id: Any = None
) -> list[dict[str, Any]]:
    """Order-level Package rows (not nested under stops) → Fleetbase entities."""
    entities: list[dict[str, Any]] = []
    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
        entities.append(_entity_from_package(pkg, stop_id=dropoff_stop_id))
    return entities


def build_order_payload(order: dict[str, Any], *, company_uuid: str | None = None) -> dict[str, Any]:
    """Build Fleetbase order create/update body from Porterchain order fields."""
    stops = _normalize_stops(order)
    pickup_stop, dropoff_stop, intermediate = _split_stops(stops)

    payload: dict[str, Any] = {
        # Fleetbase requires a resolvable OrderConfig key (default transport).
        "type": order.get("fleetbase_order_type") or order.get("order_type") or "transport",
        "pickup": place_from_address(pickup_stop or order.get("pickup") or {}),
        "dropoff": place_from_address(dropoff_stop or order.get("dropoff") or {}),
        "scheduled_at": order.get("scheduled_at"),
        "meta": {
            "porterchain_order_id": order.get("porterchain_order_id") or order.get("id"),
            "tracking_number": order.get("tracking_number"),
            "order_number": order.get("order_number"),
            "merchant_id": order.get("merchant_id"),
        },
        "internal_id": order.get("order_number") or order.get("tracking_number"),
    }
    if company_uuid:
        payload["company_uuid"] = company_uuid
    if order.get("order_config") or order.get("fleetbase_order_config"):
        payload["order_config"] = order.get("order_config") or order.get("fleetbase_order_config")
    if order.get("special_instructions"):
        payload["notes"] = order["special_instructions"]
    if order.get("pod_required") is not None:
        payload["pod_required"] = order["pod_required"]

    if intermediate:
        waypoints = [_waypoint_from_stop(s, i) for i, s in enumerate(intermediate)]
        payload["waypoints"] = waypoints
        # Legacy mirror kept for existing consumers.
        payload["meta"]["additional_stops"] = waypoints
    if len(stops) > 2:
        # Full-fidelity stop records (type, sequence, windows, POD) — the
        # round-trip source of truth regardless of Fleetbase version support.
        payload["meta"]["stops"] = stops

    entities = _entities_from_stops(stops)
    # Order-level packages (Package rows / quote cargo) when stops have none.
    if not entities:
        order_packages = order.get("packages")
        if isinstance(order_packages, list) and order_packages:
            dropoff_id = (dropoff_stop or {}).get("id") if isinstance(dropoff_stop, dict) else None
            entities = _entities_from_order_packages(order_packages, dropoff_stop_id=dropoff_id)
    if entities:
        payload["entities"] = entities

    # Fleetbase OrchestrationPayloadBuilder falls back to order meta when entities
    # lack dimensions — keep weight/volume/parcels for capacity-aware VROOM.
    weight_kg = order.get("weight_kg")
    volume_m3 = order.get("volume_m3")
    parcels = order.get("parcels") or (len(entities) if entities else None)
    if weight_kg is not None:
        payload["meta"]["weight_kg"] = weight_kg
    if volume_m3 is not None:
        payload["meta"]["volume_m3"] = volume_m3
    if parcels is not None:
        payload["meta"]["parcels"] = parcels
    return payload


def _fleetbase_required_phone(driver: dict[str, Any]) -> str | None:
    """Fleetbase POST /v1/drivers requires phone. Seed/test drivers often omit it.

    Prefer the real phone; otherwise derive a deterministic NA E.164 from the
    PorterChain driver id so sync is not permanently blocked (meta flags synthetic).
    """
    raw = (driver.get("phone") or "").strip()
    if raw:
        return raw
    seed = str(driver.get("porterchain_driver_id") or driver.get("id") or "").replace("-", "")
    if len(seed) < 7:
        return None
    # +1 555 01XX XXX — reserved fictitious block; last 7 hex digits → decimal digits
    digits = "".join(c for c in seed if c.isdigit()) + "".join(
        str(int(c, 16) % 10) for c in seed if c in "abcdef"
    )
    tail = (digits + "0000000")[:7]
    return f"+1555{tail}"


def build_driver_payload(driver: dict[str, Any], *, company_uuid: str | None = None) -> dict[str, Any]:
    phone = _fleetbase_required_phone(driver)
    meta: dict[str, Any] = {
        "porterchain_driver_id": driver.get("porterchain_driver_id") or driver.get("id"),
    }
    if phone and not (driver.get("phone") or "").strip():
        meta["porterchain_phone_synthetic"] = True
    payload: dict[str, Any] = {
        "name": driver.get("full_name") or driver.get("name"),
        "email": driver.get("email"),
        "phone": phone,
        "meta": meta,
        "internal_id": driver.get("id"),
    }
    if company_uuid:
        payload["company_uuid"] = company_uuid
    vehicle_uuid = _mysql_uuid_or_none(driver.get("fleetbase_vehicle_id"))
    if vehicle_uuid:
        payload["vehicle_uuid"] = vehicle_uuid
    return {k: v for k, v in payload.items() if v is not None}


def build_vehicle_payload(vehicle: dict[str, Any], *, company_uuid: str | None = None) -> dict[str, Any]:
    make_model = (vehicle.get("make_model") or "").split(" ", 1)
    make = vehicle.get("make") or (make_model[0] if make_model else None)
    model = vehicle.get("model") or (make_model[1] if len(make_model) > 1 else None)
    payload: dict[str, Any] = {
        "plate_number": vehicle.get("plate_number"),
        "make": make,
        "model": model,
        "meta": {"porterchain_vehicle_id": vehicle.get("porterchain_vehicle_id") or vehicle.get("id")},
        "internal_id": vehicle.get("id"),
    }
    if company_uuid:
        payload["company_uuid"] = company_uuid
    if vehicle.get("vehicle_class"):
        raw = str(vehicle["vehicle_class"])
        spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw).lower().replace("-", "_")
        compact = spaced.replace("_", "").replace(" ", "")
        aliases = {
            "cargovan": "cargo_van",
            "highroof": "sprinter_van",
            "sprinter": "sprinter_van",
            "sprintervan": "sprinter_van",
            "box16": "box_16",
            "boxtruck": "box_16",
            "box20": "box_20",
            "sedan": "sedan_suv",
            "suv": "sedan_suv",
            "sedansuv": "sedan_suv",
        }
        payload["type"] = aliases.get(compact) or aliases.get(spaced) or spaced
    # Fleetbase VROOM capacity SoT: payload_capacity* first-class columns.
    capacity_kg = vehicle.get("capacity_kg") or vehicle.get("payload_capacity")
    if capacity_kg is not None:
        try:
            payload["payload_capacity"] = float(capacity_kg)
            # Legacy alias still accepted by older Fleetbase builds.
            payload["capacity"] = float(capacity_kg)
        except (TypeError, ValueError):
            pass
    volume_m3 = vehicle.get("capacity_volume_m3") or vehicle.get("payload_capacity_volume")
    if volume_m3 is not None:
        try:
            payload["payload_capacity_volume"] = float(volume_m3)
            payload["meta"]["max_volume_m3"] = float(volume_m3)
        except (TypeError, ValueError):
            pass
    pallets = vehicle.get("capacity_pallets") or vehicle.get("payload_capacity_pallets")
    if pallets is not None:
        try:
            payload["payload_capacity_pallets"] = int(pallets)
        except (TypeError, ValueError):
            pass
    parcels = vehicle.get("capacity_parcels") or vehicle.get("payload_capacity_parcels")
    if parcels is not None:
        try:
            payload["payload_capacity_parcels"] = int(parcels)
        except (TypeError, ValueError):
            pass
    elif capacity_kg is not None:
        # Sensible default so parcel-dimension demand is constrained.
        payload["payload_capacity_parcels"] = 100
    driver_uuid = _mysql_uuid_or_none(vehicle.get("fleetbase_driver_id"))
    if driver_uuid:
        payload["driver_uuid"] = driver_uuid
    if vehicle.get("is_active") is False:
        payload["status"] = "disabled"
    elif vehicle.get("is_active") is not None:
        payload["status"] = "active"
    return {k: v for k, v in payload.items() if v is not None}
