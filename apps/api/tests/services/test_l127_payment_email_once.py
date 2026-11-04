"""L127: the payment-received email event fires once per new payment; resent webhooks don't repeat it."""

from __future__ import annotations

import pytest

from porterchain_api.billing_engine import merchant_invoice_checkout as mic
from porterchain_api.booking_models import DomainEvent

from tests.services.test_merchant_invoice_card import _session, mk  # noqa: F401

pytestmark = pytest.mark.usefixtures("db")


def _count(db, inv_id):
    return (
        db.query(DomainEvent)
        .filter(DomainEvent.event_type == "merchant.payment_received", DomainEvent.correlation_id == inv_id)
        .count()
    )


def test_payment_received_emitted_once_for_resent_webhook(db, mk):  # noqa: F811
    merchant, inv = mk()
    assert _count(db, inv.id) == 0  # issuing the invoice sends no payment email
    assert mic.complete_invoice_checkout(db, _session(inv, merchant, pi="pi_test_l127"))["status"] == "paid"
    assert _count(db, inv.id) == 1
    for _ in range(2):  # stripe events resend / return-page sync
        assert mic.complete_invoice_checkout(db, _session(inv, merchant, pi="pi_test_l127"))["status"] == "already_paid"
    assert _count(db, inv.id) == 1
