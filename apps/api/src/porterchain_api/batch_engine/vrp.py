"""Smart routing: multi-vehicle VRP, free/self-hosted only.

Per plan (doc 84 F8): self-hosted VROOM (`VROOM_URL`, vroom-express configured with `router: valhalla`)
over self-hosted Valhalla (`VALHALLA_BASE_URL`) on OpenStreetMap. Fallback / tests: built-in
cheapest-insertion + relocate heuristic below, using a Valhalla sources_to_targets matrix when reachable,
else haversine at city speed. Handles capacity (kg, boxes, vehicle type), time windows, shift length,
pickup-and-delivery pairs (incl. driver handovers), same-building grouping, service time by stop type,
time-of-day travel factors, waves, live re-optimisation, and reports saved time vs naive order.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any

SPEED_KMH = {"car": 30.0, "suv": 30.0, "cargo_van": 27.0, "box_truck": 22.0}
SERVICE_S = {"parcel": 90, "building_base": 180, "building_per_parcel": 30, "pharmacy": 120, "signature": 60,
             "id_check": 60, "dolly": 300, "house": 180, "shop": 300, "warehouse": 900, "storage": 1200,
             "driver": 300, "depot": 600}
RELOAD_S = 900
ROAD_FACTOR = 1.35  # haversine -> street distance (Toronto grid)


def tod_factor(t_s: float) -> float:
    """Toronto time-of-day multiplier on travel time (seconds since local midnight)."""
    h = (t_s // 3600) % 24
    if 7 <= h < 10:
        return 1.35
    if 15 <= h < 19:
        return 1.45
    if h >= 22 or h < 5:
        return 0.85
    return 1.0


def _hav_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6_371_000 * 2 * math.asin(min(1.0, math.sqrt(h)))


@dataclass
class Vehicle:
    id: str
    type: str = "cargo_van"
    cap_kg: float = 1200
    cap_boxes: int = 150
    start: tuple[float, float] = (43.6532, -79.3832)
    end: tuple[float, float] | None = None  # None -> return to start
    shift_start_s: float = 8 * 3600
    shift_s: float = 9 * 3600
    driver_id: str | None = None


@dataclass
class Job:
    id: str
    loc: tuple[float, float]
    kg: float = 0
    boxes: int = 1
    kind: str = "delivery"  # delivery | pickup
    stop_type: str = "parcel"
    handling: list[str] = field(default_factory=list)
    tw: tuple[float, float] | None = None
    pair: str | None = None  # delivery -> its pickup job id (same vehicle, pickup first)
    building_key: str | None = None
    parcels: list[str] = field(default_factory=list)
    allowed_types: list[str] | None = None
    service_s: float | None = None


def service_time(j: Job) -> float:
    if j.service_s is not None:
        return j.service_s
    if j.kind == "pickup":
        base = SERVICE_S.get(j.stop_type, SERVICE_S["house"])
    elif len(j.parcels) > 1:
        base = SERVICE_S["building_base"] + SERVICE_S["building_per_parcel"] * len(j.parcels)
    else:
        base = SERVICE_S["parcel"]
    return base + sum(SERVICE_S.get(h, 0) for h in set(j.handling) if h in ("pharmacy", "signature", "id_check", "dolly"))


def group_building(jobs: list[Job]) -> list[Job]:
    """Same-building deliveries become one stop (summed load; service time scales per parcel)."""
    out: list[Job] = []
    by: dict[str, Job] = {}
    for j in jobs:
        if j.kind != "delivery" or not j.building_key or j.pair:
            out.append(j)
            continue
        g = by.get(j.building_key)
        if g is None:
            g = replace(j, id=f"bld:{j.building_key}", parcels=list(j.parcels or [j.id]), handling=list(j.handling))
            by[j.building_key] = g
            out.append(g)
        else:
            g.kg += j.kg
            g.boxes += j.boxes
            g.parcels += j.parcels or [j.id]
            g.handling = sorted(set(g.handling) | set(j.handling))
            if j.tw:
                g.tw = (max(g.tw[0], j.tw[0]), min(g.tw[1], j.tw[1])) if g.tw else j.tw
    return out


class Travel:
    """Travel seconds between points; optional road matrix (seconds) keyed by point index."""

    def __init__(self, matrix: dict[tuple[tuple[float, float], tuple[float, float]], float] | None = None):
        self.matrix = matrix or {}

    def __call__(self, a: tuple[float, float], b: tuple[float, float], t_s: float, vtype: str) -> float:
        if a == b:
            return 0.0
        base = self.matrix.get((a, b))
        if base is None:
            base = _hav_m(a, b) * ROAD_FACTOR / (SPEED_KMH.get(vtype, 27.0) / 3.6)
        return base * tod_factor(t_s)


def _simulate(v: Vehicle, seq: list[Job], travel: Travel, t0: float | None = None,
              pos: tuple[float, float] | None = None, onboard: tuple[float, int] | None = None,
              check_end: bool = True) -> dict[str, Any] | None:
    """Return the timed schedule, or None if infeasible (capacity, TW, shift, precedence, vehicle type)."""
    t = v.shift_start_s if t0 is None else t0
    at = pos or v.start
    seen: set[str] = set()
    # load at departure: deliveries without an on-route pickup are loaded at the start
    kg = sum(j.kg for j in seq if j.kind == "delivery" and not (j.pair and any(p.id == j.pair for p in seq)))
    bx = sum(j.boxes for j in seq if j.kind == "delivery" and not (j.pair and any(p.id == j.pair for p in seq)))
    if onboard:
        kg, bx = kg + onboard[0], bx + onboard[1]
    if kg > v.cap_kg + 1e-9 or bx > v.cap_boxes:
        return None
    stops = []
    for j in seq:
        if j.allowed_types and v.type not in j.allowed_types:
            return None
        if j.kind == "delivery" and j.pair and j.pair not in seen and any(p.id == j.pair for p in seq):
            return None
        t += travel(at, j.loc, t, v.type)
        arrive = t
        if j.tw:
            if t > j.tw[1]:
                return None
            t = max(t, j.tw[0])
        t += service_time(j)
        if j.kind == "pickup":
            kg, bx = kg + j.kg, bx + j.boxes
        else:
            kg, bx = kg - j.kg, bx - j.boxes
        if kg > v.cap_kg + 1e-9 or bx > v.cap_boxes:
            return None
        seen.add(j.id)
        at = j.loc
        stops.append({"job_id": j.id, "arrive_s": round(arrive), "depart_s": round(t), "parcels": j.parcels or [j.id],
                      "kind": j.kind, "building_key": j.building_key})
    t += travel(at, v.end or v.start, t, v.type)
    if check_end and t > v.shift_start_s + v.shift_s:
        return None
    return {"stops": stops, "end_s": t, "duration_s": t - (v.shift_start_s if t0 is None else t0)}


def _insert_all(vehicles: list[Vehicle], jobs: list[Job], travel: Travel, starts: dict[str, dict[str, Any]]
                ) -> tuple[dict[str, list[Job]], list[Job]]:
    routes: dict[str, list[Job]] = {v.id: [] for v in vehicles}
    cost = {v.id: 0.0 for v in vehicles}
    by_id = {j.id: j for j in jobs}
    singles = [j for j in jobs if not (j.kind == "delivery" and j.pair in by_id)]
    singles.sort(key=lambda j: ((j.tw[1] - j.tw[0]) if j.tw else 1e9, -_hav_m(vehicles[0].start, j.loc)))
    pending: list[Job] = []
    for j in singles:  # each pickup is followed by its paired deliveries
        pending.append(j)
        pending += [d for d in jobs if d.kind == "delivery" and d.pair == j.id]
    unassigned: list[Job] = []
    vmap = {v.id: v for v in vehicles}
    where: dict[str, str] = {}

    def sim(vid: str, seq: list[Job]):
        st = starts.get(vid, {})
        return _simulate(vmap[vid], seq, travel, st.get("t0"), st.get("pos"), st.get("onboard"))

    lost: set[str] = set()
    for j in pending:
        if j.pair in by_id and j.kind == "delivery":
            if j.pair in lost or j.pair not in where:
                unassigned.append(j)
                continue
            cands = [where[j.pair]]
        else:
            cands = list(routes)
        best = None
        for vid in cands:
            seq = routes[vid]
            lo = (next(i for i, x in enumerate(seq) if x.id == j.pair) + 1) if j.pair in by_id and j.kind == "delivery" else 0
            for i in range(lo, len(seq) + 1):
                cand = seq[:i] + [j] + seq[i:]
                r = sim(vid, cand)
                if r and (best is None or r["duration_s"] - cost[vid] < best[0]):
                    best = (r["duration_s"] - cost[vid], vid, cand, r)
        if best is None:
            unassigned.append(j)
            lost.add(j.id)
            continue
        _, vid, seq, r = best
        routes[vid] = seq
        cost[vid] = r["duration_s"]
        where[j.id] = vid
    # relocate improvement (single job, keeps pairs feasible via _simulate)
    improved, rounds = True, 0
    while improved and rounds < 3:
        improved, rounds = False, rounds + 1
        for vid in list(routes):
            seq = routes[vid]
            for a in range(len(seq)):
                for b in range(len(seq)):
                    if a == b:
                        continue
                    c = seq[:a] + seq[a + 1:]
                    c = c[:b] + [seq[a]] + c[b:]
                    r = sim(vid, c)
                    if r and r["duration_s"] + 1 < cost[vid]:
                        routes[vid], cost[vid], seq, improved = c, r["duration_s"], c, True
    return routes, unassigned


def solve(vehicles: list[Vehicle], jobs: list[Job], *, travel: Travel | None = None, max_waves: int = 4,
          group: bool = True, starts: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    travel = travel or Travel()
    if not vehicles:
        raise ValueError("vehicles_required")
    work = group_building(jobs) if group else list(jobs)
    out_routes: list[dict[str, Any]] = []
    fleet = [replace(v) for v in vehicles]
    starts = dict(starts or {})
    wave = 1
    while work and fleet and wave <= max_waves:
        routes, left = _insert_all(fleet, work, travel, starts)
        used = 0
        next_fleet = []
        for v in fleet:
            seq = routes[v.id]
            st = starts.get(v.id, {})
            r = _simulate(v, seq, travel, st.get("t0"), st.get("pos"), st.get("onboard")) if seq else None
            if r:
                used += 1
                deliveries = [s for s in r["stops"] if s["kind"] == "delivery"]
                load = [p for s in reversed(deliveries) for p in s["parcels"]]
                out_routes.append({"vehicle_id": v.id, "driver_id": v.driver_id, "vehicle_type": v.type, "wave": wave,
                                   "stops": r["stops"], "duration_s": round(r["duration_s"]),
                                   "load_order": load})  # first loaded = last delivered
                remaining = v.shift_start_s + v.shift_s - r["end_s"] - RELOAD_S
                if remaining > 1800:
                    next_fleet.append(replace(v, shift_start_s=r["end_s"] + RELOAD_S, shift_s=remaining))
            else:
                next_fleet.append(v)
        if not used:
            break
        work, fleet, starts, wave = left, next_fleet, {}, wave + 1
    total = sum(r["duration_s"] for r in out_routes)
    naive = naive_duration(vehicles, jobs, travel)
    return {"routes": out_routes, "unassigned": [j.id for j in work], "waves": max((r["wave"] for r in out_routes), default=0),
            "total_s": total, "naive_s": naive, "saved_s": max(0, naive - total),
            "saved_pct": round(100 * max(0, naive - total) / naive, 1) if naive else 0.0, "solver": "builtin"}


def naive_duration(vehicles: list[Vehicle], jobs: list[Job], travel: Travel) -> int:
    """Input (CSV) order, no grouping, filled vehicle by vehicle up to capacity, ignoring windows."""
    v0 = vehicles[0]
    total, i = 0.0, 0
    order = [j for j in jobs]
    while i < len(order):
        kg = bx = 0
        chunk: list[Job] = []
        while i < len(order) and kg + order[i].kg <= v0.cap_kg and bx + order[i].boxes <= v0.cap_boxes:
            chunk.append(order[i])
            kg += order[i].kg
            bx += order[i].boxes
            i += 1
        if not chunk:
            i += 1
            continue
        t, at = v0.shift_start_s, v0.start
        for j in chunk:
            t += travel(at, j.loc, t, v0.type)
            if j.tw:
                t = max(t, j.tw[0])
            t += service_time(replace(j, parcels=[j.id]))
            at = j.loc
        t += travel(at, v0.start, t, v0.type)
        total += t - v0.shift_start_s
    return round(total)


def reoptimise(vehicles: list[Vehicle], jobs: list[Job], event: dict[str, Any], *,
               positions: dict[str, dict[str, Any]] | None = None, travel: Travel | None = None) -> dict[str, Any]:
    """Live re-plan of the remaining work. Events:
    new_order {job}, failed_stop {job_id, reattempt: bool}, handover {pickup: Job, deliveries: [Job]},
    delay {vehicle_id, seconds}. `positions` gives each vehicle's current {pos, t0, onboard}."""
    starts = {k: dict(v) for k, v in (positions or {}).items()}
    jobs = list(jobs)
    kind = event.get("type")
    if kind == "new_order":
        jobs.append(event["job"])
    elif kind == "failed_stop":
        failed = next((j for j in jobs if j.id == event["job_id"]), None)
        jobs = [j for j in jobs if j.id != event["job_id"]]
        if failed and event.get("reattempt"):
            late = (failed.tw[1] if failed.tw else 0) + 0
            jobs.append(replace(failed, id=failed.id + ":re", tw=(max(late, 15 * 3600), 21 * 3600)))
    elif kind == "handover":
        jobs.append(event["pickup"])
        jobs += event["deliveries"]
    elif kind == "delay":
        st = starts.setdefault(event["vehicle_id"], {})
        base = st.get("t0") or next(v.shift_start_s for v in vehicles if v.id == event["vehicle_id"])
        st["t0"] = base + float(event["seconds"])
    else:
        raise ValueError("unknown_event")
    out = solve(vehicles, jobs, travel=travel, starts=starts)
    out["event"] = kind
    return out


