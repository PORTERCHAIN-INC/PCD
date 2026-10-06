#!/usr/bin/env python3
"""Dispatch spatial guard — ban hand-rolled math in the admin ops layer.

Implements .cursor/rules/fleetbase-first-policy.mdc rule 3: admin_engine and
admin routers must never compute dispatch distance, nearest-driver ranking,
matrices, or waypoint sequencing locally. Road cost is Valhalla/OSRM.
Day sequencing is OR-Tools only in dispatch_engine — not in admin_engine.
HS-20: Google Places is autocomplete/tiles only; never Distance Matrix for ops math.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = (
    ROOT / "apps/api/src/porterchain_api/admin_engine",
    ROOT / "apps/api/src/porterchain_api/routers/admin",
)

# (compiled regex, why banned)
_BANNED: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), why)
    for pattern, why in (
        (
            r"distancematrix|DistanceMatrix",
            "HS-20 Google Places is autocomplete only — never Distance Matrix for ops",
        ),
        (r"haversine|great_circle", "straight-line distance — use Valhalla/OSRM"),
        (r"nearest[_ ]driver", "nearest-driver ranking — Valhalla matrix / dispatch scoring"),
        (r"distance[_ ]matrix|travel[_ ]matrix", "matrix math — call Valhalla/OSRM matrix API"),
        (
            r"(?:^|\s)(?:from|import)\s+ortools\b|(?:^|\s)(?:from|import)\s+vroom\b",
            "optimization solver import — only dispatch_engine/sequencer.py may use OR-Tools",
        ),
        (r"waypoint[_ ]sequenc|def \w*optimi|class \w*Optimiz", "sequencing — call dispatch_engine day plan"),
        (
            r"/v1/operations/live-map|/v1/admin/map/live",
            "deleted live-map aliases — keep /v1/admin/operations/live-map",
        ),
        (
            r"RouteCenterPlan\b|route_center_plans\b|/admin/route-center\b",
            "Route Center dispatch was deleted — use PorterChain day plan",
        ),
        (r"DriverLocationPing", "ping mirror is deprecated for ops — use Redis last_known"),
    )
)

_HTTP_SCAN = (
    ROOT / "apps/api/src/porterchain_api/admin_engine/control_tower",
    ROOT / "apps/api/src/porterchain_api/admin_engine/dispatch_suggestions_service.py",
)
_BANNED_HTTP: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern), why)
    for pattern, why in (
        (r"get_fleetbase_integration", "scoring/assignment must not open retired Fleetbase HTTP"),
        (r"adapter\.list_drivers", "use PorterChain duty / last_known roster"),
        (r"adapter\.drivers\.get", "use PorterChain driver id + last_known"),
        (r"porterchain_fleetbase_adapter", "Fleetbase adapter package is removed"),
    )
)

_TSP_SCAN = (
    ROOT / "services/driver-platform/porterchain_driver/route_optimizer.py",
    ROOT / "services/python/porterchain_services/maps/sequence.py",
    ROOT / "apps/api/src/porterchain_api/merchant_engine/import_route_optimize.py",
)
_TSP_BANNED: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern), why)
    for pattern, why in (
        (
            r"_two_opt|_solve_pd_vrp|two_opt_improve|class _StopNode",
            "Python TSP — day plan is OR-Tools in dispatch_engine; Valhalla is the matrix",
        ),
    )
)


def _iter_py(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.py"))
    return []


def main() -> int:
    failures: list[str] = []
    for scan in SCAN_DIRS:
        if not scan.is_dir():
            failures.append(f"missing scan dir: {scan.relative_to(ROOT)}")
            continue
        for py in sorted(scan.rglob("*.py")):
            rel = py.relative_to(ROOT)
            for lineno, line in enumerate(py.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                stripped = line.strip()
                if "fleetbase-first:ok" in stripped:
                    continue
                if stripped.startswith("#"):
                    continue
                for pattern, why in _BANNED:
                    if pattern.search(line):
                        failures.append(f"{rel}:{lineno}: `{pattern.pattern}` — {why}")
    for scan in _HTTP_SCAN:
        files = _iter_py(scan)
        if not files:
            failures.append(f"missing HTTP scan path: {scan.relative_to(ROOT)}")
            continue
        for py in files:
            rel = py.relative_to(ROOT)
            for lineno, line in enumerate(py.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                stripped = line.strip()
                if "fleetbase-first:ok" in stripped or stripped.startswith("#"):
                    continue
                for pattern, why in _BANNED_HTTP:
                    if pattern.search(line):
                        failures.append(f"{rel}:{lineno}: `{pattern.pattern}` — {why}")
    for py in _TSP_SCAN:
        if not py.is_file():
            failures.append(f"missing TSP scan path: {py.relative_to(ROOT)}")
            continue
        rel = py.relative_to(ROOT)
        for lineno, line in enumerate(py.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, why in _TSP_BANNED:
                if pattern.search(line):
                    failures.append(f"{rel}:{lineno}: `{pattern.pattern}` — {why}")

    maps_allow = {
        ROOT / "services/python/porterchain_services/maps/service.py",
    }
    private_maps = re.compile(r"(?:maps|_maps)\._(?:osrm_|valhalla_)")
    private_maps_def = re.compile(r"^\s*def _(?:osrm_|valhalla_)")
    engine_roots = (
        ROOT / "apps/api/src/porterchain_api",
        ROOT / "services/driver-platform",
        ROOT / "apps/api/src/porterchain_api/reporting",
    )
    for scan in engine_roots:
        files = _iter_py(scan)
        for py in files:
            if py in maps_allow:
                continue
            # OR-Tools day plan is allowed only here.
            if "dispatch_engine" in str(py.relative_to(ROOT)).replace("\\", "/"):
                continue
            rel = py.relative_to(ROOT)
            text = py.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if private_maps.search(line) or private_maps_def.search(line):
                    failures.append(
                        f"{rel}:{lineno}: private Maps `_osrm_`/`_valhalla_` — use MapsService public API"
                    )

    _GOOGLE_DM = re.compile(
        r"distancematrix|distance_matrix|google\.maps\.DistanceMatrix|"
        r"maps/api/distancematrix|maps/api/directions|DirectionsService|"
        r"computeRoutes|routes\.googleapis\.com",
        re.IGNORECASE,
    )
    _GOOGLE_DM_SCAN = (
        ROOT / "apps/api/src/porterchain_api/services/routing.py",
        ROOT / "apps/api/src/porterchain_api/pricing_engine",
        ROOT / "apps/api/src/porterchain_api/booking_engine",
        ROOT / "apps/api/src/porterchain_api/merchant_engine",
        ROOT / "services/pricing-engine",
        ROOT / "services/python/porterchain_services/maps",
        ROOT / "packages/maps",
        ROOT / "apps/customer/src",
        ROOT / "apps/merchant-portal/src",
        ROOT / "apps/admin/src",
        ROOT / "website/src",
    )
    _GOOGLE_DM_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx"}
    for scan in _GOOGLE_DM_SCAN:
        if scan.is_file():
            files = [scan]
        elif scan.is_dir():
            files = [
                p
                for p in scan.rglob("*")
                if p.is_file() and p.suffix in _GOOGLE_DM_EXTS and "node_modules" not in p.parts
            ]
        else:
            continue
        for path in files:
            rel = path.relative_to(ROOT)
            for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                stripped = line.strip()
                if "fleetbase-first:ok" in stripped or stripped.startswith("#") or stripped.startswith("//"):
                    continue
                if _GOOGLE_DM.search(line):
                    failures.append(
                        f"{rel}:{lineno}: Google Distance/Directions — Places/tiles only; "
                        "pricing distance via MapsService (Valhalla/OSRM)"
                    )

    sequencer = ROOT / "apps/api/src/porterchain_api/dispatch_engine/sequencer.py"
    if not sequencer.is_file():
        failures.append("missing dispatch_engine/sequencer.py — OR-Tools day plan required")
    elif "ortools" not in sequencer.read_text(encoding="utf-8") and "pywrapcp" not in sequencer.read_text(
        encoding="utf-8"
    ):
        failures.append("dispatch_engine/sequencer.py must use OR-Tools")

    if failures:
        print("dispatch spatial-math guard FAILED:")
        print("\n".join(f"  - {f}" for f in failures))
        return 1
    print("OK: no hand-rolled spatial math in ops; OR-Tools day plan in dispatch_engine; Places/tiles only for Google")
    return 0


if __name__ == "__main__":
    sys.exit(main())
