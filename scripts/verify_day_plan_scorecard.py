#!/usr/bin/env python3
"""Day-plan scorecard guard: the OR-Tools sequencer and day plan expose scorecard fields."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEQUENCER = ROOT / "apps/api/src/porterchain_api/dispatch_engine/sequencer.py"
DAY_PLAN = ROOT / "apps/api/src/porterchain_api/dispatch_engine/day_plan.py"
OPTIMIZE_STORE = ROOT / "apps/api/src/porterchain_api/dispatch_engine/optimize_run_store.py"


def main() -> int:
    failures: list[str] = []

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

    if failures:
        print("Day-plan scorecard guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Day-plan scorecard guard passed — OR-Tools plan metrics present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
