"""Shopify orders/create → merchant booking request.

Adapter-Version: 1.0.0
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest


def _as_str(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, (int, float)) and value == value:
        return str(value)
    return ""


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _record(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def format_shopify_address(raw: dict[str, Any]) -> str:
    parts = [
        _as_str(raw.get("address1")),
        _as_str(raw.get("address2")),
        _as_str(raw.get("city")),
        _as_str(raw.get("province_code") or raw.get("province")),
        _as_str(raw.get("zip")),
        "Canada",
    ]
    return ", ".join(p for p in parts if p)


def shipping_address(payload: dict[str, Any]) -> dict[str, Any] | None:
    return _record(payload.get("shipping_address")) or _record(payload.get("destination"))


def order_ids(payload: dict[str, Any]) -> tuple[str, str]:
    order_id = _as_str(payload.get("id"))
    name = _as_str(payload.get("name")) or (f"#{order_id}" if order_id else "")
    return order_id, name


def line_weight_kg(payload: dict[str, Any]) -> float | None:
    items = payload.get("line_items")
    if not isinstance(items, list):
        return None
    total = 0.0
    found = False
    for item in items:
        if not isinstance(item, dict):
            continue
        grams = _as_float(item.get("grams"))
        qty = _as_float(item.get("quantity")) or 1
        if grams and grams > 0:
            total += (grams / 1000.0) * qty
            found = True
    return total if found else None


def map_shopify_order(
    payload: dict[str, Any],
    *,
    pickup: AddressInput,
) -> MerchantBookDeliveryRequest:
    address = shipping_address(payload)
    if not address:
        raise ValueError("shipping_address_required")
    formatted = format_shopify_address(address)
    if not _as_str(address.get("address1")):
        raise ValueError("shipping_address_required")
    order_id, name = order_ids(payload)
    if not order_id:
        raise ValueError("shopify_order_id_required")
    dropoff = AddressInput(
        formatted=formatted,
        lat=_as_float(address.get("latitude")),
        lng=_as_float(address.get("longitude")),
        postal=_as_str(address.get("zip")) or None,
    )
    contact = " ".join(
        p
        for p in [
            _as_str(address.get("name")),
            _as_str(address.get("phone")),
        ]
        if p
    )
    notes = contact or None
    return MerchantBookDeliveryRequest(
        pickup=pickup,
        dropoff=dropoff,
        scheduled_at=datetime.now(UTC),
        schedule_mode="now",
        internal_reference=name or f"shopify-{order_id}",
        purchase_order_number=order_id,
        special_instructions=notes,
        weight_kg=line_weight_kg(payload),
        vehicle_class="cargo_van",
        package_type="looseParcel",
    )
