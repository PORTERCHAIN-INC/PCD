"""Plan-quality benchmark on seeded Toronto +150 km scenarios (no DB).

Modes per scenario:
- ``manual``: a dispatcher's greedy rule — each order, in order, goes to the vehicle whose
  route grows least when the pickup and drop are appended (capacity respected);
- ``before``: OR-Tools with every vehicle equally costly to open;
- ``after``:  OR-Tools with right-size tie-breaking (current code);
- ``per_km``: as ``after`` with example per-km costs (not the fleet default, which is 0).

Road times/metres come from local Valhalla (``--valhalla``, default when reachable) or a
haversine x1.3 detour at 45 km/h.

    python scripts/plan_quality_bench.py [--haversine]
"""

from __future__ import annotations

import dataclasses
import json
import math
import random
import sys
import urllib.request

from porterchain_api.dispatch_engine import vrp
from porterchain_api.dispatch_engine.stop_shapes import StopSpec

TORONTO = (43.6532, -79.3832)
FLEET = [("sedan", 150, 8, 0.4), ("sedan", 150, 8, 0.4), ("suv", 300, 16, 0.9), ("suv", 300, 16, 0.9),
         ("van", 900, 45, 3.5), ("van", 900, 45, 3.5), ("box_truck", 2500, 140, 14.0)]
RANK = {"sedan": 0, "suv": 1, "van": 2, "box_truck": 3}


def _metres(a: tuple[float, float], b: tuple[float, float]) -> int:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return int(2 * 6_371_000 * math.asin(math.sqrt(h)) * 1.3)


SHORE = [(-79.85, 43.25), (-79.38, 43.63), (-78.85, 43.86), (-78.0, 43.95), (-76.5, 44.1)]  # Lake Ontario, north


def _in_lake(lat: float, lng: float) -> bool:
    if lng < SHORE[0][0] or lat < 43.27:  # west of Hamilton, or the Niagara side
        return False
    for (x0, y0), (x1, y1) in zip(SHORE, SHORE[1:], strict=False):
        if x0 <= lng <= x1:
            return lat < y0 + (y1 - y0) * (lng - x0) / (x1 - x0)
    return False


def _point(rng: random.Random, radius_km: float) -> tuple[float, float]:
    while True:
        r, t = radius_km * math.sqrt(rng.random()), rng.random() * 2 * math.pi
        p = TORONTO[0] + r / 111 * math.sin(t), TORONTO[1] + r / (111 * math.cos(math.radians(43.65))) * math.cos(t)
        if not _in_lake(*p):
            return p


def valhalla(pts: list[tuple[float, float]], url: str = "http://127.0.0.1:8002") -> tuple[list, list] | None:
    """(seconds, metres) matrices from local Valhalla, or None when it is not running."""
    locs = [{"lat": a, "lon": b} for a, b in pts]
    body = json.dumps({"sources": locs, "targets": locs, "costing": "auto"}).encode()
    try:
        req = urllib.request.Request(f"{url}/sources_to_targets", body, {"Content-Type": "application/json"})
        rows = json.load(urllib.request.urlopen(req, timeout=60))["sources_to_targets"]
    except OSError:
        return None
    secs = [[int(c["time"] or 0) if c.get("time") is not None else 99_999 for c in row] for row in rows]
    metres = [[int((c.get("distance") or 0) * 1000) for c in row] for row in rows]
    return secs, metres


