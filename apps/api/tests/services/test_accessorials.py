"""Waiting-time and failed-delivery fees on merchant cycle invoices, with evidence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.merchant_ar_service import MerchantArService
from porterchain_api.billing_engine import accessorials as acc
from porterchain_api.billing_engine.models import InvoiceLine
from porterchain_api.booking_models import Invoice
from porterchain_pricing.contract_terms import DEFAULT_TERMS
from tests.services.test_merchant_ar_service import _admin, _merchant, _seed_delivered_order

T0 = datetime(2036, 3, 2, 15, 0, tzinfo=UTC)


def test_waiting_first_15_free_then_30_per_hour_in_15_min_blocks():
    o = SimpleNamespace(order_number="PC-1")
    ev = [("o:p0:a", "arrived", T0), ("o:p0:a", "picked_up", T0 + timedelta(minutes=32)),
          ("o:d0:a", "arrived", T0 + timedelta(minutes=60)), ("o:d0:a", "delivered", T0 + timedelta(minutes=70))]
    a = acc.waiting_for(o, ev, DEFAULT_TERMS)
    # pickup 32 min -> 17 over -> 2 blocks x $7.50 = $15; drop 10 min free
    assert a.amount_cents == 1500 and "pickup" in a.description and "32 min" in a.description
    assert a.evidence["source"] == "driver check-ins"
    assert acc.waiting_for(o, ev[2:], DEFAULT_TERMS) is None


def test_failed_fee_is_pct_of_stop_price_with_evidence():
    o = SimpleNamespace(order_number="PC-2", amount_cents=4000, state="FAILED",
                        compliance_metadata={"failure_reason": "No one home"})
    a = acc.failed_for(o, DEFAULT_TERMS, T0)
    assert a.amount_cents == 2000 and "No one home" in a.description and a.evidence["pct"] == 50


@pytest.mark.usefixtures("db")
def test_cycle_invoice_adds_waiting_line_and_stamps_order(db: Session):
    from porterchain_api.admin_models import Driver
    from porterchain_api.dispatch_engine.models import DispatchStopEvent

    driver = db.query(Driver).first()
    if driver is None:
        pytest.skip("no driver")
    actx = _admin(db)
    _m, merchant = _merchant(db)
    order = _seed_delivered_order(db, merchant)
    now = datetime.now(UTC)
    for key, ev, at in [(f"{order.id}:p0:x", "arrived", now - timedelta(minutes=50)),
                        (f"{order.id}:p0:x", "picked_up", now - timedelta(minutes=10))]:
        db.add(DispatchStopEvent(stop_key=key, order_id=order.id, driver_id=driver.id, event=ev, at=at))
    db.flush()
    out = MerchantArService().generate(db, actx, merchant_id=merchant.id,
                                       period_start=now - timedelta(days=1), period_end=now + timedelta(days=1))
    inv = db.get(Invoice, out["invoices"][0]["invoice_id"])
    lines = db.query(InvoiceLine).filter(InvoiceLine.invoice_id == inv.id).all()
    wait = [ln for ln in lines if ln.description.startswith("Waiting time")]
    assert wait and wait[0].amount_cents == 1500  # 40 min -> 25 over -> 2 blocks
    assert inv.amount_cents == sum(ln.amount_cents + ln.tax_cents for ln in lines)
    assert (order.compliance_metadata or {}).get("accessorials")[0]["code"] == "waiting"
