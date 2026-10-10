"""AA words, AB Toronto day bounds, AC quote snapshot, AE consignee email."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from porterchain_api.domain.catalog_labels import order_state_label, vehicle_label
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.consignee_notify import (
    consignee_error_message,
    resolve_consignee_email,
)
from porterchain_api.merchant_engine.quote_snapshot import (
    merchant_quote_picture,
    sanitize_pricing_breakdown,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.toronto import parse_toronto_day_bound
from porterchain_api.merchant_models import Merchant, MerchantRecipient, MerchantUser
from porterchain_api.schemas_merchant import AddressInput, MerchantBookDeliveryRequest


def test_order_and_vehicle_words() -> None:
    assert order_state_label("DISPATCH_READY") == "Ready for pickup"
    assert vehicle_label("cargo_van") == "Cargo van"
    assert vehicle_label("cargo_van") == "Cargo van"


def test_toronto_day_is_not_utc_midnight() -> None:
    start = parse_toronto_day_bound("2026-01-10")
    end = parse_toronto_day_bound("2026-01-10", end=True)
    assert start is not None and end is not None
    # Eastern standard: midnight Toronto is 05:00 UTC
    assert start == datetime(2026, 1, 10, 5, 0, 0)
    assert end.hour == 4 or end.day == 11
    legacy = parse_toronto_day_bound("2026-07-10T00:00:00Z")
    # July is EDT (UTC-4) — date picker meant July 10 Toronto, not UTC
    assert legacy == datetime(2026, 7, 10, 4, 0, 0)


def test_quote_picture_drops_vendor_metadata() -> None:
    picture = merchant_quote_picture(
        {
            "final_cents": 2260,
            "subtotal_cents": 2000,
            "tax_cents": 260,
            "currency": "cad",
            "items": [{"code": "base", "label": "Base fare", "amount_cents": 2000}],
            "metadata": {"routing_source": "valhalla", "distance_meters": 5400},
        },
        vehicle_class="cargo_van",
        package_type="looseParcel",
    )
    blob = str(picture)
    assert "valhalla" not in blob.lower()
    assert picture["amount_cents"] == 2260
    assert picture["tax_cents"] == 260
    assert picture["line_items"][0]["label"] == "Base fare"
    clean = sanitize_pricing_breakdown(
        {"final_cents": 100, "metadata": {"routing_source": "osrm"}, "items": []}
    )
    assert clean is not None
    assert "metadata" not in clean
    assert "routing_source" not in str(clean)


def _ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Floor Co {suffix}",
        email=f"floor-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
        profile={},
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"owner-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def _body(**extra: object) -> MerchantBookDeliveryRequest:
    payload = dict(
        pickup=AddressInput(formatted="100 King St W, Toronto", postal="M5X 1A1", lat=43.65, lng=-79.38),
        dropoff=AddressInput(formatted="200 Bay St, Toronto", postal="M5J 2J2", lat=43.65, lng=-79.38),
        scheduled_at=datetime.now(UTC),
        vehicle_class="cargo_van",
        package_type="looseParcel",
    )
    payload.update(extra)
    return MerchantBookDeliveryRequest(**payload)


def test_create_shipment_stores_quote_snapshot(db, settings) -> None:
    from porterchain_api.merchant_engine.booking_service import MerchantBookingService

    ctx = _ctx(db)
    with patch(
        "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
        side_effect=lambda db, order, **_k: order,
    ):
        order = MerchantBookingService().create_shipment(db, settings, ctx, _body())
    snap = (order.compliance_metadata or {}).get("quote") or {}
    assert snap.get("amount_cents") == order.amount_cents
    assert snap.get("line_items") is not None
    assert "routing_source" not in snap
    assert "valhalla" not in str(snap).lower()
    assert (order.compliance_metadata or {}).get("vehicle_class") == "cargo_van"


def test_consignee_email_from_recipient_and_direct(db) -> None:
    ctx = _ctx(db)
    rec = MerchantRecipient(
        merchant_id=ctx.merchant.id,
        name="Dock",
        email="dock@receiver.example",
    )
    db.add(rec)
    db.flush()
    via_recipient = resolve_consignee_email(db, ctx, _body(recipient_id=rec.id))
    assert via_recipient == "dock@receiver.example"
    via_direct = resolve_consignee_email(
        db, ctx, _body(consignee_email="recv@shop.example")
    )
    assert via_direct == "recv@shop.example"
    assert "receiver email" in consignee_error_message("consignee_email_required").lower()


def test_book_stores_consignee_for_the_booked_notice(db, settings) -> None:
    from porterchain_api.booking_models import DomainEvent
    from porterchain_api.merchant_engine.booking_service import MerchantBookingService

    with (
        patch(
            "porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
            side_effect=lambda db, order, **_k: order,
        ),
        patch(
            "porterchain_api.notification_engine.engine.NotificationEngine.dispatch",
            return_value=None,
        ),
    ):
        order = MerchantBookingService().create_shipment(
            db, settings, _ctx(db), _body(consignee_email="recv@shop.example")
        )
    assert (order.compliance_metadata or {}).get("consignee", {}).get("email") == "recv@shop.example"
    event = (
        db.query(DomainEvent)
        .filter(
            DomainEvent.aggregate_id == order.id,
            DomainEvent.event_type == "merchant.booking_created",
        )
        .one()
    )
    assert event.payload.get("tracking_number")


def test_display_state_on_order_row(db) -> None:
    from porterchain_api.booking_engine.numbers import (
        generate_order_number,
        generate_tracking_number,
    )
    from porterchain_api.booking_models import Order
    from porterchain_api.domain.states import OrderState
    from porterchain_api.order_engine.platform_helpers import OrderPlatformHelpersMixin

    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.DISPATCH_READY.value,
        merchant_id=_ctx(db).merchant.id,
        amount_cents=1000,
        pickup={"formatted": "100 King"},
        dropoff={"formatted": "200 Bay"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()

    class _H(OrderPlatformHelpersMixin):
        def __init__(self) -> None:
            self._tower = type("T", (), {"_sla_status": staticmethod(lambda *_a, **_k: "ok")})()

    row = _H()._row(db, order, {}, {})
    assert row["state"] == "DISPATCH_READY"
    assert row["display_state"] == "Ready for pickup"
