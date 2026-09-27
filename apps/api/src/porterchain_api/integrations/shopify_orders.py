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


PORTERCHAIN_SERVICE_CODE = "porterchain_same_day"

# Buyer email and phone are for the delivery and for privacy requests. Never a marketing list.
_CANADA = {"CA", "CAN", "CANADA"}


def is_canada_country(value: Any) -> bool:
    raw = _as_str(value).upper()
    if not raw:
        return True
    return raw in _CANADA


def format_shopify_address(raw: dict[str, Any]) -> str:
    country = _as_str(raw.get("country") or raw.get("country_code") or raw.get("countryCode"))
    if country.upper() in {"CA", "CAN"}:
        country = "Canada"
    parts = [
        _as_str(raw.get("address1")),
        _as_str(raw.get("address2")),
        _as_str(raw.get("city")),
        _as_str(raw.get("province_code") or raw.get("province")),
        _as_str(raw.get("zip") or raw.get("postal_code")),
        country or "Canada",
    ]
    return ", ".join(p for p in parts if p)


def porterchain_shipping_selected(payload: dict[str, Any]) -> bool:
    """Book when the buyer chose PorterChain.

    Orders with no shipping_lines still book (non-checkout ingress and existing fixtures).
    If lines are present, one of them must be our stable service code or name.
    """
    lines = payload.get("shipping_lines")
    if not isinstance(lines, list) or not lines:
        return True
    for line in lines:
        if not isinstance(line, dict):
            continue
        code = _as_str(line.get("code")).lower()
        title = _as_str(line.get("title")).lower()
        source = _as_str(line.get("source")).lower()
        if code == PORTERCHAIN_SERVICE_CODE or "porterchain" in title or "porterchain" in source:
            return True
    return False


def unpaid_non_cod(payload: dict[str, Any]) -> bool:
    status = _as_str(payload.get("financial_status")).lower()
    if status in {"", "paid", "partially_paid", "partially_refunded", "authorized"}:
        return False
    gateways = payload.get("payment_gateway_names")
    if isinstance(gateways, list):
        for gateway in gateways:
            label = _as_str(gateway).lower()
            if "cod" in label or "cash" in label:
                return False
    return status in {"pending", "unpaid", "voided"}


def quote_id_from_order(payload: dict[str, Any]) -> str | None:
    notes = payload.get("note_attributes")
    if isinstance(notes, list):
        for attr in notes:
            if not isinstance(attr, dict):
                continue
            name = _as_str(attr.get("name")).lower()
            if name in {"quote_id", "porterchain_quote_id"}:
                value = _as_str(attr.get("value"))
                if value:
                    return value
    lines = payload.get("shipping_lines")
    if isinstance(lines, list):
        for line in lines:
            if not isinstance(line, dict):
                continue
            metafields = line.get("metafields")
            if not isinstance(metafields, list):
                continue
            for field in metafields:
                if isinstance(field, dict) and _as_str(field.get("key")) == "quote_id":
                    value = _as_str(field.get("value"))
                    if value:
                        return value
    return None


def customer_slice(payload: dict[str, Any]) -> dict[str, Any]:
    """Stored for delivery and PIPEDA / Law 25 requests. Not a CASL marketing list."""
    customer = _record(payload.get("customer")) or {}
    address = shipping_address(payload) or {}
    first = _as_str(customer.get("first_name"))
    last = _as_str(customer.get("last_name"))
    name = _as_str(address.get("name")) or " ".join(p for p in (first, last) if p)
    return {
        "id": customer.get("id"),
        "email": _as_str(payload.get("email") or customer.get("email")) or None,
        "phone": _as_str(address.get("phone") or customer.get("phone") or payload.get("phone")) or None,
        "name": name or None,
    }


def line_item_slice(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("line_items")
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items[:40]:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "title": _as_str(item.get("title") or item.get("name")) or None,
                "sku": _as_str(item.get("sku")) or None,
                "quantity": item.get("quantity"),
            }
        )
    return out


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
