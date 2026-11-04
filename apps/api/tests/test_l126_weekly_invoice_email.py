"""L126: weekly cycle invoice email states the week, lines, due date and working links."""

from datetime import datetime
from types import SimpleNamespace

from porterchain_api.admin_engine.merchant_ar_service import _cycle_email_fields
from porterchain_api.billing_engine.weekly_billing import due_at_for_issue, previous_week_bounds
from porterchain_api.notification_engine.templates import render_email


def _fields(monkeypatch):
    from porterchain_api import config

    monkeypatch.setattr(config.get_settings(), "merchant_portal_url", "http://portal.test/")
    start, end = previous_week_bounds(datetime(2026, 10, 31, 16, 0))  # Sat Oct 31 noon Toronto
    inv = SimpleNamespace(id="inv-1", currency="cad", due_at=due_at_for_issue(datetime(2026, 10, 31, 16, 0)))
    specs = [
        (SimpleNamespace(order_number="ORD-A"), SimpleNamespace(gross_cents=1831)),
        (SimpleNamespace(order_number="ORD-B"), SimpleNamespace(gross_cents=5537)),
    ]
    return _cycle_email_fields(inv, specs, [], start, end)


def test_fields_week_due_lines_links(monkeypatch):
    f = _fields(monkeypatch)
    assert f["period_label"] == "Mon Oct 19, 2026 to Sun Oct 25, 2026 (Toronto)"
    assert f["due_label"] == "Wed Nov 04, 2026 (Toronto)"
    assert f["lines_text"] == "- ORD-A: $18.31 CAD\n- ORD-B: $55.37 CAD"
    assert f["order_number"] == "2 deliveries"
    # 2026-11-03: merchants pay by Interac e-Transfer; the link opens the invoice, never card checkout.
    assert f["pay_url"] == "http://portal.test/billing/invoices/inv-1"
    assert f["receipt_url"] == "http://portal.test/billing/invoices/inv-1?pdf=1"


def test_email_renders_everything(monkeypatch):
    f = _fields(monkeypatch)
    subject, text, html = render_email(
        "merchant_invoice_ready",
        {"invoice_number": "INV-1", "merchant_name": "M", "amount_display": "$73.68 CAD", **f},
    )
    assert "INV-1" in subject
    for needle in ("- ORD-B: $55.37 CAD",
                   "- ORD-A: $18.31 CAD", "View invoice: http://portal.test/billing/invoices/inv-1",
                   "?pdf=1"):
        assert needle in text
    assert "?pay=card" not in html and "Pay now" not in html and "Billing week" in html and "ORD-B" in html


def test_terms_line_week_and_due_match_labels():
    from datetime import UTC

    from porterchain_api.billing_engine.weekly_billing import terms_line

    # Admin picker end-of-day end (23:30 Toronto) and a midnight end name the same last day.
    s, due = datetime(2026, 10, 25, 4, 0, tzinfo=UTC), due_at_for_issue(datetime(2026, 10, 31, 16, 0))
    for end in (datetime(2026, 11, 1, 3, 30, tzinfo=UTC), datetime(2026, 11, 1, 4, 0, tzinfo=UTC)):
        line = terms_line(s, end, due)
        assert "Week / Semaine: Oct 25 - Oct 31, 2026" in line
        assert "Due / Échéance: Wed Nov 04, 2026 (Toronto)" in line
