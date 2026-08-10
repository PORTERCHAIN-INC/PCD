"""Address and payload mappers — Porterchain models → Fleetbase API payloads."""

from __future__ import annotations

from typing import Any


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


def _entities_from_stops(stops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-stop packages → Fleetbase entities pinned to their waypoint.

    `destination_uuid` intentionally carries the PC stop id: upstream
    `Payload::setEntities()` resolves it against waypoint `_import_id`.
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
            entity = {
                "name": pkg.get("name") or pkg.get("package_type") or "Parcel",
                "description": pkg.get("description"),
                "quantity": pkg.get("quantity"),
                "weight": pkg.get("weight_kg") or pkg.get("weight"),
                "meta": {k: v for k, v in {"porterchain_package_id": pkg.get("id")}.items() if v},
            }
            if stop_id:
                entity["destination_uuid"] = stop_id
            entities.append({k: v for k, v in entity.items() if v is not None and v != {}})
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
    if entities:
        payload["entities"] = entities
    return payload


def build_driver_payload(driver: dict[str, Any], *, company_uuid: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": driver.get("full_name") or driver.get("name"),
        "email": driver.get("email"),
        "phone": driver.get("phone"),
        "meta": {"porterchain_driver_id": driver.get("porterchain_driver_id") or driver.get("id")},
        "internal_id": driver.get("id"),
    }
    if company_uuid:
        payload["company_uuid"] = company_uuid
    if driver.get("fleetbase_vehicle_id"):
        payload["vehicle_uuid"] = driver["fleetbase_vehicle_id"]
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
        payload["type"] = vehicle["vehicle_class"]
    if vehicle.get("capacity_kg"):
        payload["capacity"] = vehicle["capacity_kg"]
    return {k: v for k, v in payload.items() if v is not None}
