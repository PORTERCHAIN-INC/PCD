#!/usr/bin/env python3
"""Day-plan scorecard replaces the retired Fleetbase sync SLO (≥98%)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEQUENCER = ROOT / "apps/api/src/porterchain_api/dispatch_engine/sequencer.py"
DAY_PLAN = ROOT / "apps/api/src/porterchain_api/dispatch_engine/day_plan.py"
OPTIMIZE_STORE = ROOT / "apps/api/src/porterchain_api/dispatch_engine/optimize_run_store.py"
HEALTH = ROOT / "apps/api/src/porterchain_api/platform/health.py"
RETIRED_SYNC = ROOT / "apps/api/src/porterchain_api/fleetbase_engine/sync_health.py"
RETIRED_RETRY = ROOT / "apps/api/src/porterchain_api/fleetbase_engine/retry_queue.py"


def main() -> int:
    failures: list[str] = []

    if RETIRED_SYNC.is_file() or RETIRED_RETRY.is_file():
        failures.append("Fleetbase sync_health/retry_queue still present — remove with the adapter")

    for label, path in (
        ("sequencer", SEQUENCER),
        ("day_plan", DAY_PLAN),
        ("optimize_run_store", OPTIMIZE_STORE),
    ):
        if not path.is_file():
            failures.append(f"day-plan module missing: {label} ({path.relative_to(ROOT)})")

    if SEQUENCER.is_file():
        seq = SEQUENCER.read_text(encoding="utf-8")
        if "unassigned" not in seq:
            failures.append("sequencer must record unassigned jobs (scorecard)")
        if "ortools" not in seq and "pywrapcp" not in seq:
            failures.append("sequencer must use OR-Tools")

    if DAY_PLAN.is_file():
        plan = DAY_PLAN.read_text(encoding="utf-8")
        for needle in ("waypoints", "unassigned", "added_minutes", "metrics"):
            if needle not in plan:
                failures.append(f"day_plan missing scorecard field wire: {needle}")

    if HEALTH.is_file():
        health = HEALTH.read_text(encoding="utf-8")
        if "assess_fleetbase_sync" in health or "build_fleetbase_sync_alerts" in health:
            failures.append("platform/health still assesses Fleetbase sync SLO")
        if 'payload["fleetbase_sync"]' in health or "fleetbase_sync.meets_slo" in health:
            failures.append("platform/health still exposes fleetbase_sync")

    if failures:
        print("Day-plan scorecard guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Day-plan scorecard guard passed — Fleetbase sync SLO retired; OR-Tools plan metrics present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
