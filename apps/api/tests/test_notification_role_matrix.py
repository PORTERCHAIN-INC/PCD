"""Notification matrix: every template × user type, plus event-router recipients."""

from __future__ import annotations

import uuid

import pytest

from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.event_router import _specs_for_event
from porterchain_api.notification_engine.templates import TEMPLATE_META, TEMPLATES
from porterchain_shared.events.catalog import DomainEventType

USER_TYPES = ("admin", "merchant", "driver", "customer")

FULL_CONTEXT = {
    "tracking_number": "TRK-MATRIX-001",
    "order_number": "ORD-MATRIX-001",
    "quote_id": "Q-MATRIX-001",
    "recovery_url": "https://porterchain.com/checkout",
    "amount_display": "$42.00",
    "invoice_number": "INV-MATRIX-001",
    "merchant_name": "Matrix Merchant",
    "claim_number": "CLM-001",
    "claim_type": "damage",
    "status": "open",
    "ticket_number": "TKT-001",
    "subject": "Help needed",
    "message": "Matrix test alert",
    "title": "Matrix alert",
    "body": "Matrix alert body",
    "reset_url": "https://porterchain.com/reset",
    "code": "123456",
    "celsius": "12.5",
    "route_id": "RTE-001",
    "stops_count": "3",
    "deep_link": "/orders/ORD-MATRIX-001",
}

# Domain events that should produce in_app (or push) for each portal persona.
EVENT_PAYLOAD = {
    "customer_id": "cust-matrix",
    "merchant_id": "merch-matrix",
    "driver_id": "drv-matrix",
    "email": "matrix@example.com",
    "contact_email": "matrix@example.com",
    "order_number": "ORD-MATRIX-001",
    "tracking_number": "TRK-MATRIX-001",
    "invoice_number": "INV-MATRIX-001",
    "merchant_name": "Matrix Merchant",
    "claim_number": "CLM-001",
    "claim_type": "damage",
    "ticket_number": "TKT-001",
    "subject": "Help",
    "status": "resolved",
    "actor_type": "driver",
    "actor_id": "drv-matrix",
    "route_id": "RTE-001",
    "stops_count": 3,
    "celsius": 12.5,
    "message": "ok",
}


def _expected_roles_for_event(event_type: str) -> set[str]:
    specs = _specs_for_event(event_type, EVENT_PAYLOAD)
    return {s["recipient_type"] for s in specs}


@pytest.mark.parametrize("template_key", sorted(TEMPLATES.keys()))
def test_every_template_has_category_meta(template_key: str) -> None:
    assert template_key in TEMPLATE_META
    assert TEMPLATE_META[template_key]["category"] in {
        "booking",
        "orders",
        "tracking",
        "payments",
        "invoices",
        "claims",
        "support",
        "marketing",
        "security",
    }


