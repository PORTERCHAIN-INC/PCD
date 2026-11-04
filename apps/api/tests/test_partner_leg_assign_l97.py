"""L97: ops assign an order to a courier (contractor fleet) partner; the leg reaches the payable statement."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from porterchain_api.admin_engine.fleet_contracts_service import TORONTO, FleetContractsService
from porterchain_api.admin_engine.logistics_partners_service import LogisticsPartnersService
from porterchain_api.booking_models import Order
from porterchain_api.dispatch_engine.models import LogisticsPartner
from porterchain_api.domain.states import OrderState
from tests.test_collections_bl import _merchant
from tests.test_fleet_contracts import _ctx

S = LogisticsPartnersService()
FC = FleetContractsService()


def _partner(db, kind="courier", active=True):
    p = LogisticsPartner(name=f"L97 Fleet {uuid.uuid4().hex[:4]}", kind=kind, active=active,
                         rate_per_kg_cents=50, min_charge_cents=2000)
    db.add(p)
    db.flush()
    return p


def _order(db, state=OrderState.DISPATCH_READY.value, **kw):
    m = _merchant(db)
    o = Order(merchant_id=m.id, state=state, amount_cents=1000, currency="cad",
              order_number=f"L97-{uuid.uuid4().hex[:8].upper()}", tracking_number=f"TRK{uuid.uuid4().hex[:10]}",
              pickup={"formatted": "a", "postal_code": "M4E 1A1"}, dropoff={"formatted": "b", "postal_code": "L1N 2B2"},
              scheduled_at=datetime.now(UTC), **kw)
    db.add(o)
    db.flush()
    return o


def test_assign_creates_planned_courier_leg(db) -> None:
    p, o, ctx = _partner(db), _order(db), _ctx(db)
    leg = S.assign_partner_leg(db, ctx, o.id, p.id, note="east run")
    assert leg["mode"] == "courier" and leg["status"] == "planned"
    assert leg["partner_name"] == p.name and leg["order_number"] == o.order_number
    assert leg["est_cost_cents"] == 2000  # min charge
    assert leg["next"] == ["cancelled", "requested"]
    assert leg["history"][0]["note"] == "east run"


@pytest.mark.parametrize(
    ("kind", "active", "state", "err"),
    [
        ("warehouse", True, OrderState.DISPATCH_READY.value, "partner_not_courier"),
        ("courier", False, OrderState.DISPATCH_READY.value, "partner_inactive"),
        ("courier", True, OrderState.DELIVERED.value, "order_not_open"),
        ("courier", True, OrderState.CANCELLED.value, "order_not_open"),
    ],
)
def test_assign_rejects(db, kind, active, state, err) -> None:
    p, o, ctx = _partner(db, kind, active), _order(db, state), _ctx(db)
    with pytest.raises(ValueError, match=err):
        S.assign_partner_leg(db, ctx, o.id, p.id)


def test_assign_rejects_missing_and_duplicates(db) -> None:
    p, o, ctx = _partner(db), _order(db), _ctx(db)
    with pytest.raises(LookupError, match="order_not_found"):
        S.assign_partner_leg(db, ctx, "nope", p.id)
    with pytest.raises(LookupError, match="partner_not_found"):
        S.assign_partner_leg(db, ctx, o.id, "nope")
    S.assign_partner_leg(db, ctx, o.id, p.id)
    with pytest.raises(ValueError, match="order_already_with_partner"):
        S.assign_partner_leg(db, ctx, o.id, _partner(db).id)


def test_assign_rejects_order_with_own_driver(db) -> None:
    from porterchain_api.admin_models import Driver

    d = Driver(full_name="L97 D", email=f"l97_{uuid.uuid4().hex[:6]}@t.test")
    db.add(d)
    db.flush()
    p, o, ctx = _partner(db), _order(db, assigned_driver_id=d.id), _ctx(db)
    with pytest.raises(ValueError, match="order_has_driver"):
        S.assign_partner_leg(db, ctx, o.id, p.id)


def test_cancelled_leg_can_be_reassigned(db) -> None:
    p, o, ctx = _partner(db), _order(db), _ctx(db)
    leg = S.assign_partner_leg(db, ctx, o.id, p.id)
    S.set_leg_status(db, ctx, leg["id"], "cancelled")
    again = S.assign_partner_leg(db, ctx, o.id, p.id)
    assert again["id"] != leg["id"] and again["seq"] == leg["seq"] + 1


def test_delivered_leg_lands_on_payable_statement(db) -> None:
    p, o, ctx = _partner(db), _order(db), _ctx(db)
    today = datetime.now(TORONTO).date()
    FC.upsert(db, ctx, {"partner_id": p.id, "effective_from": (today.replace(day=1)).isoformat(),
                        "rate_basis": "stop", "rate_cents": 1100, "min_charge_cents": 1800})
    leg = S.assign_partner_leg(db, ctx, o.id, p.id)
    for st in ("requested", "accepted", "picked_up", "delivered"):
        out = S.set_leg_status(db, ctx, leg["id"], st)
    assert out["status"] == "delivered"
    st = FC.payable_statement(db, p.id, today, today)
    assert [j["order_number"] for j in st["jobs"]] == [o.order_number]
    assert st["jobs"][0]["units"] == 2 and st["total_cents"] == 2200
    assert st["unpriced"] == []
    assert isinstance(date.fromisoformat(st["jobs"][0]["completed_at"][:10]), date)


def test_l103_estimate_uses_contract_in_force(db) -> None:
    p, o, ctx = _partner(db), _order(db), _ctx(db)
    today = datetime.now(TORONTO).date()
    FC.upsert(db, ctx, {"partner_id": p.id, "effective_from": today.replace(day=1).isoformat(),
                        "rate_basis": "stop", "rate_cents": 1100, "min_charge_cents": 1800})
    leg = S.assign_partner_leg(db, ctx, o.id, p.id)
    assert leg["est_cost_cents"] == 2200  # 2 stops x $11, not the $20 rate-card minimum


def test_l103_statement_uses_toronto_days(db) -> None:
    from porterchain_api.dispatch_engine.models import OrderLeg

    p, o, ctx = _partner(db), _order(db), _ctx(db)
    FC.upsert(db, ctx, {"partner_id": p.id, "effective_from": "2026-10-01",
                        "rate_basis": "stop", "rate_cents": 1100, "min_charge_cents": 1800})
    leg = S.assign_partner_leg(db, ctx, o.id, p.id)
    row = db.get(OrderLeg, leg["id"])
    row.status = "delivered"
    row.meta = {**(row.meta or {}), "delivered_at": "2026-10-31T01:45:00+00:00"}  # 9:45 PM EDT Oct 30
    db.flush()
    st = FC.payable_statement(db, p.id, date(2026, 10, 30), date(2026, 10, 30))
    assert st["total_cents"] == 2200 and st["jobs"][0]["completed_at"].startswith("2026-10-30T21:45")
    assert FC.payable_statement(db, p.id, date(2026, 10, 31), date(2026, 10, 31))["jobs"] == []
