"""Removed ops endpoints stay gone (fleetbase-first refactor, Aug 2026).

The admin live-map stack, legacy dispatch/map aliases, and Route Center were
deleted because Fleetbase owns dispatch, live GPS, and optimization. This test
fails if any of those routes reappear — in the OpenAPI surface or at runtime —
so the second FleetOps cannot silently regrow.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from porterchain_api.main import app

_REMOVED_NEEDLES = (
    "live-map",
    "live_map",
    "route-template",
    "route_template",
    "assign-batch",
    "dispatch/queue",
    "map/live",
    "/queue/optimize",
)

_REMOVED_PATHS = (
    "/v1/admin/dispatch/queue",
    "/v1/admin/map/live",
    "/v1/operations/live-map",
    "/v1/operations/live-map/search",
    "/v1/operations/live-map/playback",
    "/v1/operations/live-map/nearest-drivers",
    "/v1/operations/map",
    "/v1/operations/queue/assign-batch",
    "/v1/admin/route-templates",
)

_KEPT_DISPATCH_BRIDGE = "/v1/admin/dispatch/orders/{order_id}/assign"


def _spec_paths() -> set[str]:
    return set(app.openapi().get("paths", {}))


def test_removed_ops_routes_absent_from_openapi() -> None:
    paths = _spec_paths()
    offenders = sorted(p for p in paths for n in _REMOVED_NEEDLES if n in p)
    assert not offenders, f"removed ops routes re-registered: {offenders}"


def test_removed_ops_routes_return_404() -> None:
    client = TestClient(app)
    failures = []
    for path in _REMOVED_PATHS:
        for method in (client.get, client.post):
            status = method(path).status_code
            if status != 404:
                failures.append(f"{method.__name__.upper()} {path} -> {status}")
    assert not failures, "removed ops routes no longer 404: " + "; ".join(failures)


def test_kept_dispatch_bridge_route_present() -> None:
    # The one dispatch surface we keep: single-order assign that bridges to Fleetbase.
    assert _KEPT_DISPATCH_BRIDGE in _spec_paths()