def scenario(seed: int, orders: int, radius_km: float, road: bool = True) -> vrp.Problem:
    rng = random.Random(seed)
    stops, pairs = [], []
    for i in range(orders):
        size = rng.choices(["parcel", "medium", "bulky"], [0.6, 0.3, 0.1])[0]
        kg, boxes, m3 = {"parcel": (8, 1, 0.03), "medium": (60, 4, 0.25), "bulky": (400, 12, 1.8)}[size]
        start = rng.choice([None, 3600, 4 * 3600])  # offsets from an 8:00 plan
        end = start + 4 * 3600 if start else None
        pick = _point(rng, 15)  # merchants are mostly in the city
        drop = _point(rng, radius_km)
        stops += [StopSpec(f"o{i}:p0", f"o{i}", "pickup", *pick, kg=kg, boxes=boxes, m3=m3, service_s=300),
                  StopSpec(f"o{i}:d0", f"o{i}", "drop", *drop, kg=kg, boxes=boxes, m3=m3, service_s=420,
                           window_start_s=start, window_end_s=end)]
        pairs.append((f"o{i}:p0", f"o{i}:d0"))
    vehicles = [vrp.Vehicle(id=f"v{k}-{c}", driver_id=None, vehicle_class=c, cap_kg=kg * 0.85,
                            cap_boxes=int(b * 0.85), cap_m3=m * 0.85, start=_point(rng, 10), rank=RANK[c])
                for k, (c, kg, b, m) in enumerate(FLEET)]
    pts = vrp.points(vehicles, stops)
    real = valhalla(pts) if road else None
    if real:
        secs, metres = real
    else:
        metres = [[_metres(a, b) for b in pts] for a in pts]
        secs = [[int(d / 12.5) for d in row] for row in metres]  # 45 km/h
    return vrp.Problem(stops=stops, pairs=pairs, vehicles=vehicles, matrix=secs, metres=metres, time_limit_s=3)


def metrics(ev: dict) -> dict:
    routes = ev["routes"]
    stops = sum(len(r["stops"]) for r in routes) // 2 or 1
    return {
        "km": round(sum(r["metres"] for r in routes) / 1000, 1),
        "minutes": round(sum(r["seconds"] for r in routes) / 60),
        "vehicles": ev["vehicles_used"],
        "classes": sorted(r["vehicle_class"] for r in routes),
        "cost_per_stop_cad": round(ev["cost_cents"] / stops / 100, 2),
        "fill_pct": round(sum(r["fill_pct"] for r in routes) / max(1, len(routes)), 1),
        "late": len(ev["late_stops"]), "dropped": len(ev["dropped"]),
    }


KM_CENTS = {"sedan": 12, "suv": 16, "van": 22, "box_truck": 35}  # example only; fleet default is 0 (gas on driver)


def manual(problem: vrp.Problem) -> dict[str, list[str]]:
    """Greedy dispatcher: append each order to the vehicle whose route grows least."""
    idx, by_key = problem.index(), {s.key: s for s in problem.stops}
    routes: dict[str, list[str]] = {v.id: [] for v in problem.vehicles}
    for p, d in problem.pairs:
        best = None
        for vi, v in enumerate(problem.vehicles):
            trial = {**routes, v.id: [*routes[v.id], p, d]}
            ev = vrp.evaluate(problem, trial)
            if not ev["feasible"]:
                continue
            last = idx[routes[v.id][-1]] if routes[v.id] else vi
            grow = problem.matrix[last][idx[p]] + problem.matrix[idx[p]][idx[d]] + by_key[p].service_s
            grow += 0 if routes[v.id] else v.fixed_s
            if best is None or grow < best[0]:
                best = (grow, v.id)
        if best:
            routes[best[1]] += [p, d]
    return {k: r for k, r in routes.items() if r}


def run(problem: vrp.Problem, mode: str) -> dict:
    if mode == "manual":
        return metrics(vrp.evaluate(problem, manual(problem)))
    if mode == "before":
        problem = dataclasses.replace(problem, vehicles=[dataclasses.replace(v, rank=0) for v in problem.vehicles])
    if mode == "per_km":
        problem = dataclasses.replace(problem, vehicles=[
            dataclasses.replace(v, km_cents=KM_CENTS[v.vehicle_class]) for v in problem.vehicles])
    return metrics(vrp.evaluate(problem, vrp.solve_ortools(problem)))


SCENARIOS = [("today: 4 orders, city", 11, 4, 25), ("busy: 12 orders, GTA", 12, 12, 60),
             ("scale: 30 orders, +150 km", 13, 30, 150)]

if __name__ == "__main__":
    out = []
    for name, seed, n, radius in SCENARIOS:
        p = scenario(seed, n, radius, road="--haversine" not in sys.argv)
        modes = ("manual", "before", "after", "per_km")
        out.append({"scenario": name, "road": "valhalla" if p.metres and "--haversine" not in sys.argv else "haversine",
                    **{mode: run(p, mode) for mode in modes}})
    print(json.dumps(out, indent=2))
