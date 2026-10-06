"""One-van pickup-and-delivery search. Cost is a Valhalla time matrix."""

from __future__ import annotations

from dataclasses import dataclass, field

from porterchain_api.dispatch_engine.capacity import VehicleCapacity, reject_reason

MAX_STOPS = 25
HORIZON_S = 24 * 60 * 60
_DROP_PENALTY = 10_000_000


@dataclass(frozen=True)
class DayStop:
    id: str
    lat: float | None = None
    lng: float | None = None
    service_seconds: int = 0
    window_start_s: int | None = None
    window_end_s: int | None = None


@dataclass(frozen=True)
class DayJob:
    id: str
    pickup_id: str
    dropoff_id: str
    extra_ids: tuple[str, ...] = ()
    kg: float = 0
    volume_m3: float = 0
    pallets: float = 0
    parcels: float = 0
    skill: str | None = None
    locked: bool = False
    picked_up: bool = False


@dataclass
class DayPlan:
    waypoints: list[str]
    unassigned: list[dict[str, str]] = field(default_factory=list)
    label: str = "ortools"
    added_minutes: dict[str, int] = field(default_factory=dict)
    matrix_source: str | None = None


def solve_day(
    *,
    stops: list[DayStop],
    jobs: list[DayJob],
    matrix: list[list[int]] | None,
    matrix_source: str | None,
    on_break: bool = False,
    capacity: VehicleCapacity | None = None,
    vehicle_class: str | None = None,
    current_order: list[str] | None = None,
    time_limit_s: int = 3,
) -> DayPlan:
    """Order one van. A refused search keeps ``current_order``."""
    order = list(current_order) if current_order is not None else [stop.id for stop in stops]
    if on_break:
        return DayPlan(waypoints=order, label="on_break", matrix_source=matrix_source)
    if len(stops) > MAX_STOPS:
        return DayPlan(waypoints=order, label="too_large", matrix_source=matrix_source)
    if matrix_source != "valhalla" or not _matrix_ok(matrix, len(stops)):
        return DayPlan(waypoints=order, label="routing_down", matrix_source=matrix_source)

    assert matrix is not None
    by_id = {stop.id: stop for stop in stops}
    unassigned: list[dict[str, str]] = []
    open_jobs: list[DayJob] = []
    locked_ids: list[str] = []
    for job in jobs:
        if job.locked:
            locked_ids.extend(_job_stop_ids(job))
            continue
        if job.picked_up:
            locked_ids.append(job.pickup_id)
        reason = _prefilter(job, by_id, capacity, vehicle_class)
        if reason:
            unassigned.append({"job_id": job.id, "reason": reason})
            continue
        open_jobs.append(job)

    solved = _ortools(stops, open_jobs, matrix, time_limit_s, locked_ids)
    if solved is not None and not _route_ok(_unique(locked_ids + solved), jobs, stops, matrix, capacity):
        solved = None
    label = "ortools"
    if solved is None:
        solved = _insert(locked_ids, open_jobs, jobs, stops, matrix, capacity)
        label = "insertion"

    placed = _jobs_in_order(solved, open_jobs)
    for job in open_jobs:
        if job.id in placed:
            continue
        unassigned.append({"job_id": job.id, "reason": _why_dropped(job, stops, matrix, capacity)})

    waypoints = _unique(locked_ids + solved)
    return DayPlan(
        waypoints=waypoints,
        unassigned=unassigned,
        label=label,
        added_minutes=_added_minutes(waypoints, stops, matrix),
        matrix_source=matrix_source,
    )


def _job_stop_ids(job: DayJob) -> list[str]:
    return [job.pickup_id, *job.extra_ids, job.dropoff_id]


def _prefilter(
    job: DayJob,
    by_id: dict[str, DayStop],
    capacity: VehicleCapacity | None,
    vehicle_class: str | None,
) -> str | None:
    for stop_id in _job_stop_ids(job):
        stop = by_id.get(stop_id)
        if stop is None or stop.lat is None or stop.lng is None:
            return "no_coords"
    skill = (job.skill or "").strip().lower()
    van = (vehicle_class or "").strip().lower()
    if skill and skill != van:
        return "skill"
    return reject_reason(
        kg=job.kg,
        volume_m3=job.volume_m3,
        pallets=job.pallets,
        parcels=job.parcels,
        capacity=capacity,
    )


