"""L41: ready orders are offered to the best driver automatically, once."""
from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.job_offers_service import JobOffersService
from porterchain_api.dispatch_engine.models import DispatchJobOffer
from tests.test_dispatch_brain import _driver, _order


def test_auto_offer_ready_offers_once(db: Session) -> None:
    o = _order(is_sandbox=False)
    db.add(o)
    d = _driver(db)
    db.commit()
    svc = JobOffersService(recommend_fn=lambda _db, _oid: {"drivers": [{"driver_id": d.id, "blocked": None}]})
    assert svc.auto_offer_ready(db) >= 1
    rows = db.query(DispatchJobOffer).filter(DispatchJobOffer.order_id == o.id).all()
    assert len(rows) == 1 and rows[0].driver_id == d.id and rows[0].offered_by == "system:auto_dispatch"
    svc.auto_offer_ready(db)
    assert db.query(DispatchJobOffer).filter(DispatchJobOffer.order_id == o.id).count() == 1
