"""Return pickups: the customer's address back to the merchant.

One path for the merchant portal and for Shopify ``returns/approve``. A return is
an ordinary order with pickup and drop-off swapped, priced by the same engine and
moved by the same driver flow; labels, tracking and POD work unchanged. The link
lives in ``compliance_metadata["return"]`` on the return and in
``compliance_metadata["returns"]`` on the original.

Contract return terms (e.g. a "returns at 50%" clause) are not modelled; returns
for a merchant on a contract schedule are flagged ``contract_return_rules_not_modelled``
so ops can adjust the invoice by hand. Loop Returns and other return apps: later.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext

SOURCE_PORTAL = "portal"
SOURCE_SHOPIFY = "shopify"

RETURNABLE_STATES = frozenset(
    {
        OrderState.DELIVERED.value,
        OrderState.POD_COMPLETED.value,
        OrderState.INVOICED.value,
        OrderState.CLOSED.value,
    }
)
_CLOSED_RETURN_STATES = frozenset({OrderState.CANCELLED.value, OrderState.FAILED.value})
CONTRACT_RETURN_NOTE = "contract_return_rules_not_modelled"

RETURN_ERRORS = {
    "order_not_found": "Order not found.",
    "return_not_delivered": "A return can be booked once the original order is delivered.",
    "return_of_return": "This order is already a return.",
    "return_already_open": "A return pickup is already open for this order.",
    "out_of_service_area": "The customer's address is outside our service area.",
    "merchant_not_active": "Your account must be active to book a return.",
}


def return_error_message(code: str) -> str:
    return RETURN_ERRORS.get(code, "Could not book this return.")


def _meta(order: Order) -> dict[str, Any]:
    return order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}


def _address(stop: Any) -> dict[str, Any]:
    from porterchain_api.schemas_merchant import AddressInput

    data = stop if isinstance(stop, dict) else {}
    allowed = set(AddressInput.model_fields)
    out = {k: v for k, v in data.items() if k in allowed and v not in (None, "")}
    out.setdefault("formatted", str(data.get("formatted") or ""))
    return out


def has_contract_schedule(merchant: Any) -> bool:
    from porterchain_pricing.policy import policy_from_config

    cfg = getattr(merchant, "pricing_config", None)
    if not isinstance(cfg, dict):
        return False
    try:
        return bool(policy_from_config(cfg).schedule.contract_schedule)
    except (TypeError, ValueError):
        return False


def is_return(order: Order) -> bool:
    return isinstance(_meta(order).get("return"), dict)


def return_body(original: Order, *, reference: str | None = None, purchase_order: str | None = None):
    """Booking request for a pickup at the original drop-off, back to the original pickup."""
    from porterchain_api.merchant_engine.booking_service import _canonical_vehicle
    from porterchain_api.merchant_engine.stop_cargo import packages_from_stops
    from porterchain_api.schemas_merchant import (
        MerchantBookDeliveryRequest,
        RouteImportPackageInput,
    )

    meta = _meta(original)
    stops = meta.get("stops") if isinstance(meta.get("stops"), list) else []
    packages = []
    for raw in packages_from_stops(stops):
        try:
            packages.append(RouteImportPackageInput.model_validate(raw))
        except ValueError:
            continue
    return MerchantBookDeliveryRequest(
        pickup=_address(original.dropoff),
        dropoff=_address(original.pickup),
        scheduled_at=datetime.now(UTC),
        schedule_mode="now",
        internal_reference=(reference or f"return-{original.tracking_number or original.id}")[:120],
        purchase_order_number=purchase_order or original.purchase_order_number,
        # Cargo lives in compliance metadata (Order has no vehicle/package columns).
        vehicle_class=_canonical_vehicle(str(meta.get("vehicle_class") or "")) or "cargo_van",
        package_type=str(meta.get("package_type") or "looseParcel"),
        weight_kg=meta.get("weight_kg"),
        dimensions=meta.get("dimensions"),
        packages=packages or None,
    )


def open_returns(original: Order) -> list[dict[str, Any]]:
    rows = _meta(original).get("returns")
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def create_return_order(
    db: Session,
    settings: Settings,
    ctx: MerchantContext,
    original: Order,
    *,
    source: str,
    idempotency_key: str,
    booking: Any = None,
    reference: str | None = None,
    purchase_order: str | None = None,
    order_source: str = OrderSource.MERCHANT.value,
    auto_dispatch: bool = True,
    extra: dict[str, Any] | None = None,
) -> Order:
    """Book the return. Raises ``BookingValidationError`` (e.g. out_of_service_area)."""
    from porterchain_api.merchant_engine.service_area import (
        assert_ontario_booking,
        merchant_coverage_fsas,
    )

    if booking is None:
        from porterchain_api.merchant_engine.booking_service import (
            MerchantBookingService,
        )

        booking = MerchantBookingService()
    body = return_body(original, reference=reference, purchase_order=purchase_order)
    assert_ontario_booking(body, extra_fsas=merchant_coverage_fsas(db, ctx.merchant))
    order = booking.create_shipment(
        db,
        settings,
        ctx,
        body,
        order_source=order_source,
        idempotency_key=idempotency_key,
        sandbox=bool(getattr(original, "is_sandbox", False)),
        auto_dispatch=auto_dispatch,
    )
    note = CONTRACT_RETURN_NOTE if has_contract_schedule(ctx.merchant) else None
    link = {
        "of": original.id,
        "of_tracking": original.tracking_number,
        "source": source,
        "created_at": datetime.now(UTC).isoformat(),
        **(extra or {}),
    }
    if note:
        link["pricing_note"] = note
    meta = dict(_meta(order))
    meta["return"] = link
    order.compliance_metadata = meta
    flag_modified(order, "compliance_metadata")

    orig_meta = dict(_meta(original))
    rows = open_returns(original)
    rows.append({"order_id": order.id, "tracking": order.tracking_number, "source": source})
    orig_meta["returns"] = rows[-20:]
    original.compliance_metadata = orig_meta
    flag_modified(original, "compliance_metadata")
    db.flush()
    return order


def return_summary(order: Order) -> dict[str, Any]:
    link = _meta(order).get("return") or {}
    return {
        "order_id": order.id,
        "tracking_number": order.tracking_number,
        "state": order.state,
        "source": link.get("source"),
        "created_at": link.get("created_at"),
        "pricing_note": link.get("pricing_note"),
        "price_cents": getattr(order, "amount_cents", None),
    }


def returns_for(db: Session, original: Order) -> list[dict[str, Any]]:
    ids = [r.get("order_id") for r in open_returns(original) if r.get("order_id")]
    if not ids:
        return []
    rows = (
        db.query(Order)
        .filter(Order.id.in_(ids), Order.merchant_id == original.merchant_id)
        .all()
    )
    by_id = {o.id: o for o in rows}
    return [return_summary(by_id[i]) for i in ids if i in by_id]


def assert_can_open_return(db: Session, original: Order) -> None:
    if is_return(original):
        raise ValueError("return_of_return")
    if original.state not in RETURNABLE_STATES:
        raise ValueError("return_not_delivered")
    for row in returns_for(db, original):
        if row.get("source") == SOURCE_PORTAL and row.get("state") not in _CLOSED_RETURN_STATES:
            raise ValueError("return_already_open")
