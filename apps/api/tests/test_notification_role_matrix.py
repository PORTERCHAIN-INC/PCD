"""Notification matrix: every template × user type, plus event-router recipients."""

from __future__ import annotations

import uuid

import pytest
from porterchain_shared.events.catalog import DomainEventType

from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.event_router import _specs_for_event
from porterchain_api.notification_engine.templates import TEMPLATE_META, TEMPLATES

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
        "crm",
    }


@pytest.mark.parametrize("user_role", USER_TYPES)
@pytest.mark.parametrize("template_key", sorted(TEMPLATES.keys()))
def test_in_app_inbox_for_each_user_type_and_template(db, user_role: str, template_key: str) -> None:
    """Every template can land in each portal user's in-app inbox."""
    from porterchain_api.notification_engine.preference_service import PreferenceService

    user_id = f"matrix-{user_role}-{uuid.uuid4().hex[:10]}"
    engine = get_notification_engine()
    category = TEMPLATE_META[template_key]["category"]
    # Marketing is OFF by default (Phase 2); force-enable for inbox capability coverage.
    if category == "marketing":
        PreferenceService().upsert(
            db,
            user_role=user_role,
            user_id=user_id,
            category="marketing",
            in_app_enabled=True,
        )

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
    if template_key == "lead_sla_escalation":
        ids = {item["id"] for item in inbox["items"]}
        assert rec.id not in ids
        return
    assert inbox["unread_count"] >= 1
    ids = {item["id"] for item in inbox["items"]}
    assert rec.id in ids
    item = next(i for i in inbox["items"] if i["id"] == rec.id)
    assert item["category"] == category
    assert item["title"]
    assert item["is_read"] is False

    db.rollback()

def test_event_dispatch_multi_populates_all_primary_roles(db) -> None:
    """EXCEPTION_OPENED fans out to customer, merchant, and real admin staff."""
    from porterchain_api.admin_models import AdminUser
    from porterchain_api.notification_engine.staff_fanout import expand_staff_specs

    admin = AdminUser(
        clerk_user_id=f"clerk_{uuid.uuid4().hex[:12]}",
        email=f"ops-{uuid.uuid4().hex[:6]}@porterchain.test",
        role="dispatcher",
        is_active=True,
    )
    db.add(admin)
    db.flush()

    engine = get_notification_engine()
    payload = {
        **EVENT_PAYLOAD,
        "customer_id": f"cust-{uuid.uuid4().hex[:8]}",
        "merchant_id": f"merch-{uuid.uuid4().hex[:8]}",
        "driver_id": f"drv-{uuid.uuid4().hex[:8]}",
    }
    specs = expand_staff_specs(db, _specs_for_event(DomainEventType.EXCEPTION_OPENED, payload))
    in_app = [s for s in specs if s["channel"] == "in_app"]
    records = engine.dispatch_multi(db, in_app, event_type=DomainEventType.EXCEPTION_OPENED)
    assert len(records) >= 3
    assert all(r.recipient_id != "system" for r in records)

    for role, rid in (
        ("customer", payload["customer_id"]),
        ("merchant", payload["merchant_id"]),
        ("admin", admin.id),
    ):
        inbox = engine.inbox_payload(db, user_role=role, user_id=rid, limit=20)
        assert any(i["category"] == "orders" for i in inbox["items"]), f"missing inbox for {role}"

    db.rollback()


def test_no_system_recipient_in_staff_specs() -> None:
    # Routine booking.confirmed / assignment have no staff fanout; exceptions still expand.
    specs = _specs_for_event(DomainEventType.EXCEPTION_OPENED, EVENT_PAYLOAD)
    assert all(s["recipient_id"] != "system" for s in specs)
    assert any(str(s["recipient_id"]).startswith("__staff:") for s in specs)
    quiet = _specs_for_event(DomainEventType.BOOKING_CONFIRMED, EVENT_PAYLOAD)
    assert all(not str(s["recipient_id"]).startswith("__staff:") for s in quiet)
    quiet_assign = _specs_for_event(DomainEventType.DRIVER_ASSIGNED, EVENT_PAYLOAD)
    assert all(not str(s["recipient_id"]).startswith("__staff:") for s in quiet_assign)