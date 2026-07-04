"""Enterprise Route Center — planning, optimization, dispatch orchestration.

Per masterrule.md:
- Reads Porterchain order mirror for planning queue
- Valhalla/OSRM via MapsService for distance matrix and simulation
- Fleetbase execution ONLY through fleetbase_adapter (never direct HTTP)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.control_tower_service import ControlTowerService
from porterchain_api.admin_engine.live_map_service import LiveMapService
from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, Driver, RouteCenterPlan, RouteCenterTemplate, Vehicle
from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
from porterchain_api.models import Order
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration
from porterchain_services.maps.service import MapsService

PLAN_STATUSES = ("waiting", "planned", "optimized", "dispatched", "active", "completed", "cancelled")
STRATEGIES = (
    "fastest",
    "shortest",
    "balanced",
    "lowest_fuel",
    "lowest_cost",
    "priority_deliveries",
    "time_windows",
    "merchant_sla",
    "custom",
)
VEHICLE_CLASSES = ("sedan", "suv", "pickup", "cargo_van", "sprinter_van", "box_truck")


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _parse_iso_naive(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _coords(addr: dict | None) -> tuple[float, float] | None:
    if not addr:
        return None
    lat = addr.get("lat") or addr.get("latitude")
    lng = addr.get("lng") or addr.get("lon") or addr.get("longitude")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


class RouteCenterService:
    def __init__(self) -> None:
        self._tower = ControlTowerService()
        self._ops = AdminOperationsService()
        self._live_map = LiveMapService()
        self._sync = BookingSyncService()

    # ------------------------------------------------------------------ #
    # Dashboard
    # ------------------------------------------------------------------ #
    def dashboard(self, db: Session) -> dict[str, Any]:
        stats = self._tower.stats(db)
        status_counts = dict.fromkeys(PLAN_STATUSES, 0)
        for row in db.query(RouteCenterPlan.status, func.count(RouteCenterPlan.id)).group_by(RouteCenterPlan.status):
            status_counts[row[0]] = row[1]

        plans = db.query(RouteCenterPlan).filter(RouteCenterPlan.status.in_(("optimized", "dispatched", "active"))).all()
        total_distance_m = sum(int(p.simulation.get("distance_meters") or 0) for p in plans)
        total_fuel_l = sum(float(p.simulation.get("fuel_liters") or 0) for p in plans)
        late_routes = sum(1 for p in plans if p.simulation.get("late_risk"))
        on_time = [p for p in plans if p.status == "completed" and not p.simulation.get("late_risk")]

        vehicles_busy = (
            db.query(func.count(Vehicle.id))
            .filter(Vehicle.is_active == True, Vehicle.driver_id.isnot(None))  # noqa: E712
            .scalar()
            or 0
        )
        vehicles_total = db.query(func.count(Vehicle.id)).filter(Vehicle.is_active == True).scalar() or 0  # noqa: E712

        return {
            "routes_waiting": status_counts.get("waiting", 0),
            "routes_planned": status_counts.get("planned", 0),
            "routes_optimized": status_counts.get("optimized", 0),
            "routes_dispatched": status_counts.get("dispatched", 0),
            "routes_active": status_counts.get("active", 0),
            "routes_completed": status_counts.get("completed", 0),
            "drivers_available": stats["drivers_online"],
            "drivers_busy": max(0, stats["drivers_online"] - stats.get("drivers_offline", 0)),
            "vehicles_available": max(0, vehicles_total - vehicles_busy),
            "vehicles_busy": vehicles_busy,
            "orders_waiting": stats["waiting_dispatch"],
            "capacity_utilization_pct": round(
                (vehicles_busy / vehicles_total * 100) if vehicles_total else 0, 1
            ),
            "todays_distance_km": round(total_distance_m / 1000, 1),
            "fuel_estimate_liters": round(total_fuel_l, 1),
            "average_eta_minutes": round(
                sum(p.simulation.get("duration_minutes", 0) for p in plans) / max(len(plans), 1), 1
            ),
            "late_routes": late_routes,
            "on_time_pct": round(len(on_time) / max(len(plans), 1) * 100, 1),
            "orders_in_flight": stats["active_deliveries"],
        }

    # ------------------------------------------------------------------ #
    # Planning queue
    # ------------------------------------------------------------------ #
    def planning_queue(self, db: Session) -> dict[str, list[dict]]:
        queue = self._tower.queue(db, limit=200)
        buckets: dict[str, list[dict]] = {
            "website_orders": [],
            "merchant_orders": [],
            "scheduled_orders": [],
            "returns": [],
            "express_orders": [],
            "grouped_orders": [],
            "ready_for_planning": [],
        }
        now = _now()
        for item in queue:
            enriched = {**item, "source_type": item.get("source_type") or "website"}
            state = item.get("state", "")
            if state in ("RETURN_TO_SENDER",):
                buckets["returns"].append(enriched)
            elif item.get("high_priority"):
                buckets["express_orders"].append(enriched)
            elif item.get("merchant"):
                buckets["merchant_orders"].append(enriched)
            else:
                buckets["website_orders"].append(enriched)
            eta = item.get("eta")
            if eta:
                try:
                    sched = _parse_iso_naive(eta)
                    if sched > now + timedelta(hours=2):
                        buckets["scheduled_orders"].append(enriched)
                except ValueError:
                    pass
            buckets["ready_for_planning"].append(enriched)
        return buckets

    # ------------------------------------------------------------------ #
    # Route plans CRUD
    # ------------------------------------------------------------------ #
    def list_plans(
        self,
        db: Session,
        *,
        status: str | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        q = db.query(RouteCenterPlan).order_by(RouteCenterPlan.updated_at.desc())
        if status:
            q = q.filter(RouteCenterPlan.status == status)
        if search:
            like = f"%{search}%"
            q = q.filter(RouteCenterPlan.name.ilike(like))
        return [self._plan_dict(p) for p in q.limit(limit).all()]

    def get_plan(self, db: Session, plan_id: str) -> dict:
        plan = db.query(RouteCenterPlan).filter(RouteCenterPlan.id == plan_id).first()
        if not plan:
            raise LookupError("route_plan_not_found")
        detail = self._plan_dict(plan)
        detail["audit_log"] = self._audit_for_plan(db, plan_id)
        detail["live_map"] = self._live_map.snapshot(db)
        return detail

    def create_plan(
        self,
        db: Session,
        ctx: AdminContext,
        *,
        name: str,
        order_ids: list[str],
        strategy: str = "balanced",
        zone: str | None = None,
        template_id: str | None = None,
    ) -> dict:
        stops = self._build_stops_from_orders(db, order_ids)
        plan = RouteCenterPlan(
            name=name,
            status="planned" if order_ids else "waiting",
            strategy=strategy if strategy in STRATEGIES else "balanced",
            zone=zone,
            order_ids=order_ids,
            stops=stops,
            template_id=template_id,
            created_by=ctx.user.id,
        )
        db.add(plan)
        self._audit(db, ctx, "route.plan_created", plan.id, {"order_ids": order_ids})
        db.commit()
        db.refresh(plan)
        return self._plan_dict(plan)

    def update_plan(
        self,
        db: Session,
        ctx: AdminContext,
        plan_id: str,
        *,
        name: str | None = None,
        order_ids: list[str] | None = None,
        stops: list[dict] | None = None,
        strategy: str | None = None,
        driver_id: str | None = None,
        vehicle_id: str | None = None,
    ) -> dict:
        plan = db.query(RouteCenterPlan).filter(RouteCenterPlan.id == plan_id).first()
        if not plan:
            raise LookupError("route_plan_not_found")
        if plan.status in ("dispatched", "active", "completed"):
            raise ValueError("route_plan_locked")
        if name:
            plan.name = name
        if order_ids is not None:
            plan.order_ids = order_ids
            plan.stops = self._build_stops_from_orders(db, order_ids)
        if stops is not None:
            plan.stops = stops
            plan.order_ids = list({s.get("order_id") for s in stops if s.get("order_id")})
        if strategy:
            plan.strategy = strategy
        if driver_id is not None:
            plan.driver_id = driver_id or None
        if vehicle_id is not None:
            plan.vehicle_id = vehicle_id or None
        db.commit()
        db.refresh(plan)
        self._audit(db, ctx, "route.plan_updated", plan.id, {})
        return self._plan_dict(plan)

    def clone_plan(self, db: Session, ctx: AdminContext, plan_id: str) -> dict:
        src = db.query(RouteCenterPlan).filter(RouteCenterPlan.id == plan_id).first()
        if not src:
            raise LookupError("route_plan_not_found")
        clone = RouteCenterPlan(
            name=f"{src.name} (copy)",
            status="planned",
            strategy=src.strategy,
            zone=src.zone,
            order_ids=list(src.order_ids or []),
            stops=list(src.stops or []),
            template_id=src.template_id,
            created_by=ctx.user.id,
        )
        db.add(clone)
        db.commit()
        db.refresh(clone)
        self._audit(db, ctx, "route.plan_cloned", clone.id, {"source_id": plan_id})
        return self._plan_dict(clone)

    def merge_plans(self, db: Session, ctx: AdminContext, plan_ids: list[str], name: str) -> dict:
        plans = db.query(RouteCenterPlan).filter(RouteCenterPlan.id.in_(plan_ids)).all()
        if len(plans) < 2:
            raise ValueError("merge_requires_two_plans")
        order_ids: list[str] = []
        stops: list[dict] = []
        for p in plans:
            order_ids.extend(p.order_ids or [])
            stops.extend(p.stops or [])
        order_ids = list(dict.fromkeys(order_ids))
        merged = self.create_plan(db, ctx, name=name, order_ids=order_ids, strategy=plans[0].strategy)
        for p in plans:
            if p.id != merged["id"]:
                p.status = "cancelled"
        db.commit()
        self._audit(db, ctx, "route.plans_merged", merged["id"], {"merged": plan_ids})
        return merged

    def split_plan(self, db: Session, ctx: AdminContext, plan_id: str, groups: list[list[str]]) -> list[dict]:
        plan = db.query(RouteCenterPlan).filter(RouteCenterPlan.id == plan_id).first()
        if not plan:
            raise LookupError("route_plan_not_found")
        results = []
        for i, group in enumerate(groups):
            child = self.create_plan(
                db, ctx, name=f"{plan.name} — split {i + 1}", order_ids=group, strategy=plan.strategy
            )
            results.append(child)
        plan.status = "cancelled"
        db.commit()
        self._audit(db, ctx, "route.plan_split", plan_id, {"children": [r["id"] for r in results]})
        return results

    # ------------------------------------------------------------------ #
    # Optimization
    # ------------------------------------------------------------------ #
    def optimize_plan(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        plan_id: str,
        *,
        strategy: str | None = None,
        engine: str = "valhalla",
    ) -> dict:
        plan = db.query(RouteCenterPlan).filter(RouteCenterPlan.id == plan_id).first()
        if not plan:
            raise LookupError("route_plan_not_found")
        if strategy:
            plan.strategy = strategy

        stops = list(plan.stops or [])
        if len(stops) < 2:
            raise ValueError("insufficient_stops")

        points = []
        for s in stops:
            c = _coords(s.get("location"))
            if c:
                points.append(c)
        if len(points) < 2:
            raise ValueError("missing_coordinates")

        maps = MapsService()
        distance_m, duration_s = maps.route_distance_meters(points)
        if engine == "osrm" and maps.settings.osrm_url:
            # OSRM leg matrix for ETA refinement (Valhalla remains primary optimizer)
            osrm_maps = MapsService()
            if osrm_maps.settings.routing_engine != "osrm":
                osrm_m, osrm_s = self._osrm_leg_matrix(points)
                if osrm_m:
                    distance_m, duration_s = osrm_m, osrm_s
        simulation = self._simulate_route(db, plan, distance_m or 0, duration_s or 0, strategy=plan.strategy)
        plan.simulation = simulation
        plan.recommendations = self._recommendations(db, plan, simulation)
        plan.status = "optimized"

        fleetbase_ids = self._fleetbase_order_ids(db, plan.order_ids or [])
        if fleetbase_ids and settings.fleetbase_dispatch_bridge:
            adapter = get_fleetbase_integration(settings)
            run = adapter.routes.run_orchestrator(fleetbase_ids)
            if run and run.get("run_id"):
                plan.fleetbase_run_id = str(run["run_id"])

        db.commit()
        self._audit(db, ctx, "route.optimized", plan.id, {"strategy": plan.strategy, "engine": engine})
        db.refresh(plan)
        return self._plan_dict(plan)

    def simulate_plan(self, db: Session, settings: Settings, plan_id: str) -> dict:
        plan = db.query(RouteCenterPlan).filter(RouteCenterPlan.id == plan_id).first()
        if not plan:
            raise LookupError("route_plan_not_found")
        points = [_coords(s.get("location")) for s in (plan.stops or [])]
        points = [p for p in points if p]
        maps = MapsService()
        distance_m, duration_s = maps.route_distance_meters(points) if len(points) >= 2 else (0, 0)
        simulation = self._simulate_route(db, plan, distance_m or 0, duration_s or 0, strategy=plan.strategy)
        plan.simulation = simulation
        plan.recommendations = self._recommendations(db, plan, simulation)
        db.commit()
        return simulation

    # ------------------------------------------------------------------ #
    # Dispatch (Fleetbase adapter only)
    # ------------------------------------------------------------------ #
    def dispatch_plan(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        plan_id: str,
        *,
        driver_id: str,
        vehicle_id: str | None = None,
        approve: bool = False,
    ) -> dict:
        plan = db.query(RouteCenterPlan).filter(RouteCenterPlan.id == plan_id).first()
        if not plan:
            raise LookupError("route_plan_not_found")
        if plan.requires_approval and not approve and ctx.role.value not in ("super_admin", "admin"):
            raise PermissionError("dispatch_approval_required")

        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if not driver:
            raise LookupError("driver_not_found")

        if plan.fleetbase_run_id and settings.fleetbase_dispatch_bridge:
            adapter = get_fleetbase_integration(settings)
            adapter.routes.commit_orchestrator(plan.fleetbase_run_id)

        dispatched = []
        for order_id in plan.order_ids or []:
            order = self._ops.assign_driver(db, settings, ctx, order_id, driver_id)
            if driver.fleetbase_driver_id and order.fleetbase_order_id:
                self._sync.push_driver_assignment(
                    db, settings, order, fleetbase_driver_id=driver.fleetbase_driver_id
                )
            dispatched.append(order.id)

        plan.driver_id = driver_id
        plan.vehicle_id = vehicle_id
        plan.status = "dispatched"
        plan.dispatched_at = _now()
        if approve:
            plan.approved_by = ctx.user.id
        db.commit()
        self._audit(db, ctx, "route.dispatched", plan.id, {"driver_id": driver_id, "orders": dispatched})
        return self._plan_dict(plan)

    def bulk_dispatch(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        plan_ids: list[str],
        driver_id: str,
    ) -> list[dict]:
        return [self.dispatch_plan(db, settings, ctx, pid, driver_id=driver_id) for pid in plan_ids]

    def pause_plan(self, db: Session, ctx: AdminContext, plan_id: str) -> dict:
        return self._set_status(db, ctx, plan_id, "planned", "route.paused")

    def resume_plan(self, db: Session, ctx: AdminContext, plan_id: str) -> dict:
        return self._set_status(db, ctx, plan_id, "active", "route.resumed")

    def cancel_plan(self, db: Session, ctx: AdminContext, plan_id: str) -> dict:
        return self._set_status(db, ctx, plan_id, "cancelled", "route.cancelled")

    # ------------------------------------------------------------------ #
    # Templates
    # ------------------------------------------------------------------ #
    def list_templates(self, db: Session) -> list[dict]:
        return [self._template_dict(t) for t in db.query(RouteCenterTemplate).filter(RouteCenterTemplate.is_active == True).all()]  # noqa: E712

    def save_template_from_plan(self, db: Session, ctx: AdminContext, plan_id: str, name: str, template_type: str) -> dict:
        plan = db.query(RouteCenterPlan).filter(RouteCenterPlan.id == plan_id).first()
        if not plan:
            raise LookupError("route_plan_not_found")
        tpl = RouteCenterTemplate(
            name=name,
            template_type=template_type,
            zone=plan.zone,
            stops=list(plan.stops or []),
            config={"strategy": plan.strategy},
            created_by=ctx.user.id,
        )
        db.add(tpl)
        db.commit()
        db.refresh(tpl)
        self._audit(db, ctx, "route.template_saved", tpl.id, {"plan_id": plan_id})
        return self._template_dict(tpl)

    def create_plan_from_template(self, db: Session, ctx: AdminContext, template_id: str, name: str | None = None) -> dict:
        tpl = db.query(RouteCenterTemplate).filter(RouteCenterTemplate.id == template_id).first()
        if not tpl:
            raise LookupError("template_not_found")
        order_ids = [s.get("order_id") for s in (tpl.stops or []) if s.get("order_id")]
        return self.create_plan(
            db,
            ctx,
            name=name or tpl.name,
            order_ids=[o for o in order_ids if o],
            strategy=(tpl.config or {}).get("strategy", "balanced"),
            zone=tpl.zone,
            template_id=tpl.id,
        )

    # ------------------------------------------------------------------ #
    # Analytics & history
    # ------------------------------------------------------------------ #
    def analytics(self, db: Session) -> dict[str, Any]:
        completed = db.query(RouteCenterPlan).filter(RouteCenterPlan.status == "completed").all()
        optimized = db.query(RouteCenterPlan).filter(RouteCenterPlan.status.in_(("optimized", "dispatched", "active", "completed"))).all()
        distance_saved_km = sum(float(p.simulation.get("distance_saved_km") or 0) for p in optimized)
        fuel_saved = sum(float(p.simulation.get("fuel_saved_liters") or 0) for p in optimized)
        time_saved = sum(float(p.simulation.get("time_saved_minutes") or 0) for p in optimized)
        revenue = sum(int(p.simulation.get("estimated_revenue_cents") or 0) for p in optimized)
        profit = sum(int(p.simulation.get("estimated_profit_cents") or 0) for p in optimized)
        failed = db.query(func.count(RouteCenterPlan.id)).filter(RouteCenterPlan.status == "cancelled").scalar() or 0
        late = sum(1 for p in completed if p.simulation.get("late_risk"))
        return {
            "distance_saved_km": round(distance_saved_km, 1),
            "fuel_saved_liters": round(fuel_saved, 1),
            "time_saved_minutes": round(time_saved, 1),
            "revenue_cents": revenue,
            "profit_cents": profit,
            "average_stops": round(
                sum(len(p.stops or []) for p in optimized) / max(len(optimized), 1), 1
            ),
            "driver_utilization_pct": self.dashboard(db)["capacity_utilization_pct"],
            "vehicle_utilization_pct": self.dashboard(db)["capacity_utilization_pct"],
            "on_time_pct": self.dashboard(db)["on_time_pct"],
            "late_pct": round(late / max(len(completed), 1) * 100, 1),
            "failed_routes": failed,
        }

    def history(self, db: Session, *, limit: int = 50) -> list[dict]:
        rows = (
            db.query(RouteCenterPlan)
            .filter(RouteCenterPlan.status.in_(("completed", "cancelled")))
            .order_by(RouteCenterPlan.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [self._plan_dict(p) for p in rows]

    def live_execution_snapshot(self, db: Session) -> dict:
        return self._live_map.snapshot(db)

    def smart_recommendations(self, db: Session, plan_id: str) -> dict:
        plan = db.query(RouteCenterPlan).filter(RouteCenterPlan.id == plan_id).first()
        if not plan:
            raise LookupError("route_plan_not_found")
        return self._recommendations(db, plan, plan.simulation or {})

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _build_stops_from_orders(self, db: Session, order_ids: list[str]) -> list[dict]:
        stops: list[dict] = []
        for oid in order_ids:
            order = db.query(Order).filter(Order.id == oid).first()
            if not order:
                continue
            pickup = order.pickup or {}
            dropoff = order.dropoff or {}
            stops.append(
                {
                    "order_id": order.id,
                    "tracking_number": order.tracking_number,
                    "type": "pickup",
                    "location": pickup,
                    "address": pickup.get("formatted"),
                    "priority": "high" if order.amount_cents >= 20000 else "normal",
                    "status": order.state,
                }
            )
            stops.append(
                {
                    "order_id": order.id,
                    "tracking_number": order.tracking_number,
                    "type": "delivery",
                    "location": dropoff,
                    "address": dropoff.get("formatted"),
                    "priority": "high" if order.amount_cents >= 20000 else "normal",
                    "status": order.state,
                }
            )
        return stops

    def _simulate_route(
        self,
        db: Session,
        plan: RouteCenterPlan,
        distance_m: int,
        duration_s: int,
        *,
        strategy: str,
    ) -> dict[str, Any]:
        orders = db.query(Order).filter(Order.id.in_(plan.order_ids or [])).all() if plan.order_ids else []
        revenue = sum(o.amount_cents for o in orders)
        fuel_l = (distance_m / 1000) * 0.12
        if strategy == "lowest_fuel":
            fuel_l *= 0.92
        cost_cents = int(distance_m / 1000 * 45 + fuel_l * 180)
        naive_m = distance_m * 1.15 if strategy != "shortest" else distance_m * 1.05
        return {
            "distance_meters": distance_m,
            "duration_seconds": duration_s,
            "duration_minutes": round(duration_s / 60, 1),
            "fuel_liters": round(fuel_l, 2),
            "estimated_cost_cents": cost_cents,
            "estimated_revenue_cents": revenue,
            "estimated_profit_cents": revenue - cost_cents,
            "capacity_usage_pct": min(100, len(plan.order_ids or []) * 12),
            "driver_hours": round(duration_s / 3600, 2),
            "traffic_delay_minutes": 5 if strategy == "fastest" else 2,
            "late_risk": duration_s > 8 * 3600,
            "distance_saved_km": round(max(0, (naive_m - distance_m) / 1000), 1),
            "fuel_saved_liters": round(max(0, (naive_m - distance_m) / 1000 * 0.12), 2),
            "time_saved_minutes": round(max(0, (naive_m - distance_m) / 1000 * 2.5), 1),
            "strategy": strategy,
            "engine": "valhalla",
        }

    def _recommendations(self, db: Session, plan: RouteCenterPlan, simulation: dict) -> dict:
        drivers = self._tower.assignable_drivers(db)
        vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).all()  # noqa: E712
        stop_count = len(plan.stops or [])
        parcel_count = len(plan.order_ids or [])
        vehicle_class = self._recommend_vehicle(parcel_count, stop_count)
        warnings: list[str] = []
        if simulation.get("capacity_usage_pct", 0) > 90:
            warnings.append("capacity_warning")
        if simulation.get("driver_hours", 0) > 8:
            warnings.append("overtime_warning")
        if simulation.get("traffic_delay_minutes", 0) > 10:
            warnings.append("traffic_warning")
        dup_addrs = len({s.get("address") for s in (plan.stops or []) if s.get("address")})
        if dup_addrs < len(plan.stops or []) / 2:
            warnings.append("duplicate_stops")
        suggested_v = next((v for v in vehicles if v.vehicle_class == vehicle_class), vehicles[0] if vehicles else None)
        return {
            "vehicle_class": vehicle_class,
            "suggested_driver": drivers[0] if drivers else None,
            "suggested_vehicle": self._vehicle_dict(suggested_v),
            "merge_candidates": [],
            "split_recommended": stop_count > 20,
            "delay_departure_minutes": 0 if not warnings else 15,
            "reoptimize_recommended": plan.status == "planned",
            "warnings": warnings,
        }

    def _osrm_leg_matrix(self, points: list[tuple[float, float]]) -> tuple[int | None, int | None]:
        """Distance matrix via OSRM when configured."""
        import httpx

        if len(points) < 2:
            return None, None
        maps = MapsService()
        url = maps.settings.osrm_url
        if not url:
            return None, None
        coords = ";".join(f"{lng},{lat}" for lat, lng in points)
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(
                    f"{url.rstrip('/')}/route/v1/driving/{coords}",
                    params={"overview": "false"},
                )
                if resp.status_code >= 400:
                    return None, None
                data = resp.json()
                if data.get("code") != "Ok" or not data.get("routes"):
                    return None, None
                route = data["routes"][0]
                return int(route.get("distance", 0)), int(route.get("duration", 0))
        except httpx.HTTPError:
            return None, None

    def _vehicle_dict(self, vehicle: Vehicle | None) -> dict | None:
        if not vehicle:
            return None
        return {
            "id": vehicle.id,
            "plate_number": vehicle.plate_number,
            "vehicle_class": vehicle.vehicle_class,
            "make_model": vehicle.make_model,
        }

    def _recommend_vehicle(self, parcels: int, stops: int) -> str:
        if parcels >= 40 or stops >= 30:
            return "box_truck"
        if parcels >= 25 or stops >= 20:
            return "sprinter_van"
        if parcels >= 12 or stops >= 14:
            return "cargo_van"
        if parcels >= 6:
            return "suv"
        return "sedan"

    def _fleetbase_order_ids(self, db: Session, order_ids: list[str]) -> list[str]:
        rows = db.query(Order.fleetbase_order_id).filter(Order.id.in_(order_ids), Order.fleetbase_order_id.isnot(None)).all()
        return [r[0] for r in rows if r[0]]

    def _plan_dict(self, plan: RouteCenterPlan) -> dict:
        return {
            "id": plan.id,
            "name": plan.name,
            "status": plan.status,
            "strategy": plan.strategy,
            "zone": plan.zone,
            "order_ids": plan.order_ids or [],
            "stops": plan.stops or [],
            "driver_id": plan.driver_id,
            "vehicle_id": plan.vehicle_id,
            "simulation": plan.simulation or {},
            "recommendations": plan.recommendations or {},
            "fleetbase_run_id": plan.fleetbase_run_id,
            "template_id": plan.template_id,
            "requires_approval": plan.requires_approval,
            "approved_by": plan.approved_by,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
            "dispatched_at": plan.dispatched_at.isoformat() if plan.dispatched_at else None,
            "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
        }

    def _template_dict(self, tpl: RouteCenterTemplate) -> dict:
        return {
            "id": tpl.id,
            "name": tpl.name,
            "template_type": tpl.template_type,
            "merchant_id": tpl.merchant_id,
            "zone": tpl.zone,
            "schedule": tpl.schedule or {},
            "stops": tpl.stops or [],
            "config": tpl.config or {},
            "created_at": tpl.created_at.isoformat() if tpl.created_at else None,
        }

    def _audit(self, db: Session, ctx: AdminContext, action: str, resource_id: str, payload: dict) -> None:
        db.add(
            AdminAuditLog(
                actor_user_id=ctx.user.id,
                action=action,
                resource_type="route_plan",
                resource_id=resource_id,
                payload=payload,
            )
        )

    def _audit_for_plan(self, db: Session, plan_id: str) -> list[dict]:
        rows = (
            db.query(AdminAuditLog)
            .filter(AdminAuditLog.resource_type == "route_plan", AdminAuditLog.resource_id == plan_id)
            .order_by(AdminAuditLog.created_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": r.id,
                "action": r.action,
                "actor_user_id": r.actor_user_id,
                "payload": r.payload,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    def _set_status(self, db: Session, ctx: AdminContext, plan_id: str, status: str, action: str) -> dict:
        plan = db.query(RouteCenterPlan).filter(RouteCenterPlan.id == plan_id).first()
        if not plan:
            raise LookupError("route_plan_not_found")
        plan.status = status
        if status == "completed":
            plan.completed_at = _now()
        db.commit()
        self._audit(db, ctx, action, plan_id, {"status": status})
        return self._plan_dict(plan)
