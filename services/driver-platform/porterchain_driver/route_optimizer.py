"""Driver route optimizer — reorder assigned stops to save time and fuel."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Any

from porterchain_api.order_engine.buckets import DELIVERY_ONLY_POOL, HIGH_PRIORITY_CENTS

_EARTH_RADIUS_M = 6_371_000
_COMPLETED = frozenset(
    {
        "DELIVERED",
        "POD_COMPLETED",
        "INVOICED",
        "CLOSED",
        "CANCELLED",
        "FAILED",
        "RETURN_TO_SENDER",
        "DAMAGED",
        "LOST",
        "REFUNDED",
    }
)


def _coords(addr: dict | None) -> tuple[float, float] | None:
    if not addr:
        return None
    lat = addr.get("lat") or addr.get("latitude")
    lng = addr.get("lng") or addr.get("lon") or addr.get("longitude")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> int:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return int(_EARTH_RADIUS_M * 2 * math.asin(min(1.0, math.sqrt(h))) * 1.25)


def compute_urgency(order: Any, *, now: datetime | None = None) -> str:
    """critical > high > medium > normal based on SLA window and order value."""
    now = now or datetime.now(UTC)
    high_value = (order.amount_cents or 0) >= HIGH_PRIORITY_CENTS
    scheduled = order.scheduled_at
    if scheduled is not None:
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=UTC)
        hours = (scheduled - now).total_seconds() / 3600
        if hours < 0:
            return "critical"
        if hours <= 1:
            return "critical" if high_value else "high"
        if hours <= 3:
            return "high" if high_value else "medium"
        if hours <= 6 and high_value:
            return "high"
    return "high" if high_value else "normal"


class _StopNode:
    __slots__ = ("key", "order_id", "stop_type", "coords", "tracking", "address", "location", "priority", "status")

    def __init__(
        self,
        *,
        key: str,
        order_id: str,
        stop_type: str,
        coords: tuple[float, float],
        tracking: str,
        address: str | None,
        location: dict,
        priority: str,
        status: str,
    ) -> None:
        self.key = key
        self.order_id = order_id
        self.stop_type = stop_type
        self.coords = coords
        self.tracking = tracking
        self.address = address
        self.location = location
        self.priority = priority
        self.status = status


class DriverRouteOptimizer:
    def can_optimize(self, active_orders: list[Any]) -> bool:
        stop_count = 0
        for order in active_orders:
            delivery_only = str(order.state) in DELIVERY_ONLY_POOL
            pickup = order.pickup or {}
            dropoff = order.dropoff or {}
            pickup_coords = _coords(pickup)
            dropoff_coords = _coords(dropoff)
            if delivery_only:
                if dropoff_coords:
                    stop_count += 1
            else:
                if pickup_coords:
                    stop_count += 1
                if dropoff_coords:
                    stop_count += 1
        return stop_count >= 2

    def optimize(self, db: Any, driver: Any) -> dict[str, Any]:
        try:
            from porterchain_api.admin_models import RouteCenterPlan
        except ImportError:
            RouteCenterPlan = None  # type: ignore[assignment,misc]
        from porterchain_api.models import Order

        warnings: list[str] = []
        orders = (
            db.query(Order)
            .filter(Order.assigned_driver_id == driver.id)
            .order_by(Order.scheduled_at.asc().nullslast(), Order.created_at.asc())
            .all()
        )
        active_orders = [o for o in orders if str(o.state) not in _COMPLETED]
        if not active_orders:
            raise ValueError("no_active_jobs")

        nodes: list[_StopNode] = []
        included_ids: list[str] = []

        for order in active_orders:
            delivery_only = str(order.state) in DELIVERY_ONLY_POOL
            pickup = order.pickup or {}
            dropoff = order.dropoff or {}
            pickup_coords = _coords(pickup)
            dropoff_coords = _coords(dropoff)
            urgency = compute_urgency(order)
            priority = "high" if urgency in ("critical", "high") else "normal"

            if delivery_only:
                if not dropoff_coords:
                    warnings.append(f"missing_dropoff_coords:{order.tracking_number or order.id}")
                    continue
            else:
                if not pickup_coords:
                    warnings.append(f"missing_pickup_coords:{order.tracking_number or order.id}")
                    continue
                if not dropoff_coords:
                    warnings.append(f"missing_dropoff_coords:{order.tracking_number or order.id}")
                    continue

            if not delivery_only and pickup_coords:
                nodes.append(
                    _StopNode(
                        key=f"{order.id}:pickup",
                        order_id=order.id,
                        stop_type="pickup",
                        coords=pickup_coords,
                        tracking=order.tracking_number or "",
                        address=pickup.get("formatted") or pickup.get("line1"),
                        location=pickup,
                        priority=priority,
                        status=str(order.state),
                    )
                )
            if dropoff_coords:
                nodes.append(
                    _StopNode(
                        key=f"{order.id}:delivery",
                        order_id=order.id,
                        stop_type="delivery",
                        coords=dropoff_coords,
                        tracking=order.tracking_number or "",
                        address=dropoff.get("formatted") or dropoff.get("line1"),
                        location=dropoff,
                        priority=priority,
                        status=str(order.state),
                    )
                )
            included_ids.append(order.id)

        if len(nodes) < 2:
            raise ValueError("insufficient_stops_for_optimization")

        cost_matrix = self._build_cost_matrix(nodes)
        sequence_keys = self._solve_pd_vrp(nodes, cost_matrix)
        key_to_idx = {nodes[i].key: i for i in range(len(nodes))}
        route_indices = [key_to_idx[k] for k in sequence_keys]
        ordered_nodes = [nodes[i] for i in route_indices]

        distance_m = sum(
            cost_matrix[route_indices[i]][route_indices[i + 1]]
            for i in range(len(route_indices) - 1)
        )
        duration_s = int(distance_m / 8.33)

        optimized_stops: list[dict[str, Any]] = []
        leg_etas: list[int] = []
        cumulative_s = 0
        for seq, node in enumerate(ordered_nodes, start=1):
            if seq > 1:
                leg_m = cost_matrix[route_indices[seq - 2]][route_indices[seq - 1]]
                leg_s = int(leg_m / 8.33)
                cumulative_s += leg_s
                leg_etas.append(leg_s)
            else:
                leg_etas.append(0)
            optimized_stops.append(
                {
                    "sequence": seq,
                    "order_id": node.order_id,
                    "tracking_number": node.tracking,
                    "type": node.stop_type,
                    "location": node.location,
                    "address": node.address,
                    "priority": node.priority,
                    "status": node.status,
                    "leg_duration_seconds": leg_etas[-1],
                    "cumulative_duration_seconds": cumulative_s,
                }
            )

        metrics = {
            "stop_count": len(optimized_stops),
            "order_count": len(included_ids),
            "distance_meters": distance_m,
            "duration_seconds": duration_s,
            "duration_minutes": round((duration_s or 0) / 60, 1),
            "distance_km": round((distance_m or 0) / 1000, 2),
            "strategy": "balanced",
            "engine": "haversine",
        }

        existing = None
        if RouteCenterPlan is not None:
            existing = (
                db.query(RouteCenterPlan)
                .filter(
                    RouteCenterPlan.driver_id == driver.id,
                    RouteCenterPlan.status.in_(("dispatched", "active", "optimized")),
                )
                .order_by(RouteCenterPlan.updated_at.desc())
                .first()
            )

        if RouteCenterPlan is None:
            plan_id = str(uuid.uuid4())
            return {
                "plan_id": plan_id,
                "optimized_stops": optimized_stops,
                "metrics": metrics,
                "warnings": warnings + ["route_center_removed_use_fleetbase"],
                "order_ids": included_ids,
            }

        if existing:
            plan = existing
            plan.name = f"Driver route {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}"
            plan.status = "dispatched"
            plan.strategy = "balanced"
            plan.order_ids = included_ids
            plan.stops = optimized_stops
            plan.simulation = metrics
            plan.dispatched_at = datetime.now(UTC).replace(tzinfo=None)
        else:
            plan = RouteCenterPlan(
                id=str(uuid.uuid4()),
                name=f"Driver route {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}",
                status="dispatched",
                strategy="balanced",
                driver_id=driver.id,
                order_ids=included_ids,
                stops=optimized_stops,
                simulation=metrics,
                dispatched_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(plan)

        from porterchain_api.booking_engine._core import emit_event

        emit_event(
            db,
            event_type="driver.route_optimized",
            aggregate_type="driver",
            aggregate_id=driver.id,
            actor_type="driver",
            actor_id=driver.id,
            payload={
                "driver_id": driver.id,
                "plan_id": plan.id,
                "order_ids": included_ids,
                "metrics": metrics,
            },
        )
        db.flush()

        return {
            "plan_id": plan.id,
            "optimized_stops": optimized_stops,
            "metrics": metrics,
            "warnings": warnings,
            "order_ids": included_ids,
        }

    def priority_ranks_from_plan(self, plan: Any | None) -> dict[str, int]:
        if not plan or not plan.stops:
            return {}
        ranks: dict[str, int] = {}
        rank = 0
        for stop in sorted(plan.stops, key=lambda s: int(s.get("sequence") or 0)):
            oid = stop.get("order_id")
            if oid and oid not in ranks:
                rank += 1
                ranks[oid] = rank
        return ranks

    def reoptimize_remaining(self, db: Any, driver: Any, completed_stop_id: str) -> dict[str, Any] | None:
        """Re-order unfinished stops in the active plan from the driver's last location."""
        try:
            from porterchain_api.admin_models import RouteCenterPlan
        except ImportError:
            return None
        from porterchain_api.models import Order

        plan = (
            db.query(RouteCenterPlan)
            .filter(
                RouteCenterPlan.driver_id == driver.id,
                RouteCenterPlan.status.in_(("dispatched", "active", "optimized")),
            )
            .order_by(RouteCenterPlan.dispatched_at.desc())
            .first()
        )
        if not plan or not plan.stops:
            return None

        order_ids = list(plan.order_ids or [])
        orders_by_id = {
            o.id: o
            for o in db.query(Order).filter(Order.id.in_(order_ids)).all()
        } if order_ids else {}

        completed_order_id = completed_stop_id.rsplit("-", 1)[0]
        origin: tuple[float, float] | None = None
        for stop in plan.stops:
            if stop.get("order_id") == completed_order_id:
                loc = stop.get("location") or {}
                origin = _coords(loc)
                break

        if origin is None:
            from porterchain_api.driver_models import DriverLocationPing

            ping = (
                db.query(DriverLocationPing)
                .filter(DriverLocationPing.driver_id == driver.id)
                .order_by(DriverLocationPing.created_at.desc())
                .first()
            )
            if ping:
                origin = (float(ping.lat), float(ping.lng))

        nodes: list[_StopNode] = []
        pickup_leg_states = frozenset({"DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE", "AT_PICKUP"})
        pickup_done_states = frozenset(
            {"PICKED_UP", "IN_TRANSIT", "AT_DESTINATION", "DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"}
        )
        for stop in sorted(plan.stops, key=lambda s: int(s.get("sequence") or 0)):
            oid = stop.get("order_id")
            order = orders_by_id.get(oid)
            if not order or str(order.state) in _COMPLETED:
                continue
            stop_type_raw = stop.get("type") or "delivery"
            if stop_type_raw == "pickup":
                if str(order.state) in pickup_done_states:
                    continue
                pickup = order.pickup or stop.get("location") or {}
                coords = _coords(pickup)
                if not coords:
                    continue
                nodes.append(
                    _StopNode(
                        key=f"{oid}:pickup",
                        order_id=oid,
                        stop_type="pickup",
                        coords=coords,
                        tracking=order.tracking_number or "",
                        address=pickup.get("formatted") if isinstance(pickup, dict) else stop.get("address"),
                        location=pickup if isinstance(pickup, dict) else {},
                        priority=stop.get("priority") or "normal",
                        status=str(order.state),
                    )
                )
            else:
                if str(order.state) in ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"):
                    continue
                if str(order.state) in pickup_leg_states:
                    continue
                dropoff = order.dropoff or stop.get("location") or {}
                coords = _coords(dropoff)
                if not coords:
                    continue
                nodes.append(
                    _StopNode(
                        key=f"{oid}:delivery",
                        order_id=oid,
                        stop_type="delivery",
                        coords=coords,
                        tracking=order.tracking_number or "",
                        address=dropoff.get("formatted") if isinstance(dropoff, dict) else stop.get("address"),
                        location=dropoff if isinstance(dropoff, dict) else {},
                        priority=stop.get("priority") or "normal",
                        status=str(order.state),
                    )
                )

        if len(nodes) < 1:
            return None

        if len(nodes) == 1:
            ordered_nodes = nodes
            route_indices = [0]
        else:
            if origin is None:
                origin = nodes[0].coords
            cost_matrix = self._build_cost_matrix(nodes)
            start_idx = min(range(len(nodes)), key=lambda i: _haversine_m(origin, nodes[i].coords))
            sequence_keys = self._solve_pd_vrp_from(nodes, cost_matrix, start_idx)
            key_to_idx = {nodes[i].key: i for i in range(len(nodes))}
            route_indices = [key_to_idx[k] for k in sequence_keys]
            ordered_nodes = [nodes[i] for i in route_indices]

        completed_stops = [s for s in plan.stops if self._stop_is_done(s, orders_by_id)]
        seq_offset = len(completed_stops)
        optimized_tail: list[dict[str, Any]] = []
        cumulative_s = 0
        leg_etas: list[int] = []
        cost_matrix = self._build_cost_matrix(ordered_nodes) if len(ordered_nodes) > 1 else [[0]]
        for seq, node in enumerate(ordered_nodes, start=1):
            if seq > 1:
                leg_m = cost_matrix[route_indices[seq - 2]][route_indices[seq - 1]] if len(ordered_nodes) > 1 else 0
                leg_s = int(leg_m / 8.33)
                cumulative_s += leg_s
                leg_etas.append(leg_s)
            else:
                leg_etas.append(0)
            optimized_tail.append(
                {
                    "sequence": seq_offset + seq,
                    "order_id": node.order_id,
                    "tracking_number": node.tracking,
                    "type": node.stop_type,
                    "location": node.location,
                    "address": node.address,
                    "priority": node.priority,
                    "status": node.status,
                    "leg_duration_seconds": leg_etas[-1],
                    "cumulative_duration_seconds": cumulative_s,
                }
            )

        plan.stops = completed_stops + optimized_tail
        plan.simulation = dict(plan.simulation or {})
        plan.simulation["stop_count"] = len(plan.stops)
        plan.updated_at = datetime.now(UTC).replace(tzinfo=None)

        from porterchain_api.booking_engine._core import emit_event

        emit_event(
            db,
            event_type="driver.route_changed",
            aggregate_type="driver",
            aggregate_id=driver.id,
            actor_type="driver",
            actor_id=driver.id,
            payload={
                "driver_id": driver.id,
                "plan_id": plan.id,
                "trigger": "stop_completed",
                "completed_stop_id": completed_stop_id,
            },
        )
        db.flush()
        return {"plan_id": plan.id, "remaining_stops": len(optimized_tail)}

    @staticmethod
    def _stop_is_done(stop: dict, orders_by_id: dict) -> bool:
        oid = stop.get("order_id")
        order = orders_by_id.get(oid)
        if not order:
            return False
        state = str(order.state)
        stop_type = stop.get("type") or "delivery"
        if stop_type == "pickup":
            return state in (
                "PICKED_UP",
                "IN_TRANSIT",
                "AT_DESTINATION",
                "DELIVERED",
                "POD_COMPLETED",
                "INVOICED",
                "CLOSED",
            )
        return state in ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED")

    def _solve_pd_vrp_from(
        self, nodes: list[_StopNode], cost_matrix: list[list[int]], start_idx: int
    ) -> list[str]:
        pickup_index = {n.order_id: i for i, n in enumerate(nodes) if n.stop_type == "pickup"}
        delivery_index = {n.order_id: i for i, n in enumerate(nodes) if n.stop_type == "delivery"}
        delivery_only_orders = set(delivery_index) - set(pickup_index)

        visited: set[int] = set()
        visited_orders_pickup: set[str] = set()
        route: list[int] = []
        current = start_idx

        while len(visited) < len(nodes):
            if current not in visited:
                visited.add(current)
                route.append(current)
                node = nodes[current]
                if node.stop_type == "pickup":
                    visited_orders_pickup.add(node.order_id)

            best_next: int | None = None
            best_cost = math.inf
            for j in range(len(nodes)):
                if j in visited:
                    continue
                candidate = nodes[j]
                if candidate.stop_type == "delivery" and candidate.order_id not in delivery_only_orders:
                    if candidate.order_id not in visited_orders_pickup:
                        continue
                cost = cost_matrix[current][j]
                if cost < best_cost:
                    best_cost = cost
                    best_next = j
            if best_next is None:
                for j in range(len(nodes)):
                    if j not in visited:
                        best_next = j
                        break
            if best_next is None:
                break
            current = best_next

        route = self._two_opt_improve(route, nodes, cost_matrix, delivery_only_orders)
        return [nodes[i].key for i in route]

    def _build_cost_matrix(self, nodes: list[_StopNode]) -> list[list[int]]:
        n = len(nodes)
        matrix = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                matrix[i][j] = _haversine_m(nodes[i].coords, nodes[j].coords)
        return matrix

    def _solve_pd_vrp(self, nodes: list[_StopNode], cost_matrix: list[list[int]]) -> list[str]:
        pickup_index = {n.order_id: i for i, n in enumerate(nodes) if n.stop_type == "pickup"}
        delivery_index = {n.order_id: i for i, n in enumerate(nodes) if n.stop_type == "delivery"}
        delivery_only_orders = set(delivery_index) - set(pickup_index)

        visited: set[int] = set()
        visited_orders_pickup: set[str] = set()
        route: list[int] = []

        start_candidates = [i for i, n in enumerate(nodes) if n.stop_type == "pickup"]
        if not start_candidates:
            start_candidates = list(range(len(nodes)))
        current = min(start_candidates, key=lambda i: i)

        while len(visited) < len(nodes):
            if current not in visited:
                visited.add(current)
                route.append(current)
                node = nodes[current]
                if node.stop_type == "pickup":
                    visited_orders_pickup.add(node.order_id)

            best_next: int | None = None
            best_cost = math.inf
            for j in range(len(nodes)):
                if j in visited:
                    continue
                candidate = nodes[j]
                if candidate.stop_type == "delivery" and candidate.order_id not in delivery_only_orders:
                    if candidate.order_id not in visited_orders_pickup:
                        continue
                cost = cost_matrix[current][j]
                if cost < best_cost:
                    best_cost = cost
                    best_next = j
            if best_next is None:
                for j in range(len(nodes)):
                    if j in visited:
                        continue
                    candidate = nodes[j]
                    if candidate.stop_type == "delivery" and candidate.order_id not in delivery_only_orders:
                        if candidate.order_id not in visited_orders_pickup:
                            continue
                    best_next = j
                    break
            if best_next is None:
                break
            current = best_next

        route = self._two_opt_improve(route, nodes, cost_matrix, delivery_only_orders)
        return [nodes[i].key for i in route]

    def _two_opt_improve(
        self,
        route: list[int],
        nodes: list[_StopNode],
        cost_matrix: list[list[int]],
        delivery_only_orders: set[str],
        *,
        max_passes: int | None = None,
    ) -> list[int]:
        if len(route) < 4:
            return route
        if max_passes is None:
            max_passes = min(30, max(5, 40 - len(route)))

        def feasible(seq: list[int]) -> bool:
            seen_pickup: set[str] = set()
            for idx in seq:
                node = nodes[idx]
                if node.stop_type == "pickup":
                    seen_pickup.add(node.order_id)
                elif node.stop_type == "delivery" and node.order_id not in delivery_only_orders:
                    if node.order_id not in seen_pickup:
                        return False
            return True

        def tour_cost(seq: list[int]) -> int:
            return sum(cost_matrix[seq[i]][seq[i + 1]] for i in range(len(seq) - 1))

        best = list(route)
        best_cost = tour_cost(best)
        improved = True
        passes = 0
        while improved and passes < max_passes:
            improved = False
            passes += 1
            for i in range(1, len(best) - 2):
                for j in range(i + 1, len(best)):
                    if j - i == 1:
                        continue
                    candidate = best[:i] + best[i:j][::-1] + best[j:]
                    if not feasible(candidate):
                        continue
                    c_cost = tour_cost(candidate)
                    if c_cost < best_cost:
                        best = candidate
                        best_cost = c_cost
                        improved = True
        return best
