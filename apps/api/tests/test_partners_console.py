"""Partners console: per-partner workload stats (one grouped query) and audited bulk pause/activate."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.logistics_partners_service import LogisticsPartnersService
from porterchain_api.dispatch_engine.models import LogisticsPartner, OrderLeg
from tests.test_dispatch_phase2 import S, W, _ctx, _order

pytestmark = pytest.mark.usefixtures("quiet_pool")


def _partner(db: Session, **kw) -> LogisticsPartner:
    p = LogisticsPartner(name=f"QA Partner {uuid4().hex[:6]}", kind=kw.pop("kind", "3pl"), active=True, **kw)
    db.add(p)
    db.flush()
    return p


def test_stats_counts_open_delivered_and_cost(db: Session) -> None:
    p = _partner(db)
    o = _order(db, W, S)
    for status, cost in (("requested", 1000), ("picked_up", 500), ("delivered", 2500), ("cancelled", 9900)):
        db.add(OrderLeg(order_id=o.id, mode="3pl", partner_id=p.id, status=status, est_cost_cents=cost))
    db.flush()
    out = LogisticsPartnersService().stats(db)
    row = out["items"][p.id]
    assert row["open_legs"] == 2
    assert row["delivered_recent"] == 1
    assert row["cost_recent_cents"] == 4000  # cancelled legs never count as spend
    assert row["last_leg_at"]


def test_stats_partner_without_legs_absent(db: Session) -> None:
    p = _partner(db)
    assert p.id not in LogisticsPartnersService().stats(db)["items"]


def test_bulk_active_pauses_and_audits(db: Session) -> None:
    from porterchain_api.admin_models import AdminAuditLog

    ctx = _ctx(db)
    a, b = _partner(db), _partner(db)
    out = LogisticsPartnersService().bulk_active(db, ctx, [a.id, b.id, "missing"], False)
    assert out == {"updated": 2, "active": False}
    db.refresh(a)
    db.refresh(b)
    assert not a.active and not b.active
    n = db.query(AdminAuditLog).filter(AdminAuditLog.resource_id.in_([a.id, b.id])).count()
    assert n == 2


def test_bulk_active_requires_ids(db: Session) -> None:
    with pytest.raises(ValueError):
        LogisticsPartnersService().bulk_active(db, _ctx(db), [], True)
