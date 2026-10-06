"""NVIDIA cuOpt Catalog HTTP client — shadow VRP only (never commit SoT).

POST https://optimize.api.nvidia.com/v1/nvidia/cuopt
action=cuOpt_OptimizedRouting with Valhalla cost matrices.

Fails soft on RPM / auth / transport — callers keep the OR-Tools day plan.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from porterchain_shared.config.settings import get_platform_settings

logger = logging.getLogger(__name__)

DEFAULT_CUOPT_URL = "https://optimize.api.nvidia.com/v1/nvidia/cuopt"
_fail_streak = 0
_circuit_open_until = 0.0
_CIRCUIT_FAILS = 3
_CIRCUIT_COOLDOWN_S = 60.0


def cuopt_configured() -> bool:
    settings = get_platform_settings()
    return bool((getattr(settings, "nvidia_api_key", "") or "").strip())


def cuopt_status() -> dict[str, Any]:
    open_circuit = time.monotonic() < _circuit_open_until
    return {
        "configured": cuopt_configured(),
        "circuit_open": open_circuit,
        "url": _cuopt_url(),
        "note": "Shadow only — PorterChain OR-Tools remains commit SoT.",
    }


def _cuopt_url() -> str:
    settings = get_platform_settings()
    return (
        getattr(settings, "nvidia_cuopt_url", None) or DEFAULT_CUOPT_URL
    ).strip().rstrip("/")


def _record_success() -> None:
    global _fail_streak, _circuit_open_until
    _fail_streak = 0
    _circuit_open_until = 0.0


def _record_failure() -> None:
    global _fail_streak, _circuit_open_until
    _fail_streak += 1
    if _fail_streak >= _CIRCUIT_FAILS:
        _circuit_open_until = time.monotonic() + _CIRCUIT_COOLDOWN_S
        logger.warning("cuOpt circuit open for %ss", _CIRCUIT_COOLDOWN_S)


def optimize_routing(
    *,
    cost_matrix: list[list[float]],
    vehicle_count: int = 1,
    time_limit_s: float = 5.0,
    timeout_s: float = 45.0,
) -> dict[str, Any]:
    """Submit a tiny VRP to cuOpt Catalog. Returns parsed totals + raw response meta.

    ``cost_matrix`` must be square (meters or abstract cost). Index 0 is depot.
    Raises ValueError when not configured; RuntimeError on HTTP/circuit failure.
    """
    if time.monotonic() < _circuit_open_until:
        raise RuntimeError("nvidia_cuopt_circuit_open")
    if not cuopt_configured():
        raise ValueError("nvidia_api_key_missing")
    n = len(cost_matrix)
    if n < 2 or any(len(row) != n for row in cost_matrix):
        raise ValueError("cost_matrix_must_be_square_n_ge_2")

    settings = get_platform_settings()
    api_key = (getattr(settings, "nvidia_api_key", "") or "").strip()
    vehicles = max(1, min(int(vehicle_count or 1), 8))
    # Locations: 0 depot; 1..n-1 tasks
    task_locations = list(range(1, n))
    data = {
        "cost_matrix_data": {"data": {"0": cost_matrix}},
        "fleet_data": {
            "vehicle_locations": [[0, 0] for _ in range(vehicles)],
            "capacities": [[max(len(task_locations), 1)] for _ in range(vehicles)],
        },
        "task_data": {
            "task_locations": task_locations,
            "demand": [[1] * len(task_locations)],
        },
        "solver_config": {"time_limit": float(time_limit_s)},
    }
    body = {
        "action": "cuOpt_OptimizedRouting",
        "data": data,
        "client_version": "custom",
    }

    started = time.perf_counter()
    url = _cuopt_url()
    with httpx.Client(timeout=timeout_s) as client:
        try:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=body,
            )
        except httpx.TimeoutException as exc:
            _record_failure()
            raise RuntimeError("nvidia_cuopt_timeout") from exc
        except httpx.HTTPError as exc:
            _record_failure()
            raise RuntimeError(f"nvidia_cuopt_transport_{type(exc).__name__}") from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    if resp.status_code == 429:
        _record_failure()
        raise RuntimeError("nvidia_cuopt_rpm_exhausted")
    if resp.status_code >= 400:
        _record_failure()
        snippet = (resp.text or "")[:240]
        raise RuntimeError(f"nvidia_cuopt_http_{resp.status_code}:{snippet}")

    try:
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001
        _record_failure()
        raise RuntimeError("nvidia_cuopt_bad_json") from exc

    _record_success()
    parsed = _parse_cuopt_response(payload)
    parsed["latency_ms"] = latency_ms
    parsed["raw_status"] = payload.get("status") if isinstance(payload, dict) else None
    return parsed


def _parse_cuopt_response(payload: Any) -> dict[str, Any]:
    """Extract total cost / vehicle routes from managed or self-host shapes."""
    root = payload if isinstance(payload, dict) else {}

    def _walk(node: Any, depth: int = 0) -> dict[str, Any]:
        if not isinstance(node, dict) or depth > 4:
            return {}
        if any(k in node for k in ("vehicle_data", "cost", "total_objective", "objective")):
            return node
        for key in ("response", "solution", "solver_response", "result", "data"):
            child = node.get(key)
            if isinstance(child, dict):
                found = _walk(child, depth + 1)
                if found:
                    return found
        return {}

    node = _walk(root) or root

    total_cost = node.get("cost")
    if total_cost is None:
        total_cost = node.get("total_objective") or node.get("objective")
    try:
        total_cost_f = float(total_cost) if total_cost is not None else None
    except (TypeError, ValueError):
        total_cost_f = None

    vehicle_data = node.get("vehicle_data") if isinstance(node.get("vehicle_data"), dict) else {}
    routes: list[dict[str, Any]] = []
    for vid, vrow in vehicle_data.items():
        if not isinstance(vrow, dict):
            continue
        routes.append(
            {
                "vehicle_id": str(vid),
                "route": list(vrow.get("route") or []),
                "cost": vrow.get("cost") or vrow.get("type_cost"),
            }
        )

    return {
        "ok": total_cost_f is not None or bool(routes),
        "total_cost": total_cost_f,
        "vehicle_count_used": len(routes) or None,
        "routes": routes[:12],
        "note": "cuOpt shadow metrics only — do not commit these assignments.",
    }
