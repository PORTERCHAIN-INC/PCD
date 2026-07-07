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


def build_order_payload(order: dict[str, Any], *, company_uuid: str | None = None) -> dict[str, Any]:
    """Build Fleetbase order create/update body from Porterchain order fields."""
    payload: dict[str, Any] = {
        "pickup": place_from_address(order.get("pickup") or {}),
        "dropoff": place_from_address(order.get("dropoff") or {}),
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
    if order.get("special_instructions"):
        payload["notes"] = order["special_instructions"]
    if order.get("pod_required") is not None:
        payload["pod_required"] = order["pod_required"]
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
