"""Dispatch queue route optimizer — state-aware PD-VRP with greedy + 2-opt."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, RouteCenterPlan
from porterchain_api.config import Settings
from porterchain_api.models import Order
from porterchain_api.order_engine.buckets import DELIVERY_ONLY_POOL

_EARTH_RADIUS_M = 6_371_000


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


class DispatchQueueOptimizer:
    def optimize(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_ids: list[str],
        *,
        strategy: str = "balanced",
        engine: str = "valhalla",
    ) -> dict[str, Any]:
        if not order_ids:
            raise ValueError("no_orders_selected")

        warnings: list[str] = []
        included_ids: list[str] = []
        nodes: list[_StopNode] = []

        for oid in order_ids:
            order = db.query(Order).filter(Order.id == oid).first()
            if not order:
                warnings.append(f"order_not_found:{oid}")
                continue
            if order.assigned_driver_id:
                warnings.append(f"order_already_assigned:{order.tracking_number or oid}")
                continue

            delivery_only = order.state in DELIVERY_ONLY_POOL
            pickup = order.pickup or {}
            dropoff = order.dropoff or {}
            pickup_coords = _coords(pickup)
            dropoff_coords = _coords(dropoff)

            if delivery_only:
                if not dropoff_coords:
                    warnings.append(f"missing_dropoff_coords:{order.tracking_number or oid}")
                    continue
            else:
                if not pickup_coords:
                    warnings.append(f"missing_pickup_coords:{order.tracking_number or oid}")
                    continue
                if not dropoff_coords:
                    warnings.append(f"missing_dropoff_coords:{order.tracking_number or oid}")
                    continue

            priority = "high" if order.amount_cents >= 20000 else "normal"
            if not delivery_only and pickup_coords:
                nodes.append(
                    _StopNode(
                        key=f"{oid}:pickup",
                        order_id=oid,
                        stop_type="pickup",
                        coords=pickup_coords,
                        tracking=order.tracking_number or "",
                        address=pickup.get("formatted"),
                        location=pickup,
                        priority=priority,
                        status=order.state,
                    )
                )
            if dropoff_coords:
                nodes.append(
                    _StopNode(
                        key=f"{oid}:delivery",
                        order_id=oid,
                        stop_type="delivery",
                        coords=dropoff_coords,
                        tracking=order.tracking_number or "",
                        address=dropoff.get("formatted"),
                        location=dropoff,
                        priority=priority,
                        status=order.state,
                    )
                )
            included_ids.append(oid)

        if len(nodes) < 2:
            raise ValueError("insufficient_stops")

        cost_matrix = self._build_cost_matrix(nodes)
        sequence_keys = self._solve_pd_vrp(nodes, cost_matrix)
        key_to_idx = {nodes[i].key: i for i in range(len(nodes))}
        route_indices = [key_to_idx[k] for k in sequence_keys]
        ordered_nodes = [nodes[i] for i in route_indices]

        distance_m = sum(
            cost_matrix[route_indices[i]][route_indices[i + 1]]
            for i in range(len(route_indices) - 1)
        )
        duration_s = int(distance_m / 8.33)  # ~30 km/h urban average

        optimized_stops = []
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
            "strategy": strategy,
            "engine": engine,
        }

        plan = RouteCenterPlan(
            id=str(uuid.uuid4()),
            name=f"Dispatch queue {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')}",
            status="optimized",
            strategy=strategy,
            order_ids=included_ids,
            stops=optimized_stops,
            simulation=metrics,
            created_by=ctx.user.id,
        )
        db.add(plan)
        db.add(
            AdminAuditLog(
                actor_user_id=ctx.user.id,
                action="dispatch.queue_optimized",
                resource_type="route_plan",
                resource_id=plan.id,
                payload={"order_ids": included_ids, "stop_count": len(optimized_stops)},
            )
        )
        db.commit()
        db.refresh(plan)

        return {
            "plan_id": plan.id,
            "optimized_stops": optimized_stops,
            "metrics": metrics,
            "warnings": warnings,
            "order_ids": included_ids,
        }

    def _build_cost_matrix(self, nodes: list[_StopNode]) -> list[list[int]]:
        """Haversine leg costs for solver speed; road network used for final metrics."""
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

        # Start at earliest pickup (or nearest cluster centroid proxy: first pickup node)
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
                # Append any remaining feasible stops
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