def vroom_problem(vehicles: list[Vehicle], jobs: list[Job]) -> dict[str, Any]:
    """VROOM JSON (lon,lat order). Amounts = [kg*10, boxes]. Pairs become shipments."""
    def ll(p):
        return [p[1], p[0]]
    idx = {j.id: i + 1 for i, j in enumerate(jobs)}
    ves = [{"id": i + 1, "description": v.id, "profile": _COSTING.get(v.type, "auto"), "start": ll(v.start), "end": ll(v.end or v.start),
            "capacity": [int(v.cap_kg * 10), v.cap_boxes],
            "time_window": [int(v.shift_start_s), int(v.shift_start_s + v.shift_s)],
            "skills": [_SKILL[v.type]]} for i, v in enumerate(vehicles)]
    paired = {j.pair for j in jobs if j.pair} | {j.id for j in jobs if j.pair}
    out_jobs, ships = [], []
    for j in jobs:
        if j.id in paired:
            continue
        d = {"id": idx[j.id], "description": j.id, "location": ll(j.loc), "service": int(service_time(j)),
             ("pickup" if j.kind == "pickup" else "delivery"): [int(j.kg * 10), j.boxes]}
        if j.tw:
            d["time_windows"] = [[int(j.tw[0]), int(j.tw[1])]]
        if j.allowed_types:
            d["skills"] = [_SKILL[t] for t in j.allowed_types][:1]
        out_jobs.append(d)
    for d in (j for j in jobs if j.pair):
        p = next(x for x in jobs if x.id == d.pair)
        ships.append({"amount": [int(d.kg * 10), d.boxes],
                      "pickup": {"id": idx[p.id], "description": p.id, "location": ll(p.loc), "service": int(service_time(p))},
                      "delivery": {"id": idx[d.id], "description": d.id, "location": ll(d.loc), "service": int(service_time(d)),
                                   **({"time_windows": [[int(d.tw[0]), int(d.tw[1])]]} if d.tw else {})}})
    return {"vehicles": ves, "jobs": out_jobs, "shipments": ships}


