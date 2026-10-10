"""Exceptions queue: margin alerts, suggested fixes and one-click apply (admin-approved only).

Suggestions come from ``dispatch_engine.exception_fixes`` (rules). Nothing here runs on
its own: ``apply`` is only called from the admin endpoint, and every apply is stored in
``dispatch_fix_actions`` and the admin audit log.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

TZ = ZoneInfo("America/Toronto")
SLOT_HOUR = 9
DRIVER_KINDS = {"late", "at_risk", "unassigned", "margin"}
DRIVER_TYPES = {"DRIVER_TIMEOUT", "DRIVER_REJECT", "VEHICLE_BREAKDOWN"}
MAX_RECOMMEND = 10  # Valhalla-backed ranking is the slow part; the rest is rules


def next_slot(now: datetime) -> datetime:
    """Next weekday 09:00 Toronto (today's if it is still before 09:00 on a weekday)."""
    local = now.astimezone(TZ)
    day = local.date() if local.time() < time(SLOT_HOUR) else local.date() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return datetime.combine(day, time(SLOT_HOUR), TZ)


def _committed_routes(db: Session, now: datetime) -> list[Any]:
    from porterchain_api.dispatch_engine.models import DispatchPlan, DispatchRoute

    today = now.astimezone(TZ).date()
    return (
        db.query(DispatchRoute, DispatchPlan.id)
        .join(DispatchPlan, DispatchPlan.id == DispatchRoute.plan_id)
        .filter(DispatchPlan.status == "committed", DispatchPlan.service_date == today)
        .all()
    )


def margin_items(db: Session, *, now: datetime, floor_pct: float) -> list[dict[str, Any]]:
    """Orders on today's committed routes whose cost per stop eats the margin floor."""
    from porterchain_api.booking_models import Order
    from porterchain_api.dispatch_engine.margin import (
        below_floor,
        margin_pct,
        order_costs,
        order_price_cents,
    )

    rows = _committed_routes(db, now)
    costs = order_costs([{"stops": r.stops, "cost_cents": r.cost_cents} for r, _ in rows])
    if not costs:
        return []
    items = []
    for o in db.query(Order).filter(Order.id.in_(list(costs)), Order.is_sandbox.is_(False)).all():
        price, cost = order_price_cents(o), costs[o.id]
        if below_floor(price, cost, floor_pct):
            items.append({
                "id": f"margin:{o.id}", "kind": "margin", "type": "LOW_MARGIN", "severity": "medium",
                "order_id": o.id, "order_number": o.order_number, "state": o.state, "age_min": None,
                "status": "open", "price_cents": price, "cost_cents": cost,
                "margin_pct": margin_pct(price, cost), "floor_pct": floor_pct,
            })
    return items


def rescue_service() -> Any:
    """Breakdown rescue wired to Valhalla, live GPS, the planner's vehicles and the delay email."""
    from porterchain_shared.events.catalog import DomainEventType

    from porterchain_api.admin_engine import fleet_plan_service as fps
    from porterchain_api.booking_engine._core import emit_event
    from porterchain_api.dispatch_engine.fleet_capacity import load_fleet
    from porterchain_api.dispatch_engine.rescue import RescueService

    planner = fps.FleetPlanService()

    def email_delay(db: Session, ctx: Any, order: Any, message: str) -> None:
        emit_event(db, event_type=DomainEventType.ORDER_DELAYED.value, aggregate_type="order", aggregate_id=order.id,
                   actor_type="admin", actor_id=str(ctx.user.id), payload={"message": message, "reason": "vehicle_rescue"})

    return RescueService(matrix_fn=fps._valhalla, position_fn=fps._position, email_delay=email_delay,
                         vehicles_fn=lambda db, only: planner._vehicles(db, load_fleet(db), only=only))


class ExceptionFixesService:
    def __init__(self, recommend_fn: Callable[[Session, str], dict[str, Any]] | None = None) -> None:
        self.recommend_fn = recommend_fn

    def _recommend(self, db: Session, order_id: str) -> dict[str, Any] | None:
        from porterchain_api.admin_engine.dispatch_board_service import recommend

        try:
            rec = (self.recommend_fn or recommend)(db, order_id)
        except (LookupError, ValueError):
            return None
        best = rec.get("best_driver_id")
        return next((d for d in rec.get("drivers", []) if d["driver_id"] == best), None)

    def annotate(self, db: Session, items: list[dict[str, Any]], *, now: datetime) -> list[dict[str, Any]]:
        """Attach ranked ``fixes`` to each queue item (in place)."""
        from porterchain_api.dispatch_engine.exception_fixes import suggest

        plan_of: dict[str, str] = {}
        for route, plan_id in _committed_routes(db, now):
            for s in route.stops or []:
                plan_of.setdefault(s["order_id"], plan_id)
        slot = next_slot(now)
        budget = MAX_RECOMMEND
        for it in items:
            best = None
            if budget and (it["kind"] in DRIVER_KINDS or it["type"] in DRIVER_TYPES):
                budget -= 1
                best = self._recommend(db, it["order_id"])
            it["fixes"] = suggest(it, plan_id=plan_of.get(it["order_id"]), best_driver=best, next_slot=slot)
        return items

    def apply(self, db: Session, settings: Any, ctx: Any, *, item_id: str, order_id: str, action: str,
              params: dict[str, Any]) -> dict[str, Any]:
        from porterchain_api.admin_engine.logistics_partners_service import _audit
        from porterchain_api.booking_models import Order
        from porterchain_api.dispatch_engine.exception_fixes import ACTIONS
        from porterchain_api.dispatch_engine.models import DispatchFixAction

        if action not in ACTIONS:
            raise ValueError("fix_action_invalid")
        order = db.get(Order, order_id)
        if order is None:
            raise LookupError("order_not_found")
        result = getattr(self, f"_{action}")(db, settings, ctx, order, params)
        db.add(DispatchFixAction(item_id=item_id[:96], order_id=order.id, action=action, params=params,
                                 result=result, approved_by=str(ctx.user.id)))
        _audit(db, ctx, f"dispatch.fix.{action}", order.id, {"item_id": item_id, "params": params, "result": result})
        db.commit()
        return {"ok": True, "action": action, "result": result}

    # ---- actions
    @staticmethod
    def _reroute(db: Session, settings: Any, ctx: Any, order: Any, params: dict[str, Any]) -> dict[str, Any]:
        from porterchain_api.admin_engine.fleet_plan_service import FleetPlanService

        plan_id = str(params.get("plan_id") or "")
        if not plan_id:
            raise ValueError("plan_id_required")
        draft = FleetPlanService().replan(db, plan_id, actor=str(ctx.user.id))
        return {"draft_plan_id": draft["id"], "note": "re-plan drafted — commit it on Plan"}

    @staticmethod
    def _rescue(db: Session, settings: Any, ctx: Any, order: Any, params: dict[str, Any]) -> dict[str, Any]:
        broken = str(params.get("driver_id") or order.assigned_driver_id or "")
        if not broken:
            raise ValueError("driver_id_required")
        return rescue_service().rescue(db, ctx, broken_driver_id=broken,
                                       rescue_driver_id=params.get("rescue_driver_id") or None)

    @staticmethod
    def _reassign(db: Session, settings: Any, ctx: Any, order: Any, params: dict[str, Any]) -> dict[str, Any]:
        from porterchain_api.admin_engine.operations_service import (
            AdminOperationsService,
        )

        driver_id = str(params.get("driver_id") or "")
        if not driver_id:
            raise ValueError("driver_id_required")
        AdminOperationsService().assign_driver(db, settings, ctx, order.id, driver_id)
        return {"driver_id": driver_id}

    @staticmethod
    def _reschedule(db: Session, settings: Any, ctx: Any, order: Any, params: dict[str, Any]) -> dict[str, Any]:
        from porterchain_api.booking_engine.order_transitions import (
            transition_order_state,
        )
        from porterchain_api.domain.states import OrderState

        try:
            when = datetime.fromisoformat(str(params.get("scheduled_at")))
        except ValueError as exc:
            raise ValueError("scheduled_at_invalid") from exc
        order.scheduled_at = when if when.tzinfo else when.replace(tzinfo=UTC)
        if order.state == "FAILED":
            transition_order_state(db, order, OrderState.DISPATCH_READY, event_type="order.reattempt_scheduled",
                                   actor_type="admin", actor_id=str(ctx.user.id), payload={"source": "dispatch_fix"})
        return {"scheduled_at": order.scheduled_at.isoformat(), "state": order.state}

    @staticmethod
    def _contact(db: Session, settings: Any, ctx: Any, order: Any, params: dict[str, Any]) -> dict[str, Any]:
        from porterchain_shared.events.catalog import DomainEventType

        from porterchain_api.booking_engine._core import emit_event

        message = str(params.get("message") or "Your delivery is running late. We will update your ETA shortly.")
        emit_event(db, event_type=DomainEventType.ORDER_DELAYED.value, aggregate_type="order", aggregate_id=order.id,
                   actor_type="admin", actor_id=str(ctx.user.id), payload={"message": message[:300]})
        return {"notified": "order.delayed"}
