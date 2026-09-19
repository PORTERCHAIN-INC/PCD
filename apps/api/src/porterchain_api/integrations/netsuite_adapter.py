"""NetSuite MVP adapter — map fulfillments to merchant bookings (§7.2.3)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest


def _parse_datetime(value: str | datetime | None) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not value:
        return datetime.now(UTC)
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _address(raw: dict[str, Any] | None) -> AddressInput:
    raw = raw or {}
    return AddressInput(
        formatted=str(raw.get("formatted") or raw.get("addrtext") or "").strip(),
        lat=raw.get("lat"),
        lng=raw.get("lng"),
    )


def map_netsuite_fulfillment(payload: dict[str, Any]) -> MerchantBookDeliveryRequest:
    """Map NetSuite item fulfillment RESTlet payload → merchant booking request."""
    external_id = str(payload.get("external_id") or payload.get("tranid") or "").strip()
    if not external_id:
        raise ValueError("external_id_required")
    pickup = _address(payload.get("pickup_address") or payload.get("location_address"))
    dropoff = _address(payload.get("ship_address") or payload.get("shipping_address"))
    if not pickup.formatted or not dropoff.formatted:
        raise ValueError("address_required")
    return MerchantBookDeliveryRequest(
        pickup=pickup,
        dropoff=dropoff,
        scheduled_at=_parse_datetime(payload.get("ship_date") or payload.get("duedate")),
        internal_reference=external_id,
        purchase_order_number=payload.get("purchase_order") or payload.get("otherrefnum"),
        cost_centre=payload.get("subsidiary"),
        special_instructions=payload.get("memo"),
        weight_kg=payload.get("weight_kg"),
        vehicle_class=payload.get("vehicle_class") or "cargoVan",
        package_type=payload.get("package_type") or "looseParcel",
    )


def netsuite_setup_bundle(*, api_base_url: str) -> dict[str, Any]:
    return {
        "integration": "netsuite",
        "status": "mvp",
        "sync_endpoint": f"{api_base_url}/v1/merchant/integrations/netsuite/sync",
        "connect_endpoint": f"{api_base_url}/v1/merchant/integrations/netsuite/connect",
        "schema_path": "integrations/netsuite/inbound.schema.json",
        "sample_path": "integrations/netsuite/samples/fulfillment.json",
        "field_mapping": {
            "external_id": "internal_reference",
            "purchase_order": "purchase_order_number",
            "ship_address": "dropoff",
            "pickup_address": "pickup",
            "ship_date": "scheduled_at",
            "memo": "special_instructions",
            "subsidiary": "cost_centre",
        },
    }
