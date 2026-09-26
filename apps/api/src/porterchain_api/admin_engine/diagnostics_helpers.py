"""Shared helpers and constants for admin diagnostics."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from typing import Any, Callable

import httpx

from porterchain_api.admin_engine.diagnostics_catalog import COMPONENT_CATEGORY
from porterchain_api.platform.health_status import HealthStatus, normalize_check_status

HealthClass = HealthStatus  # healthy | warning | critical — Jeff Dean triad

EVENT_PUBLISHERS: dict[str, str] = {
    "quote.created": "booking_engine",
    "booking.confirmed": "booking_engine",
    "payment.succeeded": "billing_engine",
    "order.created": "booking_engine",
    "order.dispatch_ready": "orders_engine",
    "fleetbase.order_created": "fleetbase_engine",
    "notification.queued": "notification_engine",
    "claim.opened": "admin_engine",
    "support.ticket_created": "admin_engine",
}

EVENT_CONSUMERS: dict[str, list[str]] = {
    "payment.succeeded": ["booking_engine", "notification_engine", "billing_engine"],
    "booking.confirmed": ["notification_engine", "fleetbase_engine"],
    "order.dispatch_ready": ["fleetbase_engine", "notification_engine"],
    "fleetbase.status_updated": ["fleetbase_engine", "notification_engine"],
}

def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _classify(raw: str) -> HealthClass:
    """Delegate to platform SSOT so probes + Jeff Dean share one mapper."""
    return normalize_check_status(raw)


def _component(
    component_id: str,
    name: str,
    *,
    status: HealthClass,
    latency_ms: float | None = None,
    last_sync: str | None = None,
    version: str | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    recovery_status: str = "none",
    details: dict[str, Any] | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    cat = category or COMPONENT_CATEGORY.get(component_id, "infrastructure")
    return {
        "id": component_id,
        "name": name,
        "category": cat,
        "status": status,
        "latency_ms": round(latency_ms, 1) if latency_ms is not None else None,
        "last_sync": last_sync,
        "version": version,
        "errors": errors or [],
        "warnings": warnings or [],
        "recovery_status": recovery_status,
        "details": details or {},
    }


def _probe_http(
    url: str,
    *,
    timeout: float = 5.0,
    method: str = "GET",
    local_optional: bool = False,
) -> tuple[HealthClass, float | None, str | None]:
    start = time.monotonic()
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.request(method, url)
            latency = (time.monotonic() - start) * 1000
            if response.status_code < 500:
                return "healthy", latency, None
            return "critical", latency, f"HTTP {response.status_code}"
    except httpx.ConnectError as exc:
        if local_optional:
            return "warning", None, f"Not running: {exc}"
        return "critical", None, str(exc)[:500]
    except Exception as exc:  # noqa: BLE001
        return "critical", None, str(exc)[:500]


def _portal_component(
    cid: str,
    name: str,
    url: str,
    *,
    local: bool,
) -> dict[str, Any]:
    status, latency, err = _probe_http(url, local_optional=local)
    warnings: list[str] = []
    if cid == "driver_mobile":
        warnings.append("Web proxy for Expo/mobile — verify native app separately")
    if local and status == "warning" and err and "Not running" in err:
        warnings.append("Start with pnpm dev:website / dev:merchant / dev:driver")
    return _component(
        cid,
        name,
        status=status,
        latency_ms=latency,
        errors=[err] if err else [],
        warnings=warnings,
        details={"url": url},
    )


def _run_probe_batch(
    probes: list[tuple[str, str, Callable[[], dict[str, Any]]]],
    *,
    max_workers: int = 8,
) -> dict[str, tuple[str, dict[str, Any]]]:
    """Run independent probe callables in parallel; returns {id: (name, probe_dict)}."""
    if not probes:
        return {}

    results: dict[str, tuple[str, dict[str, Any]]] = {}
    workers = min(max_workers, len(probes))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(fn): (cid, name) for cid, name, fn in probes}
        for future in as_completed(future_map):
            cid, name = future_map[future]
            try:
                probe = future.result()
            except Exception as exc:  # noqa: BLE001
                probe = {"status": "critical", "errors": [str(exc)]}
            results[cid] = (name, probe)
    return results


def _openapi_paths() -> set[str]:
    """Collect registered API paths — works with FastAPI _IncludedRouter nesting."""
    from porterchain_api.main import create_app

    app = create_app()
    return set(app.openapi().get("paths", {}).keys())


def _test_result(
    test_id: str,
    name: str,
    *,
    status: HealthClass,
    execution_ms: float,
    logs: list[str],
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": test_id,
        "name": name,
        "status": status,
        "execution_ms": round(execution_ms, 1),
        "logs": logs,
        "details": details or {},
        "ran_at": _now_iso(),
    }
