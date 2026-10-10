"""Multi-vehicle pickup-and-delivery routing (OR-Tools default) + re-planning.

Pure: callers pass a seconds matrix over ``[vehicle starts..., stops...]``.
Solvers return ``{vehicle_id: [stop keys]}``; :func:`evaluate` scores any plan the
same way so OR-Tools and cuOpt are compared on identical maths.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from porterchain_api.dispatch_engine.stop_shapes import PICKUP_KINDS, StopSpec

DROP_PENALTY = 1_000_000  # seconds-equivalent; dropping a pair is always worse than driving
HORIZON_S = 14 * 3600


@dataclass
class Vehicle:
    id: str
    driver_id: str | None
    vehicle_class: str
    cap_kg: float
    cap_boxes: int
    start: tuple[float, float]
    hourly_cents: int = 2700
    fixed_s: int = 1800  # discourages opening another vehicle for a tiny gain
    max_route_s: int = 10 * 3600
    onboard_kg: float = 0.0  # re-plan: already loaded (pickup done)
    onboard_boxes: int = 0
    must_deliver: list[str] = field(default_factory=list)  # re-plan: drop keys locked to this vehicle


@dataclass
class Problem:
    stops: list[StopSpec]
    pairs: list[tuple[str, str]]
    vehicles: list[Vehicle]
    matrix: list[list[int]]  # (V+S)x(V+S) seconds, vehicles first
    time_limit_s: int = 5

    def index(self) -> dict[str, int]:
        v = len(self.vehicles)
        return {s.key: v + i for i, s in enumerate(self.stops)}


def points(problem_vehicles: list[Vehicle], stops: list[StopSpec]) -> list[tuple[float, float]]:
    return [v.start for v in problem_vehicles] + [(s.lat, s.lng) for s in stops]


# ---------------------------------------------------------------- evaluation
def evaluate(problem: Problem, routes: dict[str, list[str]]) -> dict[str, Any]:
    """Score a plan: feasibility, seconds, peak fill, cost; dropped pairs counted."""
    idx = problem.index()
    by_key = {s.key: s for s in problem.stops}
    pair_of = {d: p for p, d in problem.pairs}
    served: set[str] = set()
    out_routes: list[dict[str, Any]] = []
    total_cost = 0
    violations: list[str] = []
    for vi, veh in enumerate(problem.vehicles):
        keys = [k for k in routes.get(veh.id, []) if k in by_key]
        if not keys and not veh.must_deliver:
            continue
        seconds, at = 0, vi
        kg, boxes = veh.onboard_kg, veh.onboard_boxes
        peak_kg, peak_boxes = kg, boxes
        seen: set[str] = set()
        seq: list[dict[str, Any]] = []
        for k in keys:
            s = by_key[k]
            seconds += problem.matrix[at][idx[k]] + s.service_s
            at = idx[k]
            if s.kind in PICKUP_KINDS:
                kg += s.kg
                boxes += s.boxes
            else:
                p = pair_of.get(k)
                if p and p not in seen and p in by_key and k not in veh.must_deliver:
                    violations.append(f"{veh.id}: drop before pickup {k}")
                kg -= s.kg
                boxes -= s.boxes
            peak_kg, peak_boxes = max(peak_kg, kg), max(peak_boxes, boxes)
            seen.add(k)
            seq.append({"key": k, "order_id": s.order_id, "kind": s.kind, "fsa": s.fsa, "eta_s": seconds})
        for d in veh.must_deliver:
            if d not in seen:
                violations.append(f"{veh.id}: onboard drop {d} missing")
        if peak_kg > veh.cap_kg + 1e-6 or peak_boxes > veh.cap_boxes:
            violations.append(f"{veh.id}: over capacity")
        if seconds > veh.max_route_s:
            violations.append(f"{veh.id}: route too long")
        fill = max(peak_kg / veh.cap_kg if veh.cap_kg else 0, peak_boxes / veh.cap_boxes if veh.cap_boxes else 0)
        cost = int(round(seconds / 3600 * veh.hourly_cents))
        total_cost += cost
        served |= seen
        out_routes.append({
            "vehicle_id": veh.id, "driver_id": veh.driver_id, "vehicle_class": veh.vehicle_class,
            "stops": seq, "seconds": seconds, "fill_pct": round(fill * 100, 1),
            "peak_kg": round(peak_kg, 1), "peak_boxes": peak_boxes, "cost_cents": cost,
        })
    dropped = [p for p, d in problem.pairs if p not in served or d not in served]
    return {
        "routes": out_routes,
        "dropped": dropped,
        "cost_cents": total_cost,
        "vehicles_used": len(out_routes),
        "feasible": not violations,
        "violations": violations,
        "score": (len(dropped), 0 if not violations else 1, total_cost),
    }


def better(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """True when plan ``a`` beats ``b``: feasible, fewer dropped pairs, then lower cost."""
    ka = (0 if a.get("feasible") else 1, len(a.get("dropped", [])), a.get("cost_cents", 0))
    kb = (0 if b.get("feasible") else 1, len(b.get("dropped", [])), b.get("cost_cents", 0))
    return ka < kb


# ---------------------------------------------------------------- OR-Tools
def solve_ortools(problem: Problem) -> dict[str, list[str]]:
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2

    v = len(problem.vehicles)
    s = len(problem.stops)
    if v == 0 or s == 0:
        return {}
    # node 0 = free end depot; 1..v vehicle starts; v+1.. stops
    n = 1 + v + s

    def m(a: int, b: int) -> int:
        if a == 0 or b == 0:
            return 0
        return int(problem.matrix[a - 1][b - 1])

    service = [0] * n
    for i, st in enumerate(problem.stops):
        service[1 + v + i] = st.service_s
    starts = [1 + i for i in range(v)]
    manager = pywrapcp.RoutingIndexManager(n, v, starts, [0] * v)
    routing = pywrapcp.RoutingModel(manager)

    def transit(i: int, j: int) -> int:
        a, b = manager.IndexToNode(i), manager.IndexToNode(j)
        return m(a, b) + service[a]

    cb = routing.RegisterTransitCallback(transit)
    routing.SetArcCostEvaluatorOfAllVehicles(cb)
    for k, veh in enumerate(problem.vehicles):
        routing.SetFixedCostOfVehicle(int(veh.fixed_s), k)
    routing.AddDimensionWithVehicleCapacity(
        cb, HORIZON_S, [int(veh.max_route_s) for veh in problem.vehicles], True, "Time"
    )
    time_dim = routing.GetDimensionOrDie("Time")

    node_of = {st.key: 1 + v + i for i, st in enumerate(problem.stops)}
    for i, st in enumerate(problem.stops):
        if st.window_start_s is not None or st.window_end_s is not None:
            lo = max(0, st.window_start_s or 0)
            hi = min(HORIZON_S, st.window_end_s if st.window_end_s is not None else HORIZON_S)
            if lo <= hi:
                time_dim.CumulVar(manager.NodeToIndex(1 + v + i)).SetRange(lo, hi)

    for name, attr, cap_attr, onboard_attr, scale in (
        ("kg", "kg", "cap_kg", "onboard_kg", 10),
        ("boxes", "boxes", "cap_boxes", "onboard_boxes", 1),
    ):
        demand = [0] * n
        for i, st in enumerate(problem.stops):
            q = int(math.ceil(getattr(st, attr) * scale))
            demand[1 + v + i] = q if st.kind in PICKUP_KINDS else -q
        # Onboard load leaves at the vehicle start node.
        dcb = routing.RegisterUnaryTransitCallback(lambda i, d=demand: d[manager.IndexToNode(i)])
        caps = [int(getattr(veh, cap_attr) * scale) for veh in problem.vehicles]
        routing.AddDimensionWithVehicleCapacity(dcb, 0, caps, False, name)
        dim = routing.GetDimensionOrDie(name)
        for k, veh in enumerate(problem.vehicles):
            load = int(math.ceil(getattr(veh, onboard_attr) * scale))
            dim.CumulVar(routing.Start(k)).SetRange(load, load)

    solver = routing.solver()
    for p, d in problem.pairs:
        pi, di = manager.NodeToIndex(node_of[p]), manager.NodeToIndex(node_of[d])
        routing.AddPickupAndDelivery(pi, di)
        solver.Add(routing.VehicleVar(pi) == routing.VehicleVar(di))
        solver.Add(time_dim.CumulVar(pi) <= time_dim.CumulVar(di))
        routing.AddDisjunction([pi], DROP_PENALTY)
        routing.AddDisjunction([di], DROP_PENALTY)
    paired = {k for pr in problem.pairs for k in pr}
    for k, veh in enumerate(problem.vehicles):
        for d in veh.must_deliver:
            if d in node_of:
                di = manager.NodeToIndex(node_of[d])
                routing.VehicleVar(di).SetValues([-1, k])
                if d not in paired:
                    routing.AddDisjunction([di], DROP_PENALTY * 10)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromSeconds(max(1, int(problem.time_limit_s)))
    sol = routing.SolveWithParameters(params)
    if sol is None:
        return {}
    out: dict[str, list[str]] = {}
    key_of = {node: key for key, node in node_of.items()}
    for k, veh in enumerate(problem.vehicles):
        idx = routing.Start(k)
        keys: list[str] = []
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node in key_of:
                keys.append(key_of[node])
            idx = sol.Value(routing.NextVar(idx))
        if keys:
            out[veh.id] = keys
    return out


def replan_problem(
    problem: Problem,
    routes: dict[str, list[str]],
    done_keys: set[str],
    positions: dict[str, tuple[float, float]],
) -> Problem:
    """Re-plan mid-day from the committed ``routes``.

    Finished stops leave the problem. A pair whose pickup is done but drop is not stays
    on the vehicle that loaded it (``must_deliver`` + onboard load). Vehicles restart at
    their live ``positions``. The caller rebuilds the matrix for the returned problem.
    """
    by_key = {s.key: s for s in problem.stops}
    vehicles: list[Vehicle] = []
    locked: set[str] = set()
    for veh in problem.vehicles:
        nv = Vehicle(**{**veh.__dict__, "start": positions.get(veh.id, veh.start), "must_deliver": [],
                        "onboard_kg": 0.0, "onboard_boxes": 0})
        route = routes.get(veh.id, [])
        for p, d in problem.pairs:
            if p in done_keys and d not in done_keys and p in route:
                nv.must_deliver.append(d)
                nv.onboard_kg += by_key[d].kg
                nv.onboard_boxes += by_key[d].boxes
                locked.add(d)
        vehicles.append(nv)
    stops = [s for s in problem.stops if s.key not in done_keys]
    pairs = [(p, d) for p, d in problem.pairs if p not in done_keys]
    return Problem(stops=stops, pairs=pairs, vehicles=vehicles, matrix=[], time_limit_s=problem.time_limit_s)
