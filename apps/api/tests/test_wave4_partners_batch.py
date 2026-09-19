"""Wave 4 batch: merchant lifecycle notify + honest driver actions."""

from __future__ import annotations

from porterchain_api.notification_engine.event_router import _specs_for_event
from porterchain_api.notification_engine.templates import TEMPLATES
from porterchain_shared.events.catalog import DomainEventType


def test_merchant_approved_routes_staff() -> None:
    specs = _specs_for_event(
        DomainEventType.MERCHANT_APPROVED,
        {"merchant_id": "m1", "company_name": "Acme"},
    )
    assert specs
    assert all(s["recipient_type"] == "admin" for s in specs)
    assert {s["template_key"] for s in specs} == {"merchant_approved"}
    topics = {s["recipient_id"] for s in specs}
    assert any("ops" in t for t in topics)
    assert any("finance" in t for t in topics)


def test_merchant_suspended_routes_staff_high() -> None:
    specs = _specs_for_event(
        DomainEventType.MERCHANT_SUSPENDED,
        {"merchant_id": "m1", "company_name": "Acme"},
    )
    assert specs
    assert all(s["priority"] == "high" for s in specs)
    assert {s["template_key"] for s in specs} == {"merchant_suspended"}


def test_merchant_lifecycle_templates_exist() -> None:
    assert "merchant_approved" in TEMPLATES
    assert "merchant_suspended" in TEMPLATES
    assert DomainEventType.MERCHANT_SUSPENDED == "merchant.suspended"
