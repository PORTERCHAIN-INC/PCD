"""Fleet plan: multi-vehicle routing for the day, re-plan, commit, explain.

OR-Tools solves every plan. When ``dispatch_cuopt_enabled`` is on, self-hosted cuOpt
solves the same problem; both are scored by ``vrp.evaluate`` and the better plan wins
(OR-Tools on any cuOpt error). Plans are drafts until an admin commits them.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from porterchain_api.dispatch_engine import vrp
from porterchain_api.dispatch_engine.stop_shapes import StopSpec, order_stops

TZ = ZoneInfo("America/Toronto")
PICKED = {"PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"}
DONE = {"DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED", "CANCELLED", "RETURN_TO_SENDER"}
POOL = ("BOOKED", "DISPATCH_READY", "DRIVER_REJECTED", "FAILED")
MAX_ORDERS = 300
Matrix = Callable[[list[tuple[float, float]]], list[list[int]] | None]


def _now() -> datetime:
    return datetime.now(UTC)


def _valhalla(points: list[tuple[float, float]]) -> list[list[int]] | None:
    from porterchain_api.dispatch_engine.day_plan import drive_seconds

    try:
        matrix, _ = drive_seconds(points, vehicle_class="van")
    except Exception:  # noqa: BLE001 — router down → plan refuses rather than guess
        return None
    return matrix


def _position(driver_id: str) -> tuple[float, float] | None:
    try:
        from porterchain_api.platform.last_known import read_last_known

        lk = read_last_known(driver_id)
    except Exception:  # noqa: BLE001
        return None
    return (lk.lat, lk.lng) if lk else None


class FleetPlanService:
    def __init__(self, *, matrix_fn: Matrix | None = None, position_fn: Callable[[str], Any] | None = None,
                 cuopt_fn: Callable[[vrp.Problem], dict | None] | None = None) -> None:
        self.matrix_fn = matrix_fn or _valhalla
        self.position_fn = position_fn or _position
        self.cuopt_fn = cuopt_fn

    # ------------------------------------------------------------ inputs
    def _orders(self, db: Session, order_ids: list[str] | None) -> list[Any]:
        from porterchain_api.booking_models import Order

        q = db.query(Order).filter(Order.is_sandbox.is_(False))
        if order_ids:
            q = q.filter(Order.id.in_(order_ids))
        else:
            end = datetime.combine(datetime.now(TZ).date() + timedelta(days=1), time.min, TZ)
            q = q.filter(Order.assigned_driver_id.is_(None), Order.state.in_(POOL), Order.scheduled_at < end)
        return q.order_by(Order.scheduled_at).limit(MAX_ORDERS).all()

    def _hub_override(self, db: Session, order: Any) -> Any:
        """First planned leg ends at a warehouse/partner → the van's drop is that hub."""
        from porterchain_api.dispatch_engine.models import OrderLeg

        leg = (
            db.query(OrderLeg)
            .filter(OrderLeg.order_id == order.id, OrderLeg.status.in_(("planned", "requested", "accepted")))
            .order_by(OrderLeg.seq)
            .first()
        )
        meta = (leg.meta or {}) if leg is not None else {}
        if leg is None or leg.mode != "local" or meta.get("to_lat") is None:
            return order
        hub = {"lat": meta["to_lat"], "lng": meta["to_lng"], "formatted": leg.to_label,
               "kind": meta.get("stop_kind", "hub"), "partner_id": leg.partner_id}

        class _View:  # read-only view; never mutates the ORM row
            pass

        v = _View()
        for attr in ("id", "pickup", "order_type", "state", "compliance_metadata"):
            setattr(v, attr, getattr(order, attr))
        v.dropoff = hub  # type: ignore[attr-defined]
        return v

    def _stops(self, db: Session, orders: list[Any]) -> tuple[list[StopSpec], list[tuple[str, str]], list[dict], dict]:
        from porterchain_api.dispatch_engine.fleet_capacity import order_load

        stops: list[StopSpec] = []
        pairs: list[tuple[str, str]] = []
        skipped: list[dict] = []
        shapes: dict[str, int] = {}
        for o in orders:
            load = order_load(o)
            os_ = order_stops(self._hub_override(db, o), boxes=load.boxes, kg=load.kg)
            shapes[os_.shape] = shapes.get(os_.shape, 0) + 1
            if os_.skipped:
                skipped.append({"order_id": o.id, "order_number": o.order_number, "reason": os_.skipped})
                continue
            stops += os_.stops
            pairs += os_.pairs
        return stops, pairs, skipped, shapes

    def _vehicles(self, db: Session, fleet: dict[str, Any], only: list[str] | None = None) -> list[vrp.Vehicle]:
        from porterchain_api.admin_models import Driver, Vehicle
        from porterchain_api.dispatch_engine.fleet_capacity import (
            RANK,
            canonical_class,
            vehicle_by_id,
        )
        from porterchain_api.dispatch_engine.legs import TORONTO

        q = db.query(Driver).filter(Driver.status == "APPROVED")
        q = q.filter(Driver.id.in_(only)) if only else q.filter(Driver.is_online.is_(True))
        out: list[vrp.Vehicle] = []
        cap = float(fleet.get("max_fill") or 0.85)
        for d in q.limit(100).all():
            classes = sorted(
                {c for c in (canonical_class(v.vehicle_class) for v in db.query(Vehicle).filter(
                    Vehicle.driver_id == d.id, Vehicle.is_active.is_(True)).all()) if c},
                key=lambda c: RANK.get(c, 9),
            )
            spec = vehicle_by_id(fleet, classes[-1]) if classes else None
            if spec is None or not spec.get("enabled", True):
                continue
            out.append(vrp.Vehicle(
                id=f"v-{d.id}", driver_id=d.id, vehicle_class=spec["id"],
                cap_kg=float(spec["max_kg"]) * cap, cap_boxes=int(spec["max_boxes"] * cap),
                start=self.position_fn(d.id) or TORONTO, hourly_cents=int(fleet.get("hourly_cost_cents") or 2700),
            ))
        return out

    def _matrix(self, vehicles: list[vrp.Vehicle], stops: list[StopSpec]) -> tuple[list[list[int]], str]:
        pts = vrp.points(vehicles, stops)
        if len(pts) > 400:
            raise ValueError("plan_too_large_split_by_area")
        m = self.matrix_fn(pts)
        if not m or len(m) != len(pts):
            # Road times only (Valhalla) — never straight-line guesses.
            raise ValueError("road_router_unavailable")
        return m, "valhalla"

    # ------------------------------------------------------------ solve
    def _solve(self, problem: vrp.Problem) -> dict[str, Any]:
        from porterchain_api.config import get_settings

        compare: dict[str, Any] = {}
        best_routes = vrp.solve_ortools(problem)
        best = vrp.evaluate(problem, best_routes)
        best["solver"] = "ortools"
        compare["ortools"] = {k: best[k] for k in ("cost_cents", "feasible")} | {"dropped": len(best["dropped"])}
        settings = get_settings()
        fn = self.cuopt_fn
        if fn is None and settings.dispatch_cuopt_enabled:
            from porterchain_api.dispatch_engine.cuopt_solver import solve_cuopt

            def fn(p: vrp.Problem) -> dict | None:
                return solve_cuopt(p, base_url=settings.dispatch_cuopt_url)
        if fn is not None:
            cu = fn(problem)
            if cu is None:
                compare["cuopt"] = {"status": "unavailable — OR-Tools kept"}
            else:
                ev = vrp.evaluate(problem, cu)
                compare["cuopt"] = {k: ev[k] for k in ("cost_cents", "feasible")} | {"dropped": len(ev["dropped"])}
                if vrp.better(ev, best):
                    best, best["solver"] = ev, "cuopt"
        best["compare"] = compare
        return best

    def _persist(self, db: Session, plan_eval: dict[str, Any], *, meta: dict[str, Any], actor: str | None,
                 parent: Any | None = None) -> Any:
        from porterchain_api.dispatch_engine.models import DispatchPlan, DispatchRoute

        summary = {
            **meta, "cost_cents": plan_eval["cost_cents"], "vehicles_used": plan_eval["vehicles_used"],
            "dropped": plan_eval["dropped"], "feasible": plan_eval["feasible"],
            "violations": plan_eval["violations"], "compare": plan_eval.get("compare", {}),
        }
        plan = DispatchPlan(
            service_date=datetime.now(TZ).date(), status="draft", solver=plan_eval.get("solver", "ortools"),
            version=(parent.version + 1) if parent is not None else 1, parent_id=parent.id if parent is not None else None,
            summary=summary, created_by=actor,
        )
        db.add(plan)
        db.flush()
        for r in plan_eval["routes"]:
            db.add(DispatchRoute(
                plan_id=plan.id, vehicle_id=r["vehicle_id"], driver_id=r["driver_id"], vehicle_class=r["vehicle_class"],
                stops=r["stops"], seconds=r["seconds"], cost_cents=r["cost_cents"], fill_pct=r["fill_pct"],
            ))
        db.commit()
        return plan

    def plan(self, db: Session, *, actor: str | None, order_ids: list[str] | None = None, time_limit_s: int = 5,
             driver_ids: list[str] | None = None) -> dict:
        from porterchain_api.dispatch_engine.fleet_capacity import load_fleet

        fleet = load_fleet(db)
        orders = self._orders(db, order_ids)
        stops, pairs, skipped, shapes = self._stops(db, orders)
        vehicles = self._vehicles(db, fleet, only=driver_ids)
        if not vehicles:
            raise ValueError("no_online_drivers_with_vehicle")
        matrix, source = self._matrix(vehicles, stops)
        problem = vrp.Problem(stops=stops, pairs=pairs, vehicles=vehicles, matrix=matrix, time_limit_s=time_limit_s)
        ev = self._solve(problem)
        plan = self._persist(db, ev, actor=actor, meta={
            "orders": len(orders), "pairs": len(pairs), "shapes": shapes, "skipped": skipped,
            "matrix": source, "order_ids": [o.id for o in orders], "kind": "plan",
        })
        return self.get(db, plan.id)

    def replan(self, db: Session, plan_id: str, *, actor: str | None) -> dict:
        """Mid-day: keep loaded freight on its vehicle, re-sequence the rest + new orders."""
        from porterchain_api.dispatch_engine.fleet_capacity import load_fleet
        from porterchain_api.dispatch_engine.models import DispatchPlan, DispatchRoute

        base = db.get(DispatchPlan, plan_id)
        if base is None:
            raise LookupError("plan_not_found")
        routes = db.query(DispatchRoute).filter(DispatchRoute.plan_id == base.id).all()
        fleet = load_fleet(db)
        planned_ids = list(dict.fromkeys(s["order_id"] for r in routes for s in r.stops))
        new_ids = [o.id for o in self._orders(db, None)]
        orders = self._orders(db, list(dict.fromkeys(planned_ids + new_ids)))
        state = {o.id: o.state for o in orders}
        stops, pairs, skipped, shapes = self._stops(db, orders)
        done: set[str] = set()
        for p, d in pairs:
            st = state.get(p.split(":", 1)[0])
            if st in DONE:
                done |= {p, d}
            elif st in PICKED:
                done.add(p)
        # Exact stop-level check-ins from the driver app beat order-state inference.
        from porterchain_api.dispatch_engine.driver_route import DriverRouteService

        done |= DriverRouteService().done_keys(db, [r.id for r in routes])
        drivers = [r.driver_id for r in routes if r.driver_id]
        vehicles = self._vehicles(db, fleet, only=drivers) + [
            v for v in self._vehicles(db, fleet) if v.driver_id not in drivers
        ]
        prior = {f"v-{r.driver_id}": [s["key"] for s in r.stops] for r in routes if r.driver_id}
        for v in vehicles:  # orders already picked by a driver outside the plan stay with them
            for o in orders:
                if o.assigned_driver_id == v.driver_id and state.get(o.id) in PICKED:
                    prior.setdefault(v.id, []).extend(s.key for s in stops if s.order_id == o.id)
        base_problem = vrp.Problem(stops=stops, pairs=pairs, vehicles=vehicles, matrix=[])
        positions = {v.id: p for v in vehicles if v.driver_id and (p := self.position_fn(v.driver_id))}
        problem = vrp.replan_problem(base_problem, prior, done, positions)
        problem.matrix, source = self._matrix(problem.vehicles, problem.stops)
        ev = self._solve(problem)
        plan = self._persist(db, ev, actor=actor, parent=base, meta={
            "orders": len(orders), "pairs": len(problem.pairs), "shapes": shapes, "skipped": skipped,
            "matrix": source, "order_ids": [o.id for o in orders], "kind": "replan", "done_stops": len(done),
        })
        return self.get(db, plan.id)

    # ------------------------------------------------------------ read / commit / explain
    def get(self, db: Session, plan_id: str) -> dict:
        from porterchain_api.admin_models import Driver
        from porterchain_api.booking_models import Order
        from porterchain_api.dispatch_engine.models import DispatchPlan, DispatchRoute

        plan = db.get(DispatchPlan, plan_id)
        if plan is None:
            raise LookupError("plan_not_found")
        routes = db.query(DispatchRoute).filter(DispatchRoute.plan_id == plan.id).order_by(DispatchRoute.seconds.desc()).all()
        dids = [r.driver_id for r in routes if r.driver_id]
        names = {d.id: d.full_name for d in db.query(Driver).filter(Driver.id.in_(dids)).all()} if dids else {}
        oids = list({s["order_id"] for r in routes for s in r.stops})
        numbers = {o.id: o.order_number for o in db.query(Order).filter(Order.id.in_(oids)).all()} if oids else {}
        return {
            "id": plan.id, "status": plan.status, "solver": plan.solver, "version": plan.version,
            "parent_id": plan.parent_id, "service_date": plan.service_date.isoformat(),
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "committed_at": plan.committed_at.isoformat() if plan.committed_at else None,
            "summary": plan.summary,
            "routes": [{
                "id": r.id, "vehicle_class": r.vehicle_class, "driver_id": r.driver_id,
                "driver_name": names.get(r.driver_id or ""), "seconds": r.seconds, "cost_cents": r.cost_cents,
                "fill_pct": r.fill_pct, "status": r.status,
                "stops": [{**s, "order_number": numbers.get(s["order_id"])} for s in r.stops],
            } for r in routes],
        }

    def latest(self, db: Session) -> dict | None:
        from porterchain_api.dispatch_engine.models import DispatchPlan

        row = (
            db.query(DispatchPlan).filter(DispatchPlan.status.in_(("draft", "committed")))
            .order_by(DispatchPlan.created_at.desc()).first()
        )
        return self.get(db, row.id) if row else None

    def commit(self, db: Session, settings: Any, ctx: Any, plan_id: str) -> dict:
        """Admin-approved: assign each route's orders to its driver through the normal path."""
        from porterchain_api.admin_engine.operations_service import (
            AdminOperationsService,
        )
        from porterchain_api.booking_models import Order
        from porterchain_api.dispatch_engine.models import DispatchPlan, DispatchRoute

        plan = db.get(DispatchPlan, plan_id)
        if plan is None:
            raise LookupError("plan_not_found")
        if plan.status != "draft":
            raise ValueError("plan_not_draft")
        ops = AdminOperationsService()
        assigned, skipped = 0, []
        for r in db.query(DispatchRoute).filter(DispatchRoute.plan_id == plan.id).all():
            if not r.driver_id:
                continue
            for oid in dict.fromkeys(s["order_id"] for s in r.stops):
                o = db.get(Order, oid)
                if o is None or o.assigned_driver_id == r.driver_id:
                    continue
                if o.assigned_driver_id or o.state not in POOL:
                    skipped.append({"order_id": oid, "reason": f"already {o.state.lower()}"})
                    continue
                try:
                    ops.assign_driver(db, settings, ctx, oid, r.driver_id)
                    assigned += 1
                except (ValueError, LookupError, PermissionError) as exc:
                    db.rollback()
                    skipped.append({"order_id": oid, "reason": str(exc)})
            r.status = "committed"
        db.query(DispatchPlan).filter(
            DispatchPlan.status == "committed", DispatchPlan.service_date == plan.service_date
        ).update({DispatchPlan.status: "superseded"}, synchronize_session=False)
        plan.status = "committed"
        plan.committed_at = _now()
        plan.committed_by = getattr(getattr(ctx, "user", None), "id", None)
        plan.summary = {**(plan.summary or {}), "commit": {"assigned": assigned, "skipped": skipped}}
        db.commit()
        return self.get(db, plan.id)

    def explain(self, db: Session, plan_id: str) -> dict:
        from porterchain_api.config import get_settings
        from porterchain_api.dispatch_engine.models import DispatchRoute
        from porterchain_api.dispatch_engine.plan_explain import (
            llm_explain,
            redact,
            rules_explain,
        )

        data = self.get(db, plan_id)
        routes = db.query(DispatchRoute).filter(DispatchRoute.plan_id == plan_id).all()
        orders = self._orders(db, list({s["order_id"] for r in routes for s in r.stops}))
        stops, _, _, _ = self._stops(db, orders)
        by_key = {s.key: s for s in stops}
        summary = redact({
            "routes": [{**r, "stops": r["stops"]} for r in data["routes"]],
            "dropped": data["summary"].get("dropped", []), "cost_cents": data["summary"].get("cost_cents", 0),
            "solver": data["solver"], "compare": data["summary"].get("compare", {}),
        }, by_key)
        out = rules_explain(summary)
        if get_settings().dispatch_llm_explain_enabled:
            try:
                from porterchain_api.intelligence_engine.nim_client import (
                    chat_completion,
                    nim_configured,
                )

                if nim_configured():
                    out = llm_explain(summary, chat_completion) | {"rules": out}
            except Exception as exc:  # noqa: BLE001 — rules answer stands
                out["llm_error"] = type(exc).__name__
        out["sent_to_llm"] = summary if out.get("source") == "nvidia_nim" else None
        return out
