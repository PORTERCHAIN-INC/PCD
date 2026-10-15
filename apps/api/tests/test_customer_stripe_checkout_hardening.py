"""Customer Stripe Checkout hardening (2026-10-15): customers pay by card, merchants by Interac."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.stripe_webhook_service import StripeWebhookService
from porterchain_api.booking_models import Invoice, Order, Payment
from porterchain_api.config import Settings
from tests.test_stripe_webhook_idempotency import _checkout_completed_event, _setup_quote


def _evt(quote, customer, payment, **obj):
    e = _checkout_completed_event(
        event_id=f"evt_{uuid4().hex}", quote_id=quote.id, customer_id=customer.id, payment_id=payment.id
    )
    e["data"]["object"].update(obj)
    return e


def test_second_delivery_after_poll_is_ok_not_500(db: Session, settings: Settings) -> None:
    """Poll confirms first; the later webhook (new event id) must not raise."""
    quote, customer, payment = _setup_quote(db, settings)
    svc = StripeWebhookService()
    assert svc.handle(db, settings, _evt(quote, customer, payment, payment_status="paid")) == {"status": "ok"}
    assert svc.handle(db, settings, _evt(quote, customer, payment, payment_status="paid")) == {"status": "ok"}
    assert db.query(Order).filter(Order.quote_id == quote.id).count() == 1


def test_unpaid_completed_session_does_not_book(db: Session, settings: Settings) -> None:
    quote, customer, payment = _setup_quote(db, settings)
    svc = StripeWebhookService()
    svc.handle(db, settings, _evt(quote, customer, payment, payment_status="unpaid"))
    assert db.query(Order).filter(Order.quote_id == quote.id).count() == 0
    e = _evt(quote, customer, payment, payment_status="paid")
    e["type"] = "checkout.session.async_payment_succeeded"
    assert svc.handle(db, settings, e) == {"status": "ok"}
    assert db.query(Order).filter(Order.quote_id == quote.id).count() == 1


def test_zero_stripe_tax_keeps_our_hst_split(db: Session, settings: Settings) -> None:
    """Stripe Tax is off (amount_tax=0); the invoice must still carry the HST in our price."""
    quote, customer, payment = _setup_quote(db, settings)
    StripeWebhookService().handle(
        db, settings, _evt(quote, customer, payment, payment_status="paid", total_details={"amount_tax": 0})
    )
    order = db.query(Order).filter(Order.quote_id == quote.id).one()
    inv = db.query(Invoice).filter(Invoice.order_id == order.id).one()
    assert inv.tax_cents > 0
    assert inv.tax_cents < inv.amount_cents


def test_reconcile_confirms_paid_and_expires_abandoned(db: Session, settings: Settings, monkeypatch) -> None:
    import porterchain_api.services.stripe_service as ss

    paid_q, paid_c, paid_p = _setup_quote(db, settings)
    exp_q, exp_c, exp_p = _setup_quote(db, settings)
    old = datetime.now(UTC) - timedelta(minutes=30)
    for p, sid in ((paid_p, "cs_test_paid"), (exp_p, "cs_test_expired")):
        p.stripe_checkout_session_id = f"{sid}_{uuid4().hex[:6]}"
        p.status = "PROCESSING"
        p.created_at = old
    db.commit()
    sessions = {
        paid_p.stripe_checkout_session_id: {
            "id": paid_p.stripe_checkout_session_id, "status": "complete", "payment_status": "paid",
            "payment_intent": "pi_test_rec", "amount_total": 4500, "currency": "cad",
            "metadata": {"quote_id": paid_q.id, "customer_id": paid_c.id, "payment_id": paid_p.id},
        },
        exp_p.stripe_checkout_session_id: {
            "id": exp_p.stripe_checkout_session_id, "status": "expired", "payment_status": "unpaid",
            "metadata": {"quote_id": exp_q.id, "customer_id": exp_c.id, "payment_id": exp_p.id},
        },
    }
    monkeypatch.setattr(ss, "retrieve_checkout_session", lambda _s, sid: sessions[sid])
    s2 = settings.model_copy(update={"stripe_secret": "sk_test_dummy"})
    out = StripeWebhookService().reconcile_open_checkouts(db, s2)
    assert out["confirmed"] >= 1 and out["expired"] >= 1
    assert db.query(Order).filter(Order.quote_id == paid_q.id).count() == 1
    assert db.query(Order).filter(Order.quote_id == exp_q.id).count() == 0
    db.refresh(exp_p)
    assert exp_p.status == "FAILED"
    # Re-running is a no-op for the confirmed one.
    StripeWebhookService().reconcile_open_checkouts(db, s2)
    assert db.query(Order).filter(Order.quote_id == paid_q.id).count() == 1