def _matrix_ok(matrix: list[list[int]] | None, stop_count: int) -> bool:
    if not matrix or len(matrix) < stop_count + 1:
        return False
    return all(len(row) >= stop_count + 1 for row in matrix)


def _ortools(
    stops: list[DayStop],
    jobs: list[DayJob],
    matrix: list[list[int]],
    time_limit_s: int,
    locked_ids: list[str],
) -> list[str] | None:
    if not jobs:
        return []
    try:
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    except ImportError:
        return None

    index_of = {stop.id: i + 1 for i, stop in enumerate(stops)}
    service = [0] + [max(0, int(stop.service_seconds)) for stop in stops]
    manager = pywrapcp.RoutingIndexManager(len(stops) + 1, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def transit(from_index: int, to_index: int) -> int:
        start = manager.IndexToNode(from_index)
        end = manager.IndexToNode(to_index)
        if end == 0:
            return 0
        return int(matrix[start][end]) + service[start]

    callback = routing.RegisterTransitCallback(transit)
    routing.SetArcCostEvaluatorOfAllVehicles(callback)
    routing.AddDimension(callback, HORIZON_S, HORIZON_S, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for i, stop in enumerate(stops, start=1):
        start_s = 0 if stop.window_start_s is None else int(stop.window_start_s)
        end_s = HORIZON_S if stop.window_end_s is None else int(stop.window_end_s)
        time_dim.CumulVar(manager.NodeToIndex(i)).SetRange(max(0, start_s), max(start_s, end_s))

    for job in jobs:
        nodes = [index_of[stop_id] for stop_id in _job_stop_ids(job)]
        indexes = [manager.NodeToIndex(node) for node in nodes]
        routing.AddPickupAndDelivery(indexes[0], indexes[-1])
        routing.solver().Add(routing.VehicleVar(indexes[0]) == routing.VehicleVar(indexes[-1]))
        routing.solver().Add(time_dim.CumulVar(indexes[0]) <= time_dim.CumulVar(indexes[-1]))
        for extra in indexes[1:-1]:
            routing.solver().Add(routing.VehicleVar(extra) == routing.VehicleVar(indexes[0]))
            routing.solver().Add(time_dim.CumulVar(indexes[0]) <= time_dim.CumulVar(extra))
            routing.solver().Add(time_dim.CumulVar(extra) <= time_dim.CumulVar(indexes[-1]))
        prefix = set(locked_ids)
        for node in indexes:
            if stops[manager.IndexToNode(node) - 1].id in prefix:
                continue
            routing.AddDisjunction([node], _DROP_PENALTY)
            routing.solver().Add(routing.ActiveVar(node) == routing.ActiveVar(indexes[0]))

    index_of_all = {stop.id: manager.NodeToIndex(i + 1) for i, stop in enumerate(stops)}
    chain = [routing.Start(0)] + [index_of_all[stop_id] for stop_id in locked_ids if stop_id in index_of_all]
    for left, right in zip(chain, chain[1:]):
        routing.solver().Add(routing.NextVar(left) == right)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    if time_limit_s > 0:
        params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        params.time_limit.seconds = int(time_limit_s)
    solution = routing.SolveWithParameters(params)
    if solution is None:
        return None
    index = routing.Start(0)
    chosen: list[str] = []
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        if node != 0:
            chosen.append(stops[node - 1].id)
        index = solution.Value(routing.NextVar(index))
    return chosen


def _insert(
    locked_ids: list[str],
    open_jobs: list[DayJob],
    jobs: list[DayJob],
    stops: list[DayStop],
    matrix: list[list[int]],
    capacity: VehicleCapacity | None,
) -> list[str]:
    order = list(locked_ids)
    for job in open_jobs:
        best: list[str] | None = None
        best_cost: int | None = None
        start = len(locked_ids)
        for at in range(start, len(order) + 1):
            trial = order[:at] + _job_stop_ids(job) + order[at:]
            if not _route_ok(trial, jobs, stops, matrix, capacity):
                continue
            cost = _route_seconds(trial, stops, matrix)
            if best_cost is None or cost < best_cost:
                best = trial
                best_cost = cost
        if best is not None:
            order = best
    locked = set(locked_ids)
    return [stop_id for stop_id in order if stop_id not in locked]


def _route_ok(
    order: list[str],
    jobs: list[DayJob],
    stops: list[DayStop],
    matrix: list[list[int]],
    capacity: VehicleCapacity | None,
) -> bool:
    pos = {stop_id: i for i, stop_id in enumerate(order)}
    present = [job for job in jobs if job.pickup_id in pos and job.dropoff_id in pos]
    for job in present:
        if not (pos[job.pickup_id] < pos[job.dropoff_id]):
            return False
        for extra in job.extra_ids:
            if extra not in pos or not (pos[job.pickup_id] < pos[extra] < pos[job.dropoff_id]):
                return False
    if not _load_ok(order, present, capacity):
        return False
    index_of = {stop.id: i + 1 for i, stop in enumerate(stops)}
    return _windows_ok(order, {stop.id: stop for stop in stops}, index_of, matrix)


def _load_ok(order: list[str], jobs: list[DayJob], capacity: VehicleCapacity | None) -> bool:
    caps = capacity or VehicleCapacity()
    by_pickup = {job.pickup_id: job for job in jobs}
    by_drop = {job.dropoff_id: job for job in jobs}
    kg = vol = pal = parcels = 0.0
    for stop_id in order:
        if stop_id in by_pickup:
            job = by_pickup[stop_id]
            kg += job.kg
            vol += job.volume_m3
            pal += job.pallets
            parcels += job.parcels
        if reject_reason(kg=kg, volume_m3=vol, pallets=pal, parcels=parcels, capacity=caps):
            return False
        if stop_id in by_drop:
            job = by_drop[stop_id]
            kg -= job.kg
            vol -= job.volume_m3
            pal -= job.pallets
            parcels -= job.parcels
    return True


def _windows_ok(
    order: list[str],
    by_id: dict[str, DayStop],
    index_of: dict[str, int],
    matrix: list[list[int]],
) -> bool:
    clock = 0
    prev = 0
    for stop_id in order:
        node = index_of[stop_id]
        clock += int(matrix[prev][node])
        stop = by_id[stop_id]
        if stop.window_start_s is not None and clock < stop.window_start_s:
            clock = stop.window_start_s
        if stop.window_end_s is not None and clock > stop.window_end_s:
            return False
        clock += max(0, int(stop.service_seconds))
        prev = node
    return True


def _route_seconds(order: list[str], stops: list[DayStop], matrix: list[list[int]]) -> int:
    by_id = {stop.id: stop for stop in stops}
    index_of = {stop.id: i + 1 for i, stop in enumerate(stops)}
    clock = 0
    prev = 0
    for stop_id in order:
        node = index_of[stop_id]
        clock += int(matrix[prev][node]) + max(0, int(by_id[stop_id].service_seconds))
        prev = node
    return clock


def _why_dropped(
    job: DayJob,
    stops: list[DayStop],
    matrix: list[list[int]],
    capacity: VehicleCapacity | None,
) -> str:
    alone = _job_stop_ids(job)
    if reject_reason(
        kg=job.kg,
        volume_m3=job.volume_m3,
        pallets=job.pallets,
        parcels=job.parcels,
        capacity=capacity,
    ):
        return "capacity"
    if _windows_ok(alone, {stop.id: stop for stop in stops}, {stop.id: i + 1 for i, stop in enumerate(stops)}, matrix):
        return "capacity"
    return "time_window"


def _jobs_in_order(order: list[str], jobs: list[DayJob]) -> set[str]:
    present = set(order)
    return {job.id for job in jobs if job.pickup_id in present and job.dropoff_id in present}


def _unique(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for stop_id in ids:
        if stop_id in seen:
            continue
        seen.add(stop_id)
        out.append(stop_id)
    return out


def _added_minutes(waypoints: list[str], stops: list[DayStop], matrix: list[list[int]]) -> dict[str, int]:
    index_of = {stop.id: i + 1 for i, stop in enumerate(stops)}
    added: dict[str, int] = {}
    prev = 0
    for stop_id in waypoints:
        node = index_of.get(stop_id)
        if node is None:
            continue
        added[stop_id] = max(0, round(int(matrix[prev][node]) / 60))
        prev = node
    return added
