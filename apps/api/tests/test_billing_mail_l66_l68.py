from types import SimpleNamespace
from porterchain_api.billing_engine.late_penalty import _billing_email
from porterchain_api.notification_engine.templates import TEMPLATES


def _m(contacts, email="merchant@x.example"):
    return SimpleNamespace(email=email, profile={"settings": {"billing_contacts": contacts}})


def test_billing_email_prefers_primary_ap():
    m = _m([{"email": "other@x.example"}, {"email": "ap@x.example", "is_primary": True}])
    assert _billing_email(m) == "ap@x.example"


def test_billing_email_falls_back_to_company():
    assert _billing_email(_m([])) == "merchant@x.example"


def test_reminder_subjects_say_reminder_and_overdue():
    assert "reminder" in TEMPLATES["merchant_invoice_reminder"]["subject"].lower()
    assert "overdue" in TEMPLATES["merchant_invoice_overdue"]["subject"].lower()
    assert "ready" not in TEMPLATES["merchant_invoice_overdue"]["subject"].lower()


def test_cycle_invoice_body_has_no_empty_order_line():
    from porterchain_api.notification_engine.templates import _fmt_safe

    out = _fmt_safe(TEMPLATES["merchant_invoice_ready"]["body"], {"invoice_number": "INV-1", "order_number": None, "amount_display": "$1"})
    assert "Order:" not in out and "Invoice: INV-1" in out and "None" not in out
