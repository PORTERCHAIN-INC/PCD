"""A suspended business is told in-app AND by a bilingual (EN/FR) email."""

from porterchain_api.notification_engine.event_router import _specs_for_event
from porterchain_api.notification_engine.templates import render_email, render_template
from porterchain_shared.events.catalog import DomainEventType

MID = "11111111-2222-3333-4444-555555555555"


def _specs(payload):
    return _specs_for_event(DomainEventType.MERCHANT_SUSPENDED, payload)


def test_suspension_notifies_merchant_in_app_and_email():
    specs = _specs({"merchant_id": MID, "company_name": "Maple Leaf", "merchant_email": "ap@mapleleaf.example"})
    mine = [(s["channel"], s["recipient_address"]) for s in specs if s["recipient_type"] == "merchant"]
    assert ("in_app", None) in mine
    assert ("email", "ap@mapleleaf.example") in mine
    # staff still get their in-app alerts
    assert sum(1 for s in specs if s["recipient_type"] == "admin") == 2


def test_suspension_without_email_still_in_app():
    specs = _specs({"merchant_id": MID, "company_name": "Maple Leaf"})
    chans = [s["channel"] for s in specs if s["recipient_type"] == "merchant"]
    assert chans == ["in_app"]


def test_suspension_email_is_bilingual():
    subject, body = render_template("merchant_account_suspended", {"company_name": "Maple Leaf"})[:2]
    assert "suspended" in subject and "suspendu" in subject
    assert "Hello Maple Leaf" in body and "Bonjour Maple Leaf" in body
    s2, text, html = render_email("merchant_account_suspended", {"company_name": "Maple Leaf"})
    assert "suspendu" in text and html