@pytest.mark.parametrize(
    "event_type,expected_roles",
    [
        (DomainEventType.BOOKING_DRAFT_CREATED, {"customer"}),
        (DomainEventType.BOOKING_CONFIRMED, {"customer", "merchant", "admin"}),
        (DomainEventType.PAYMENT_STARTED, {"customer"}),
        (DomainEventType.PAYMENT_SUCCEEDED, {"customer", "merchant", "finance"}),
        (DomainEventType.PAYMENT_FAILED, {"customer"}),
        (DomainEventType.ORDER_CREATED, {"customer", "merchant", "admin"}),
        (DomainEventType.ORDER_BOOKED, {"customer", "merchant", "admin"}),
        (DomainEventType.DRIVER_ASSIGNED, {"customer", "driver", "merchant", "admin"}),
        (DomainEventType.DRIVER_ACCEPTED, {"driver", "admin"}),
        (DomainEventType.DRIVER_REJECTED, {"admin"}),
        (DomainEventType.DRIVER_ARRIVED_PICKUP, {"customer", "admin"}),
        (DomainEventType.PARCEL_PICKED_UP, {"customer", "admin"}),
        (DomainEventType.DELIVERY_STARTED, {"customer"}),
        (DomainEventType.ORDER_NEAR_DELIVERY, {"customer"}),
        (DomainEventType.PARCEL_DELIVERED, {"customer", "driver", "admin"}),
        (DomainEventType.PROOF_COMPLETED, {"admin", "driver"}),
        (DomainEventType.INVOICE_GENERATED, {"customer", "merchant", "finance"}),
        (DomainEventType.MERCHANT_BILLED, {"merchant", "finance"}),
        (DomainEventType.REFUND_ISSUED, {"customer"}),
        (DomainEventType.CLAIM_OPENED, {"customer", "driver", "support"}),
        (DomainEventType.CLAIM_RESOLVED, {"customer", "driver", "support"}),
        (DomainEventType.SUPPORT_TICKET_CREATED, {"customer", "driver", "support"}),
        (DomainEventType.FLEETBASE_STATUS_UPDATED, {"customer"}),
        (DomainEventType.ORDER_TEMP_EXCURSION, {"admin", "merchant"}),
        ("driver.emergency", {"admin"}),
        ("driver.route_changed", {"driver"}),
        ("incident.reported", {"driver", "admin"}),
        ("driver.shift_started", {"driver"}),
        ("driver.shift_ended", {"driver"}),
        ("driver.break_started", {"driver"}),
        ("driver.break_resumed", {"driver"}),
    ],
)
def test_event_router_roles(event_type: str, expected_roles: set[str]) -> None:
    assert _expected_roles_for_event(event_type) == expected_roles


@pytest.mark.parametrize("user_role", USER_TYPES)
@pytest.mark.parametrize("template_key", sorted(TEMPLATES.keys()))
def test_in_app_inbox_for_each_user_type_and_template(db, user_role: str, template_key: str) -> None:
    """Every template can land in each portal user's in-app inbox."""
    user_id = f"matrix-{user_role}-{uuid.uuid4().hex[:10]}"
    engine = get_notification_engine()
    category = TEMPLATE_META[template_key]["category"]

    rec = engine.dispatch(
        db,
        event_type="test.matrix",
        template_key=template_key,
        channel="in_app",
        recipient_type=user_role,
        recipient_id=user_id,
        context=FULL_CONTEXT,
        priority="normal",
    )
    assert rec is not None, f"dispatch returned None for {user_role}/{template_key}"
    assert rec.status == "sent"
    assert rec.category == category
    assert rec.channel == "in_app"

    inbox = engine.inbox_payload(db, user_role=user_role, user_id=user_id, limit=50)
    assert inbox["unread_count"] >= 1
    ids = {item["id"] for item in inbox["items"]}
    assert rec.id in ids
    item = next(i for i in inbox["items"] if i["id"] == rec.id)
    assert item["category"] == category
    assert item["title"]
    assert item["is_read"] is False

    db.rollback()


def test_event_dispatch_multi_populates_all_primary_roles(db) -> None:
    """DRIVER_ASSIGNED fans out to customer, merchant, driver, admin (system)."""
    engine = get_notification_engine()
    payload = {
        **EVENT_PAYLOAD,
        "customer_id": f"cust-{uuid.uuid4().hex[:8]}",
        "merchant_id": f"merch-{uuid.uuid4().hex[:8]}",
        "driver_id": f"drv-{uuid.uuid4().hex[:8]}",
    }
    specs = _specs_for_event(DomainEventType.DRIVER_ASSIGNED, payload)
    in_app = [s for s in specs if s["channel"] == "in_app"]
    records = engine.dispatch_multi(db, in_app, event_type=DomainEventType.DRIVER_ASSIGNED)
    assert len(records) >= 4

    for role, rid in (
        ("customer", payload["customer_id"]),
        ("merchant", payload["merchant_id"]),
        ("driver", payload["driver_id"]),
        ("admin", "system"),
    ):
        inbox = engine.inbox_payload(db, user_role=role, user_id=rid, limit=20)
        assert any(i["category"] == "tracking" for i in inbox["items"]), f"missing inbox for {role}"

    db.rollback()
