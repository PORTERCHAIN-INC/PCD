"""App Review demo orders: owner-only visibility; public and normal sandbox stay hidden."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from porterchain_api.auth.clerk import get_optional_clerk_user_id
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_engine.order_sla import publish_due_delivery_notices
from porterchain_api.booking_models import Customer, Order
from porterchain_api.db import get_db
from porterchain_api.main import create_app

ADDR = {"formatted": "100 Queen St W, Toronto", "postal": "M5H 2N2", "lat": 43.65, "lng": -79.38}


def _customer(db) -> Customer:
    c = Customer(clerk_user_id=f"user_{uuid.uuid4().hex}", email=f"{uuid.uuid4().hex}@example.test")
    db.add(c)
    db.flush()
    return c


def _order(db, customer: Customer, *, demo: bool, sandbox: bool = True) -> Order:
    o = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state="DRIVER_EN_ROUTE",
        customer_id=customer.id,
        payment_terms="IMMEDIATE",
        amount_cents=5240,
        currency="CAD",
        pickup=ADDR,
        dropoff=ADDR,
        scheduled_at=datetime(2020, 1, 1, tzinfo=UTC),
        is_sandbox=sandbox,
        compliance_metadata={"app_review_demo": True} if demo else {},
    )
    db.add(o)
    db.commit()
    return o


@pytest.fixture
def owner(db) -> Customer:
    return _customer(db)


@pytest.fixture
def call(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)

    def _get(path: str, viewer: str | None) -> int:
        app.dependency_overrides[get_optional_clerk_user_id] = lambda: viewer
        return client.get(path).status_code

    return _get


PATHS = ("/v1/orders/{tn}", "/v1/orders/{tn}/tracking", "/v1/orders/{tn}/experience")


def test_owner_sees_review_demo_order(db, owner, call) -> None:
    tn = _order(db, owner, demo=True).tracking_number
    assert [call(p.format(tn=tn), owner.clerk_user_id) for p in PATHS] == [200, 200, 200]


def test_anon_and_non_owner_still_404(db, owner, call) -> None:
    tn = _order(db, owner, demo=True).tracking_number
    other = _customer(db).clerk_user_id
    db.commit()
    for viewer in (None, other):
        assert [call(p.format(tn=tn), viewer) for p in PATHS] == [404, 404, 404]


def test_normal_sandbox_hidden_even_from_owner(db, owner, call) -> None:
    tn = _order(db, owner, demo=False).tracking_number
    assert [call(p.format(tn=tn), owner.clerk_user_id) for p in PATHS] == [404, 404, 404]


def test_review_demo_stays_out_of_delay_checks(db, owner) -> None:
    order = _order(db, owner, demo=True)
    publish_due_delivery_notices(db, limit=10_000)
    db.refresh(order)
    assert not (order.compliance_metadata or {}).get("sla_notices")
