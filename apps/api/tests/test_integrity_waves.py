"""Integrity waves: invoice document, wallet ledger SoT, stop dual-write."""

from __future__ import annotations

from datetime import UTC, datetime

from porterchain_api.booking_engine.numbers import generate_invoice_number, generate_order_number, generate_tracking_number
from porterchain_api.billing_engine.credit_notes import issue_credit_note
from porterchain_api.billing_engine.invoice_document import attach_invoice_document
from porterchain_api.billing_engine.models import CreditNote, InvoiceLine
from porterchain_api.booking_engine.stop_sync import dual_write_stops
from porterchain_api.booking_models import Invoice, Order, Payment, Stop
from porterchain_api.domain.states import OrderState, PaymentStatus
from porterchain_api.driver_engine.wallet_ledger import record_transaction, wallet_balance_cents
from porterchain_api.driver_models import DriverWalletTransaction


def test_ensure_invoice_persists_status_and_line(db, monkeypatch):
    from porterchain_api.booking_engine.invoice_service import InvoiceService

    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.POD_COMPLETED.value,
        amount_cents=2500,
        currency="cad",
        pickup={"formatted": "A", "postal": "M5V 1A1"},
        dropoff={"formatted": "B", "postal": "M2N 1A1"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    payment = Payment(
        order_id=order.id,
        status=PaymentStatus.SUCCEEDED.value,
        amount_cents=2500,
        currency="cad",
    )
    db.add(payment)
    db.flush()

    invoice = InvoiceService().ensure_invoice(db, order)
    db.flush()
    assert invoice.status == "paid"
    assert invoice.paid_at is not None
    line = db.query(InvoiceLine).filter(InvoiceLine.invoice_id == invoice.id).one()
    assert line.amount_cents == 2500
    db.refresh(payment)
    assert payment.invoice_id == invoice.id


def test_wallet_balance_is_the_ledger_sum(db):
    from porterchain_api.admin_models import Driver

    driver = Driver(full_name="Pat", email="pat-wallet@example.com", phone="4160000000")
    db.add(driver)
    db.flush()
    record_transaction(db, driver_id=driver.id, tx_type="delivery", amount_cents=4000, balance_after_cents=4000)
    record_transaction(db, driver_id=driver.id, tx_type="payout", amount_cents=-1500, balance_after_cents=2500)
    assert wallet_balance_cents(db, driver.id) == 2500
    assert db.query(DriverWalletTransaction).filter(DriverWalletTransaction.driver_id == driver.id).count() == 2


def test_dual_write_stops_from_order_json(db):
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.BOOKED.value,
        amount_cents=1000,
        pickup={"formatted": "Pickup St", "city": "Toronto", "postal": "M5V 1A1", "lat": 43.64, "lng": -79.38},
        dropoff={"formatted": "Drop Ave", "city": "North York", "postal": "M2N 1A1"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    stops = dual_write_stops(db, order)
    assert [s.kind for s in stops] == ["pickup", "drop"]
    again = dual_write_stops(db, order)
    assert len(again) == 2
    assert db.query(Stop).filter(Stop.order_id == order.id).count() == 2


def test_dual_write_stops_includes_additional_mids(db):
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.BOOKED.value,
        amount_cents=1000,
        pickup={"formatted": "Pickup St", "city": "Toronto", "lat": 43.64, "lng": -79.38},
        dropoff={"formatted": "Drop Ave", "city": "North York"},
        compliance_metadata={
            "additional_stops": [
                {"formatted": "Mid Hub", "city": "Scarborough", "lat": 43.77, "lng": -79.23},
            ]
        },
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    stops = dual_write_stops(db, order)
    assert [s.kind for s in stops] == ["pickup", "stop", "drop"]
    assert [s.sequence for s in stops] == [0, 1, 2]


def test_credit_note_row_is_written(db):
    from porterchain_api.merchant_models import Merchant

    merchant = Merchant(company_name="CN Co", email="cn@example.com")
    db.add(merchant)
    db.flush()
    note = issue_credit_note(db, merchant_id=merchant.id, invoice_id=None, amount_cents=500, reason="damage")
    assert note.amount_cents == 500
    assert db.query(CreditNote).filter(CreditNote.merchant_id == merchant.id).one().reason == "damage"


def test_attach_invoice_document_is_idempotent(db):
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.INVOICED.value,
        amount_cents=800,
        pickup={"formatted": "A"},
        dropoff={"formatted": "B"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    invoice = Invoice(
        invoice_number=generate_invoice_number(),
        order_id=order.id,
        amount_cents=800,
        tax_cents=0,
        fees_cents=0,
        currency="cad",
    )
    db.add(invoice)
    db.flush()
    attach_invoice_document(db, invoice, order, None)
    attach_invoice_document(db, invoice, order, None)
    assert db.query(InvoiceLine).filter(InvoiceLine.invoice_id == invoice.id).count() == 1
