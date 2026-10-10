#!/usr/bin/env python3
"""§5.2 — validate:e2e + day-plan guards wired for the dev layer."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package.json"
NIGHTLY = ROOT / ".github/workflows/nightly-e2e.yml"
E2E_SCRIPT = ROOT / "apps/api/scripts/run_e2e_validation.py"
DAY_PLAN_SLO = ROOT / "scripts/verify_day_plan_scorecard.py"
SEQUENCER = ROOT / "apps/api/src/porterchain_api/dispatch_engine/sequencer.py"


def main() -> int:
    failures: list[str] = []
    pkg = PACKAGE.read_text(encoding="utf-8", errors="ignore") if PACKAGE.is_file() else ""

    for script in ("validate:e2e", "validate:d3:e2e", "validate:architecture"):
        if script not in pkg:
            failures.append(f"§5.2 package.json missing {script}")

    if "docker:fleetbase:verify" in pkg:
        failures.append("§5.2 package.json still wires docker:fleetbase:verify — use day-plan guards")

    if not NIGHTLY.is_file():
        failures.append("§5.2 missing nightly-e2e.yml")
    elif "verify_d3_matrix.py --e2e" not in NIGHTLY.read_text(encoding="utf-8", errors="ignore"):
        failures.append("§5.2 nightly-e2e must run verify_d3_matrix --e2e")

    if not E2E_SCRIPT.is_file():
        failures.append("§5.2 missing run_e2e_validation.py")

    if not DAY_PLAN_SLO.is_file():
        failures.append("§5.2 missing day-plan scorecard guard (verify_day_plan_scorecard.py)")
    if not SEQUENCER.is_file():
        failures.append("§5.2 missing dispatch_engine/sequencer.py")

    if failures:
        print("Execution validation scripts guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Execution validation scripts guard passed (§5.2 — validate:e2e + day-plan).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
