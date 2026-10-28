"""Minimal real parent rows for tests that touch FK-constrained columns.

dm2fkorphan0002 turned the CRM/quote/order soft links into real foreign keys,
so tests can no longer invent ``str(uuid4())`` ids for quote/order/company.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.booking_models import Order, Quote
from porterchain_api.crm_models import CrmCompany

_ADDR = {"formatted_address": "100 King St W, Toronto", "postal_code": "M5H 1A1"}


def make_quote(db: Session, **kw) -> Quote:
    now = datetime.now(UTC)
    row = Quote(
        amount_cents=kw.pop("amount_cents", 5000),
        currency="cad",
        state=kw.pop("state", "QUOTE"),
        vehicle_class="cargo_van",
        package_type="parcel",
        pickup=_ADDR,
        dropoff=_ADDR,
        pricing_breakdown={},
        scheduled_at=now,
        expires_at=now + timedelta(hours=24),
        **kw,
    )
    db.add(row)
    db.flush()
    return row


def make_order(db: Session, **kw) -> Order:
    row = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=kw.pop("state", "BOOKED"),
        payment_terms="IMMEDIATE",
        amount_cents=5000,
        currency="CAD",
        pickup=_ADDR,
        dropoff=_ADDR,
        scheduled_at=datetime.now(UTC),
        **kw,
    )
    db.add(row)
    db.flush()
    return row


def make_company(db: Session, **kw) -> CrmCompany:
    row = CrmCompany(legal_name=kw.pop("legal_name", f"FK Co {uuid.uuid4().hex[:8]}"), **kw)
    db.add(row)
    db.flush()
    return row
