"""Optional NVIDIA cuOpt (open source, self-hosted server) — second VRP solver.

Behind ``PORTERCHAIN_DISPATCH_CUOPT_ENABLED``. Payload is numbers only (seconds matrix,
demands, capacities, pair indices) — no names, phones, emails or addresses.
Any error returns ``None`` so OR-Tools stays the answer.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Any

import httpx

from porterchain_api.dispatch_engine.stop_shapes import PICKUP_KINDS
from porterchain_api.dispatch_engine.vrp import HORIZON_S, Problem

logger = logging.getLogger(__name__)


def build_payload(problem: Problem) -> dict[str, Any]:
    """cuOpt server request. Location 0 = free end depot, 1..V starts, V+1.. stops."""
    v, s = len(problem.vehicles), len(problem.stops)
    n = 1 + v + s
    matrix = [[0 if (a == 0 or b == 0) else int(problem.matrix[a - 1][b - 1]) for b in range(n)] for a in range(n)]
    task_of = {st.key: i for i, st in enumerate(problem.stops)}
    kg = [int(math.ceil(st.kg * 10)) * (1 if st.kind in PICKUP_KINDS else -1) for st in problem.stops]
    boxes = [st.boxes * (1 if st.kind in PICKUP_KINDS else -1) for st in problem.stops]
    litres = [int(math.ceil(st.m3 * 1000)) * (1 if st.kind in PICKUP_KINDS else -1) for st in problem.stops]
    payload: dict[str, Any] = {
        "cost_matrix_data": {"data": {"0": matrix}},
        "travel_time_matrix_data": {"data": {"0": matrix}},
        "fleet_data": {
            "vehicle_locations": [[1 + k, 0] for k in range(v)],
            # Onboard load (re-plan) is approximated by reducing free capacity.
            "capacities": [
                [max(0, int(veh.cap_kg * 10) - int(math.ceil(veh.onboard_kg * 10))) for veh in problem.vehicles],
                [max(0, veh.cap_boxes - veh.onboard_boxes) for veh in problem.vehicles],
                [max(0, int(veh.cap_m3 * 1000) - int(math.ceil(veh.onboard_m3 * 1000))) for veh in problem.vehicles],
            ],
            "vehicle_max_times": [int(veh.max_route_s) for veh in problem.vehicles],
            "vehicle_fixed_costs": [int(veh.fixed_s) for veh in problem.vehicles],
        },
        "task_data": {
            "task_locations": [1 + v + i for i in range(s)],
            "demand": [kg, boxes, litres],
            # cuOpt windows are hard: send only the opening; lateness is scored by vrp.evaluate.
            "task_time_windows": [[st.window_start_s or 0, HORIZON_S] for st in problem.stops],
            "pickup_and_delivery_pairs": [[task_of[p], task_of[d]] for p, d in problem.pairs],
            "service_times": [st.service_s for st in problem.stops],
        },
        "solver_config": {"time_limit": max(1, int(problem.time_limit_s))},
    }
    match = [
        {"order_id": task_of[d], "vehicle_ids": [k]}
        for k, veh in enumerate(problem.vehicles)
        for d in veh.must_deliver
        if d in task_of
    ]
    if match:
        payload["task_data"]["order_vehicle_match"] = match
    return payload


def parse_routes(problem: Problem, body: Any) -> dict[str, list[str]]:
    resp = body.get("response", body) if isinstance(body, dict) else {}
    sol = resp.get("solver_response", resp) if isinstance(resp, dict) else {}
    vdata = sol.get("vehicle_data") or {}
    out: dict[str, list[str]] = {}
    for vid, info in vdata.items():
        try:
            veh = problem.vehicles[int(vid)]
        except (ValueError, IndexError):
            continue
        keys = [problem.stops[t].key for t in info.get("task_id", []) if isinstance(t, int) and 0 <= t < len(problem.stops)]
        if keys:
            out[veh.id] = keys
    return out


def solve_cuopt(problem: Problem, *, base_url: str, timeout_s: float = 30.0) -> dict[str, list[str]] | None:
    if not problem.stops or not problem.vehicles:
        return {}
    url = base_url.rstrip("/")
    try:
        with httpx.Client(timeout=timeout_s) as client:
            r = client.post(f"{url}/cuopt/request", json=build_payload(problem))
            r.raise_for_status()
            body = r.json()
            req = body.get("reqId") if isinstance(body, dict) else None
            deadline = time.monotonic() + timeout_s
            while req and "response" not in body and time.monotonic() < deadline:
                time.sleep(0.5)
                r = client.get(f"{url}/cuopt/solution/{req}")
                if r.status_code == 200:
                    body = r.json()
        return parse_routes(problem, body)
    except Exception as exc:  # noqa: BLE001 — optional solver; OR-Tools answers
        logger.warning("cuopt_unavailable: %s", type(exc).__name__)
        return None
