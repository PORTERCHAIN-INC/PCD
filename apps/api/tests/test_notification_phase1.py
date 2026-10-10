"""Phase 1 notification upgrade — context, fan-out, idempotency."""

from __future__ import annotations

import uuid

from porterchain_shared.events.catalog import DomainEventType

from porterchain_api.admin_models import AdminUser
from porterchain_api.notification_engine.context import (
    hydrate_order_context,
    merge_notification_context,
)
from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.event_router import _specs_for_event
from porterchain_api.notification_engine.staff_fanout import (
    expand_staff_specs,
    roles_for_topic,
    staff_sentinel,
)


def test_roles_for_topic_ops_includes_dispatcher() -> None:
    roles = roles_for_topic("ops")
    assert "dispatcher" in roles
    assert "admin" in roles
    assert "super_admin" in roles


def test_roles_for_topic_finance() -> None:
    roles = roles_for_topic("finance")
    assert "finance" in roles
    assert "super_admin" in roles


def test_roles_for_topic_growth() -> None:
    roles = roles_for_topic("growth")
    assert "super_admin" in roles
    assert staff_sentinel("growth") == "__staff:growth__"


def test_driver_assigned_specs_include_customer_when_hydrated() -> None:
    payload = {
        "customer_id": "cust-1",
        "merchant_id": "merch-1",
        "driver_id": "drv-1",
        "email": "c@example.com",
        "order_number": "ORD-1",
        "tracking_number": "TRK-1",
    }
    specs = _specs_for_event(DomainEventType.DRIVER_ASSIGNED, payload)
    roles = {s["recipient_type"] for s in specs}
    assert "customer" in roles
    assert "merchant" in roles
    assert "driver" in roles
    # Ops already sees assignment on the board. Do not also page staff.
    assert all(s["recipient_id"] != staff_sentinel("ops") for s in specs)
    assert all(s["recipient_id"] != "system" for s in specs)


def test_exception_opened_specs() -> None:
    specs = _specs_for_event(
        DomainEventType.EXCEPTION_OPENED,
        {
            "customer_id": "c1",
            "merchant_id": "m1",
            "email": "c@example.com",
            "exception_type": "failed",
            "tracking_number": "TRK-1",
            "order_number": "ORD-1",
        },
    )
    channels = {(s["recipient_type"], s["channel"]) for s in specs}
    assert ("customer", "email") in channels
    assert ("customer", "push") in channels
    assert ("merchant", "in_app") in channels
    assert ("admin", "in_app") in channels


def test_expand_staff_replaces_sentinel(db) -> None:
    admin = AdminUser(
        clerk_user_id=f"clerk_{uuid.uuid4().hex[:12]}",
        email=f"a-{uuid.uuid4().hex[:6]}@test.com",
        role="dispatcher",
        is_active=True,
    )
    db.add(admin)
    db.flush()
    specs = [
        {
            "template_key": "booking_confirmed",
            "channel": "in_app",
            "recipient_type": "admin",
            "recipient_id": staff_sentinel("ops"),
            "context": {},
            "search_tags": {},
            "priority": "normal",
        }
    ]
    expanded = expand_staff_specs(db, specs)
    assert any(s["recipient_id"] == admin.id for s in expanded)
    assert all(s["recipient_id"] != "system" for s in expanded)
    assert all(s.get("search_tags", {}).get("fanout_topic") == "ops" for s in expanded)
    db.rollback()


def test_dispatch_idempotent(db) -> None:
    engine = get_notification_engine()
    kwargs = {
        "event_type": "booking.confirmed",
        "template_key": "booking_confirmed",
        "channel": "email",
        "recipient_type": "customer",
        "recipient_id": f"cust-{uuid.uuid4().hex[:8]}",
        "recipient_address": "idem@example.com",
        "context": {"tracking_number": "TRK", "order_number": "ORD"},
        "correlation_id": f"corr-{uuid.uuid4().hex[:8]}",
    }
    a = engine.dispatch(db, **kwargs)
    b = engine.dispatch(db, **kwargs)
    assert a is not None and b is not None
    assert a.id == b.id
    db.rollback()


def test_merge_and_hydrate_empty_order(db) -> None:
    assert hydrate_order_context(db, None) == {}
    assert hydrate_order_context(db, "missing-order-id") == {}
    merged = merge_notification_context({"driver_id": "d1"}, {"customer_id": "c1", "driver_id": "old"})
    assert merged["driver_id"] == "d1"
    assert merged["customer_id"] == "c1"
