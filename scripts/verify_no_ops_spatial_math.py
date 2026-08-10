#!/usr/bin/env python3
"""Fleetbase-first guard — ban hand-rolled spatial math in the admin ops layer.

Implements .cursor/rules/fleetbase-first-policy.mdc rule 3: admin_engine and
admin routers must never compute dispatch distance, nearest-driver ranking,
matrices, or waypoint sequencing locally — those payloads go to Valhalla/OSRM
via the Fleetbase adapter. Also bans references to removed modules so the
deleted live-map / route-center stack cannot silently regrow.
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
        (r"haversine|great_circle", "straight-line distance — use Valhalla/OSRM via adapter"),
        (r"nearest[_ ]driver", "nearest-driver ranking — Fleetbase dispatch / matrix owns this"),
        (r"distance[_ ]matrix|travel[_ ]matrix", "matrix math — call Valhalla/OSRM matrix API"),
        (r"\bortools\b|\bvroom\b", "optimization solver — Fleetbase orchestrator owns sequencing"),
        (r"waypoint[_ ]sequenc|def \w*optimi|class \w*Optimiz", "sequencing/optimization code — Fleetbase orchestrator only"),
        (r"live_map|live-map", "admin live map was deleted (second FleetOps) — do not reintroduce"),
        (r"route_template|route_center", "Route Center was deleted — Fleetbase orchestrator only"),
        (r"DriverLocationPing", "ping mirror is deprecated for ops — Fleetbase owns driver GPS"),
    )
)


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
                    continue  # inline waiver for labels that name Fleetbase-owned steps
                if stripped.startswith("#"):
                    continue  # plain comments may reference history
                for pattern, why in _BANNED:
                    if pattern.search(line):
                        failures.append(f"{rel}:{lineno}: `{pattern.pattern}` — {why}")
    if failures:
        print("fleetbase-first spatial-math guard FAILED:")
        print("\n".join(f"  - {f}" for f in failures))
        return 1
    print("OK: no hand-rolled spatial math / removed-module refs in admin ops layer")
    return 0


if __name__ == "__main__":
    sys.exit(main())
