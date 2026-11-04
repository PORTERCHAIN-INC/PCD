"""Fleet partner contracts: manual entry rules and the per-job payable statement."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest

from porterchain_api.admin_engine.fleet_contracts_service import FleetContractsService
from porterchain_api.booking_models import Order
from porterchain_api.dispatch_engine.models import LogisticsPartner, OrderLeg
from porterchain_api.domain.states import OrderState
from tests.test_collections_bl import _merchant

S = FleetContractsService()


def _ctx(db):
    from porterchain_api.admin_models import AdminUser

    u = AdminUser(email=f"fc_{uuid.uuid4().hex[:8]}@t.test", role="super_admin")
    db.add(u)
    db.flush()
    return SimpleNamespace(user=u)


def _partner(db):
    p = LogisticsPartner(name=f"Test Fleet {uuid.uuid4().hex[:4]}", kind="courier")
    db.add(p)
    db.flush()
    return p


def _leg(db, partner, *, when, status="delivered", **meta):
    m = _merchant(db)
    o = Order(merchant_id=m.id, state=OrderState.DELIVERED.value, amount_cents=1000, currency="cad",
              order_number=f"FC-{uuid.uuid4().hex[:8].upper()}", tracking_number=f"TRK{uuid.uuid4().hex[:10]}",
              pickup={"formatted": "a"}, dropoff={"formatted": "b"}, scheduled_at=when)
    db.add(o)
    db.flush()
    leg = OrderLeg(order_id=o.id, mode="3pl", partner_id=partner.id, status=status,
                   from_label="A", to_label="B", meta={"delivered_at": when.isoformat(), **meta})
    db.add(leg)
    db.flush()
    return leg


def _c(**kw):
    base = {"effective_from": "2026-10-01", "rate_basis": "stop", "rate_cents": 900, "min_charge_cents": 0}
    return {**base, **kw}


def test_validation(db) -> None:
    p, ctx = _partner(db), _ctx(db)
    with pytest.raises(ValueError, match="rate_basis"):
        S.upsert(db, ctx, _c(partner_id=p.id, rate_basis="km"))
    with pytest.raises(ValueError, match="effective_to"):
        S.upsert(db, ctx, _c(partner_id=p.id, effective_to="2026-09-01"))
    with pytest.raises(LookupError):
        S.upsert(db, ctx, _c(partner_id="nope"))
    S.upsert(db, ctx, _c(partner_id=p.id, effective_to="2026-10-31"))
    with pytest.raises(ValueError, match="overlap"):
        S.upsert(db, ctx, _c(partner_id=p.id, effective_from="2026-10-15"))
    S.upsert(db, ctx, _c(partner_id=p.id, effective_from="2026-11-01", rate_basis="route", rate_cents=15000))
    assert len(S.list(db, p.id)) == 2


@pytest.mark.parametrize(
    ("basis", "rate", "minc", "meta", "expect"),
    [
        ("stop", 900, 0, {}, 1800),            # default 2 stops
        ("stop", 900, 0, {"stops": 5}, 4500),
        ("parcel", 350, 0, {"parcels": 4}, 1400),
        ("parcel", 350, 2000, {"parcels": 4}, 2000),  # minimum applies
        ("route", 15000, 0, {}, 15000),
        ("hour", 4200, 0, {"hours": 2.5}, 10500),
    ],
)
def test_payable_per_basis(db, basis, rate, minc, meta, expect) -> None:
    p, ctx = _partner(db), _ctx(db)
    S.upsert(db, ctx, _c(partner_id=p.id, rate_basis=basis, rate_cents=rate, min_charge_cents=minc))
    _leg(db, p, when=datetime(2026, 10, 20, 15, tzinfo=UTC), **meta)
    st = S.payable_statement(db, p.id, date(2026, 10, 1), date(2026, 10, 31))
    assert [j["charge_cents"] for j in st["jobs"]] == [expect]
    assert st["total_cents"] == expect


def test_only_delivered_in_period_and_contract_by_date(db) -> None:
    p, ctx = _partner(db), _ctx(db)
    S.upsert(db, ctx, _c(partner_id=p.id, effective_to="2026-10-15", rate_basis="route", rate_cents=10000))
    S.upsert(db, ctx, _c(partner_id=p.id, effective_from="2026-10-16", rate_basis="route", rate_cents=12000))
    _leg(db, p, when=datetime(2026, 10, 10, 12, tzinfo=UTC))
    _leg(db, p, when=datetime(2026, 10, 20, 12, tzinfo=UTC))
    _leg(db, p, when=datetime(2026, 10, 21, 12, tzinfo=UTC), status="picked_up")  # not completed
    _leg(db, p, when=datetime(2026, 11, 2, 12, tzinfo=UTC))  # outside period
    _leg(db, p, when=datetime(2026, 9, 2, 12, tzinfo=UTC))   # no contract, outside period
    st = S.payable_statement(db, p.id, date(2026, 10, 1), date(2026, 10, 31))
    assert [j["charge_cents"] for j in st["jobs"]] == [10000, 12000]
    assert st["total_cents"] == 22000
    st2 = S.payable_statement(db, p.id, date(2026, 9, 1), date(2026, 9, 30))
    assert st2["jobs"] == [] and len(st2["unpriced"]) == 1
