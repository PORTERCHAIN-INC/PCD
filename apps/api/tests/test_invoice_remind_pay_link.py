"""Invoice reminder includes portal Pay now link."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from porterchain_api.merchant_engine.invoice_reminder import remind_invoice


def test_remind_invoice_includes_pay_url():
    db = MagicMock()
    merchant = SimpleNamespace(
        id="m1",
        email="ap@test.local",
        company_name="Test Co",
        phone=None,
        profile={"settings": {"billing_contacts": [{"email": "ap@test.local", "is_primary": True}]}},
    )
    invoice = SimpleNamespace(
        id="inv-99",
        invoice_number="INV-99",
        order_id="o1",
        amount_cents=5000,
        currency="cad",
        last_reminded_at=None,
    )
    order = SimpleNamespace(id="o1", merchant_id="m1")
    db.query.return_value.filter.return_value.first.return_value = order

    payload_base = {
        "invoice_id": "inv-99",
        "invoice_number": "INV-99",
        "amount_cents": 5000,
        "amount_display": "$50.00 CAD",
        "receipt_url": None,
    }

    with (
        patch(
            "porterchain_api.merchant_engine.invoice_reminder.InvoiceService"
        ) as inv_svc,
        patch("porterchain_api.merchant_engine.invoice_reminder.emit_event"),
        patch(
            "porterchain_api.merchant_engine.invoice_reminder.get_settings",
            create=True,
        ),
        patch(
            "porterchain_api.config.get_settings",
            return_value=SimpleNamespace(merchant_portal_url="http://localhost:3001"),
        ),
        patch(
            "porterchain_api.notification_engine.event_router.handle_domain_event",
            return_value=None,
        ),
    ):
        inv_svc.return_value._invoice_event_payload.return_value = dict(payload_base)
        result = remind_invoice(db, invoice, merchant, actor_type="merchant", actor_id="u1")

    assert result["pay_url"] == "http://localhost:3001/billing/invoices/inv-99"
    assert result["email"] == "ap@test.local"
    # Audit payload captured pay_url
    audit = db.add.call_args[0][0]
    assert audit.payload["pay_url"] == result["pay_url"]
