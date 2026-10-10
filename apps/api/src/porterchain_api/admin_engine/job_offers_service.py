"""Job offers: offer an order to the best driver, expire after TTL, cascade.

- ``offer``: ranks drivers (dispatch_engine.recommend), offers to the best one
  not yet offered for this order. One pending offer per order at a time.
- ``sweep``: pending offers past ``expires_at`` → expired, then the next driver
  gets an offer. When no driver is left an open DRIVER_TIMEOUT exception is
  raised for the Exceptions queue. Idempotent; the worker runs it every pass.
- ``respond``: driver accepts (order → DRIVER_ASSIGNED → DRIVER_ACCEPTED,
  same audit/event path as an admin assign) or declines (cascade at once).
Nothing here sends mail/SMS; the existing ``order.driver_assigned`` event
drives the driver push exactly as a manual assign does.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.dispatch_engine.fleet_capacity import load_fleet
from porterchain_api.dispatch_engine.models import DispatchJobOffer

OPEN = "pending"


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(ts: datetime) -> datetime:
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def serialize(o: DispatchJobOffer, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or _now()
    left = max(int((_aware(o.expires_at) - now).total_seconds()), 0) if o.status == OPEN else 0
    return {
        "id": o.id,
        "order_id": o.order_id,
        "driver_id": o.driver_id,
        "status": o.status,
        "rank": o.rank,
        "offered_at": o.offered_at.isoformat() if o.offered_at else None,
        "expires_at": _aware(o.expires_at).isoformat(),
        "seconds_left": left,
        "responded_at": o.responded_at.isoformat() if o.responded_at else None,
        "meta": o.meta or {},
    }


class JobOffersService:
    def __init__(self, recommend_fn: Any = None) -> None:
        self._recommend = recommend_fn

    def _rank(self, db: Session, order_id: str) -> dict[str, Any]:
        if self._recommend is not None:
            return self._recommend(db, order_id)
        from porterchain_api.admin_engine.dispatch_board_service import recommend

        return recommend(db, order_id)

    def list_for_order(self, db: Session, order_id: str) -> list[dict[str, Any]]:
        rows = (
            db.query(DispatchJobOffer)
            .filter(DispatchJobOffer.order_id == order_id)
            .order_by(DispatchJobOffer.rank)
            .all()
        )
        return [serialize(r) for r in rows]

    def list_for_driver(self, db: Session, driver_id: str) -> list[dict[str, Any]]:
        self.sweep(db)
        rows = (
            db.query(DispatchJobOffer)
            .filter(DispatchJobOffer.driver_id == driver_id, DispatchJobOffer.status == OPEN)
            .order_by(DispatchJobOffer.expires_at)
            .all()
        )
        return [serialize(r) for r in rows]

    def offer(self, db: Session, order_id: str, *, actor_id: str | None, now: datetime | None = None) -> dict[str, Any]:
        from porterchain_api.booking_models import Order

        now = now or _now()
        order = db.get(Order, order_id)
        if order is None:
            raise LookupError("order_not_found")
        if order.state not in {"DISPATCH_READY", "DRIVER_REJECTED"}:
            raise ValueError("order_not_dispatchable")
        pending = (
            db.query(DispatchJobOffer)
            .filter(DispatchJobOffer.order_id == order_id, DispatchJobOffer.status == OPEN)
            .first()
        )
        if pending is not None:
            return {"offer": serialize(pending, now=now), "created": False}
        created = self._next(db, order_id, actor_id=actor_id, now=now)
        db.commit()
        return {"offer": serialize(created, now=now) if created else None, "created": created is not None}

    def _next(self, db: Session, order_id: str, *, actor_id: str | None, now: datetime) -> DispatchJobOffer | None:
        tried = {
            r[0]
            for r in db.query(DispatchJobOffer.driver_id).filter(DispatchJobOffer.order_id == order_id).all()
        }
        rec = self._rank(db, order_id)
        ttl = int(load_fleet(db)["offer_ttl_seconds"])
        for rank_no, drv in enumerate(rec.get("drivers") or [], start=1):
            if drv.get("blocked") or drv["driver_id"] in tried:
                continue
            row = DispatchJobOffer(
                order_id=order_id,
                driver_id=drv["driver_id"],
                status=OPEN,
                rank=len(tried) + 1,
                offered_at=now,
                expires_at=now + timedelta(seconds=ttl),
                offered_by=actor_id,
                meta={
                    "recommended_rank": rank_no,
                    "vehicle_class": drv.get("vehicle_class"),
                    "insertion_minutes": drv.get("insertion_minutes"),
                    "cost_cents": drv.get("cost_cents"),
                },
            )
            db.add(row)
            db.flush()
            return row
        self._raise_exhausted(db, order_id)
        return None

    @staticmethod
    def _raise_exhausted(db: Session, order_id: str) -> None:
        from porterchain_api.booking_models import OrderException

        exists = (
            db.query(OrderException)
            .filter(
                OrderException.order_id == order_id,
                OrderException.type == "DRIVER_TIMEOUT",
                OrderException.status == "open",
            )
            .first()
        )
        if exists is None:
            db.add(
                OrderException(
                    order_id=order_id,
                    type="DRIVER_TIMEOUT",
                    status="open",
                    reported_by_type="system",
                    evidence={"reason": "job_offers_exhausted"},
                )
            )

    def sweep(self, db: Session, *, now: datetime | None = None) -> dict[str, int]:
        now = now or _now()
        expired = (
            db.query(DispatchJobOffer)
            .filter(DispatchJobOffer.status == OPEN, DispatchJobOffer.expires_at <= now)
            .limit(100)
            .all()
        )
        passed = 0
        for o in expired:
            o.status = "expired"
            o.responded_at = now
            db.flush()
            if self._cascade_ok(db, o.order_id) and self._next(db, o.order_id, actor_id=o.offered_by, now=now):
                passed += 1
        if expired:
            db.commit()
        return {"expired": len(expired), "passed_on": passed}

    @staticmethod
    def _cascade_ok(db: Session, order_id: str) -> bool:
        from porterchain_api.booking_models import Order

        order = db.get(Order, order_id)
        return order is not None and order.state in {"DISPATCH_READY", "DRIVER_REJECTED"}

    def cancel_for_order(self, db: Session, order_id: str) -> int:
        n = 0
        for o in db.query(DispatchJobOffer).filter(DispatchJobOffer.order_id == order_id, DispatchJobOffer.status == OPEN):
            o.status = "cancelled"
            o.responded_at = _now()
            n += 1
        return n

    def respond(self, db: Session, offer_id: str, *, driver_id: str, accept: bool, now: datetime | None = None) -> dict[str, Any]:
        now = now or _now()
        offer = db.get(DispatchJobOffer, offer_id)
        if offer is None or offer.driver_id != driver_id:
            raise LookupError("offer_not_found")
        if offer.status != OPEN:
            raise ValueError(f"offer_{offer.status}")
        if _aware(offer.expires_at) <= now:
            offer.status = "expired"
            offer.responded_at = now
            db.commit()
            raise ValueError("offer_expired")
        offer.responded_at = now
        if not accept:
            offer.status = "declined"
            db.flush()
            if self._cascade_ok(db, offer.order_id):
                self._next(db, offer.order_id, actor_id=offer.offered_by, now=now)
            db.commit()
            return {"offer": serialize(offer, now=now)}
        self._assign(db, offer)
        offer.status = "accepted"
        self.cancel_for_order(db, offer.order_id)
        db.commit()
        return {"offer": serialize(offer, now=now)}

    @staticmethod
    def _assign(db: Session, offer: DispatchJobOffer) -> None:
        from porterchain_api.admin_engine.operations_service import (
            AdminOperationsService,
        )
        from porterchain_api.admin_engine.rbac import AdminContext
        from porterchain_api.admin_models import AdminUser
        from porterchain_api.booking_engine.order_transitions import (
            transition_order_state,
        )
        from porterchain_api.booking_models import Order
        from porterchain_api.domain.admin_states import AdminRole
        from porterchain_api.domain.states import OrderState

        admin = db.get(AdminUser, offer.offered_by) if offer.offered_by else None
        if admin is None:
            raise ValueError("offer_has_no_dispatcher")
        ctx = AdminContext(user=admin, role=AdminRole(admin.role) if admin.role in AdminRole._value2member_map_ else AdminRole.DISPATCHER)
        order = AdminOperationsService()._assign_driver_no_commit(db, ctx, offer.order_id, offer.driver_id)
        order = db.get(Order, order.id)
        transition_order_state(
            db,
            order,
            OrderState.DRIVER_ACCEPTED,
            event_type="order.accepted",
            actor_type="driver",
            actor_id=offer.driver_id,
            payload={"offer_id": offer.id},
        )
