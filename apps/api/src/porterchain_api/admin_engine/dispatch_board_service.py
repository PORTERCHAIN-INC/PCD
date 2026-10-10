"""Dispatch board read models: one Exceptions queue and the speed metrics bar."""

from __future__ import annotations

import statistics
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

STATE_KINDS = {
    "FAILED": ("failed", "high"),
    "DAMAGED": ("damaged", "critical"),
    "LOST": ("lost", "critical"),
    "RETURN_TO_SENDER": ("return", "medium"),
    "CLAIM_OPEN": ("claim", "medium"),
}
EXCEPTION_SEVERITY = {
    "PARCEL_LOST": "critical",
    "PARCEL_DAMAGED": "critical",
    "VEHICLE_BREAKDOWN": "critical",
    "DRIVER_TIMEOUT": "high",
    "DRIVER_REJECT": "high",
    "FAILED_DELIVERY": "high",
    "CUSTOMER_UNAVAILABLE": "high",
    "WRONG_ADDRESS": "high",
}
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
UNASSIGNED_ALERT_MIN = 15


def _aware(ts: datetime | None) -> datetime | None:
    if ts is None:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def _age_min(ts: datetime | None, now: datetime) -> int | None:
    t = _aware(ts)
    return None if t is None else max(int((now - t).total_seconds() // 60), 0)


def recommend(db: Session, order_id: str, **kw: Any) -> dict[str, Any]:
    """Recommendation with the admin verification gate applied."""
    from porterchain_api.admin_engine.control_tower.scoring import (
        driver_verification_gap,
    )
    from porterchain_api.dispatch_engine.recommend import recommend_for_order

    return recommend_for_order(db, order_id, gap_fn=driver_verification_gap, **kw)


class DispatchBoardService:
    # ---------- Exceptions queue ----------
    def exceptions_queue(
        self,
        db: Session,
        *,
        now: datetime | None = None,
        etas_fn: Callable[[Session], list[dict[str, Any]]] | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.booking_models import Order, OrderException

        now = now or datetime.now(UTC)
        items: list[dict[str, Any]] = []
        seen_orders: set[str] = set()

        open_exc = (
            db.query(OrderException, Order)
            .join(Order, Order.id == OrderException.order_id)
            .filter(OrderException.status.in_(("open", "acknowledged")), Order.is_sandbox.is_(False))
            .order_by(OrderException.created_at)
            .limit(200)
            .all()
        )
        for exc, order in open_exc:
            seen_orders.add(order.id)
            items.append(
                {
                    "id": f"exc:{exc.id}",
                    "kind": "exception",
                    "type": exc.type,
                    "severity": EXCEPTION_SEVERITY.get(exc.type, "medium"),
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "state": order.state,
                    "age_min": _age_min(exc.created_at, now),
                    "status": exc.status,
                    "exception_id": exc.id,
                }
            )

        state_rows = (
            db.query(Order)
            .filter(Order.is_sandbox.is_(False), Order.state.in_(tuple(STATE_KINDS)))
            .order_by(Order.updated_at)
            .limit(200)
            .all()
        )
        for order in state_rows:
            if order.id in seen_orders:
                continue
            kind, sev = STATE_KINDS[order.state]
            seen_orders.add(order.id)
            items.append(
                {
                    "id": f"state:{order.id}",
                    "kind": kind,
                    "type": order.state,
                    "severity": sev,
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "state": order.state,
                    "age_min": _age_min(order.updated_at, now),
                    "status": "open",
                }
            )

        cutoff = now - timedelta(minutes=UNASSIGNED_ALERT_MIN)
        waiting = (
            db.query(Order)
            .filter(
                Order.is_sandbox.is_(False),
                Order.state == "DISPATCH_READY",
                Order.created_at <= cutoff,
            )
            .order_by(Order.created_at)
            .limit(100)
            .all()
        )
        for order in waiting:
            if order.id in seen_orders:
                continue
            items.append(
                {
                    "id": f"wait:{order.id}",
                    "kind": "unassigned",
                    "type": "UNASSIGNED",
                    "severity": "medium",
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "state": order.state,
                    "age_min": _age_min(order.created_at, now),
                    "status": "open",
                }
            )

        eta_status = "ok"
        try:
            if etas_fn is not None:
                etas = etas_fn(db)
            else:
                from porterchain_api.dispatch_engine.eta_risk import live_etas

                etas = live_etas(db, now=now)
        except Exception:  # noqa: BLE001 — Valhalla/Redis down must not hide the queue
            etas, eta_status = [], "unavailable"
        for row in etas:
            if row["status"] not in {"late", "at_risk"} or row["order_id"] in seen_orders:
                continue
            items.append(
                {
                    "id": f"eta:{row['order_id']}",
                    "kind": row["status"],
                    "type": "LATE" if row["status"] == "late" else "AT_RISK",
                    "severity": "critical" if row["status"] == "late" else "high",
                    "order_id": row["order_id"],
                    "order_number": row["order_number"],
                    "state": row["state"],
                    "age_min": None,
                    "status": "open",
                    "eta": row["eta"],
                    "promise": row["promise"],
                }
            )

        items.sort(key=lambda i: (SEVERITY_ORDER.get(i["severity"], 9), -(i["age_min"] or 0)))
        counts: dict[str, int] = defaultdict(int)
        for i in items:
            counts[i["severity"]] += 1
        return {"items": items, "counts": dict(counts), "total": len(items), "eta": eta_status}

    # ---------- Metrics ----------
    def metrics(self, db: Session, *, days: int = 7, now: datetime | None = None) -> dict[str, Any]:
        from porterchain_api.admin_models import SystemConfig, Vehicle
        from porterchain_api.booking_models import Order, OrderEvent
        from porterchain_api.dispatch_engine.fleet_capacity import (
            canonical_class,
            fill_ratio,
            load_fleet,
            order_load,
            vehicle_by_id,
        )
        from porterchain_api.driver_models import DriverShift

        now = now or datetime.now(UTC)
        days = max(1, min(int(days), 90))
        since = now - timedelta(days=days)
        fleet = load_fleet(db)

        created = (
            db.query(Order)
            .filter(Order.is_sandbox.is_(False), Order.created_at >= since)
            .limit(5000)
            .all()
        )
        ids = [o.id for o in created]
        first_assign: dict[str, datetime] = {}
        if ids:
            for oid, at in (
                db.query(OrderEvent.order_id, OrderEvent.occurred_at)
                .filter(OrderEvent.order_id.in_(ids), OrderEvent.to_state == "DRIVER_ASSIGNED")
                .order_by(OrderEvent.occurred_at)
                .all()
            ):
                first_assign.setdefault(oid, at)
        waits = [
            (_aware(first_assign[o.id]) - _aware(o.created_at)).total_seconds() / 60.0
            for o in created
            if o.id in first_assign and o.created_at
        ]

        delivered_ev = (
            db.query(OrderEvent.order_id, OrderEvent.occurred_at)
            .filter(OrderEvent.to_state == "DELIVERED", OrderEvent.occurred_at >= since)
            .all()
        )
        delivered_at = {oid: at for oid, at in delivered_ev}
        delivered = (
            db.query(Order).filter(Order.id.in_(list(delivered_at)), Order.is_sandbox.is_(False)).all()
            if delivered_at
            else []
        )
        n = len(delivered)
        with_promise = [o for o in delivered if o.sla_deadline_at]
        on_time = [o for o in with_promise if _aware(delivered_at[o.id]) <= _aware(o.sla_deadline_at)]
        failed_ids = (
            {
                r[0]
                for r in db.query(OrderEvent.order_id)
                .filter(OrderEvent.order_id.in_([o.id for o in delivered]), OrderEvent.to_state == "FAILED")
                .all()
            }
            if delivered
            else set()
        )

        shifts = db.query(DriverShift).filter(DriverShift.started_at >= since).all()
        paid_min = 0.0
        for s in shifts:
            end = _aware(s.ended_at) or now
            paid_min += max((end - _aware(s.started_at)).total_seconds() / 60.0 - (s.break_minutes or 0), 0)
        hours = paid_min / 60.0

        cost_per_stop = None
        if n and paid_min:
            plan_row = db.get(SystemConfig, "driver_pay_plan")
            try:
                from porterchain_pricing.driver_pay import compute_driver_pay

                total = compute_driver_pay(
                    plan_row.value if plan_row else None, paid_minutes=paid_min, stops=n, pickups=n
                ).total_cents
            except (ImportError, ValueError):
                total = int(round(hours * fleet["hourly_cost_cents"]))
            cost_per_stop = int(round(total / n))

        fills = []
        for o in delivered:
            if not o.assigned_driver_id:
                continue
            v = (
                db.query(Vehicle)
                .filter(Vehicle.driver_id == o.assigned_driver_id, Vehicle.is_active.is_(True))
                .first()
            )
            spec = vehicle_by_id(fleet, canonical_class(v.vehicle_class)) if v else None
            if spec:
                fills.append(fill_ratio(order_load(o), spec))

        def pct(a: int, b: int) -> float | None:
            return round(100.0 * a / b, 1) if b else None

        return {
            "window_days": days,
            "orders_created": len(created),
            "delivered": n,
            "order_to_dispatch_min": round(statistics.median(waits), 1) if waits else None,
            "on_time_pct": pct(len(on_time), len(with_promise)),
            "first_attempt_pct": pct(n - len(failed_ids), n),
            "cost_per_stop_cents": cost_per_stop,
            "fill_pct": round(100 * statistics.mean(fills), 1) if fills else None,
            "stops_per_driver_hour": round(n / hours, 2) if hours else None,
            "driver_hours": round(hours, 1),
            "hourly_cost_cents": fleet["hourly_cost_cents"],
        }

    # ---------- Vehicle capacity table (settings; writes live in fleet_capacity_service) ----------
    def fleet_get(self, db: Session) -> dict[str, Any]:
        from porterchain_api.admin_engine.fleet_capacity_service import fleet_get

        return fleet_get(db)

    def fleet_put(self, db: Session, ctx: Any, raw: dict[str, Any]) -> dict[str, Any]:
        from porterchain_api.admin_engine.fleet_capacity_service import fleet_put

        return fleet_put(db, ctx, raw)

    def live_etas(self, db: Session) -> list[dict[str, Any]]:
        from porterchain_api.dispatch_engine.eta_risk import live_etas

        return live_etas(db)