_COSTING = {"car": "auto", "suv": "auto", "cargo_van": "truck", "box_truck": "truck"}


def valhalla_travel(points: list[tuple[float, float]], valhalla_url: str, *, vtype: str = "cargo_van",
                    http: Any = None) -> Travel | None:
    """Road-time matrix from self-hosted Valhalla `/sources_to_targets`; None if unreachable."""
    if not valhalla_url or len(points) < 2:
        return None
    try:
        import httpx
        client = http or httpx
        locs = [{"lat": p[0], "lon": p[1]} for p in points]
        resp = client.post(valhalla_url.rstrip("/") + "/sources_to_targets",
                           json={"sources": locs, "targets": locs, "costing": _COSTING.get(vtype, "auto")}, timeout=30)
        rows = resp.json()["sources_to_targets"]
        m = {(points[i], points[j]): float(c["time"]) for i, row in enumerate(rows) for j, c in enumerate(row)
             if c.get("time") is not None}
        return Travel(m)
    except Exception:  # noqa: BLE001 - routing engine down -> haversine fallback
        return None


_SKILL = {"car": 1, "suv": 2, "cargo_van": 3, "box_truck": 4}


def with_matrix(problem: dict[str, Any], travel: Travel, vehicles: list[Vehicle]) -> dict[str, Any]:
    """Give VROOM our own Valhalla matrix (one call, unroutable pairs fall back to the road-factor estimate)
    instead of letting vroom-express query Valhalla, which fails the whole solve on one unroutable stop."""
    locs: list[list[float]] = []
    seen: dict[tuple[float, float], int] = {}

    def ix(ll: list[float]) -> int:
        k = (ll[0], ll[1])
        if k not in seen:
            seen[k] = len(locs)
            locs.append(ll)
        return seen[k]
    for v in problem["vehicles"]:
        v["start_index"], v["end_index"] = ix(v.pop("start")), ix(v.pop("end"))
    for j in problem["jobs"]:
        j["location_index"] = ix(j.pop("location"))
    for sh in problem["shipments"]:
        for side in ("pickup", "delivery"):
            sh[side]["location_index"] = ix(sh[side].pop("location"))
    mats = {}
    for v, pv in zip(vehicles, problem["vehicles"]):
        prof = pv["profile"]
        if prof in mats:
            continue
        mats[prof] = {"durations": [[int(travel((a[1], a[0]), (b[1], b[0]), v.shift_start_s, v.type)) for b in locs]
                                    for a in locs]}
    return {**problem, "matrices": mats}


