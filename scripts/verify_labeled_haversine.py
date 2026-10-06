#!/usr/bin/env python3
"""Driver-platform haversine must be labeled — never a silent operational ETA.

Quotes keep labeled haversine in apps/api routing.py (not a defect).
This guard only covers next-stop / import / optimizer / shift.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS: tuple[tuple[Path, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ROOT / "services/driver-platform/porterchain_driver/next_stop.py",
        ('"source": source', "source=\"haversine\""),
        ("distance_m / 500", "/ 500)"),
    ),
    (
        ROOT / "services/driver-platform/porterchain_driver/shift.py",
        ('"mileage_source"', "last_known_haversine"),
        (),
    ),
    (
        ROOT / "services/driver-platform/porterchain_driver/route_optimizer.py",
        ("queue_one_van", "porterchain"),
        ("_two_opt", "_solve_pd_vrp", '"engine": "haversine"', "_StopNode"),
    ),
    (
        ROOT / "services/python/porterchain_services/maps/sequence.py",
        ("source or \"haversine\"", "optimize_drop_order_with_source"),
        (),
    ),
    (
        ROOT / "apps/api/src/porterchain_api/services/routing.py",
        ('"haversine"',),
        (),
    ),
)


def main() -> int:
    failures: list[str] = []
    for path, required, forbidden in CHECKS:
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        for needle in required:
            if needle not in text:
                failures.append(f"{rel}: missing labeled `{needle}`")
        for needle in forbidden:
            if needle in text:
                failures.append(f"{rel}: forbidden `{needle}`")
    gta = ROOT / "services/pricing-engine/porterchain_pricing/gta_rate.py"
    if gta.is_file():
        for line in gta.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "isochrone(" in stripped:
                failures.append("gta_rate.py must not call Valhalla isochrone (CAD parity)")
                break
    if failures:
        print("labeled-haversine guard FAILED:")
        print("\n".join(f"  - {f}" for f in failures))
        return 1
    print("OK: next-stop/import/optimizer/shift haversine is labeled; quotes keep fallback")
    return 0


if __name__ == "__main__":
    sys.exit(main())