def solve_best(vehicles: list[Vehicle], jobs: list[Job], *, vroom_url: str = "", http: Any = None,
               travel: Travel | None = None, valhalla_url: str = "") -> dict[str, Any]:
    """VROOM when configured and reachable; otherwise the built-in solver on a Valhalla matrix. Never a paid API."""
    if travel is None and valhalla_url:
        pts = sorted({*(v.start for v in vehicles), *(j.loc for j in jobs)})
        travel = valhalla_travel(pts, valhalla_url, vtype=vehicles[0].type if vehicles else "cargo_van", http=http)
    if vroom_url:
        try:
            import httpx
            client = http or httpx
            grouped = group_building(jobs)
            prob = vroom_problem(vehicles, grouped)
            if travel is not None and travel.matrix:
                prob = with_matrix(prob, travel, vehicles)
            resp = client.post(vroom_url.rstrip("/") + "/", json=prob, timeout=30)
            data = resp.json()
            if data.get("code") == 0:
                base = solve(vehicles, jobs, travel=travel)  # naive + fallback numbers for comparison
                routes = [{"vehicle_id": vehicles[r["vehicle"] - 1].id, "wave": 1, "duration_s": r["duration"],
                           "stops": [{"job_id": s.get("description"), "arrive_s": s.get("arrival")}
                                     for s in r["steps"] if s["type"] in ("job", "pickup", "delivery")]}
                          for r in data.get("routes", [])]
                total = sum(r["duration_s"] for r in routes)
                return {**base, "routes": routes, "total_s": total, "saved_s": max(0, base["naive_s"] - total),
                        "unassigned": [u.get("description") for u in data.get("unassigned", [])], "solver": "vroom"}
        except Exception:  # noqa: BLE001 - unreachable solver -> built-in
            pass
    return solve(vehicles, jobs, travel=travel)
