#!/usr/bin/env python3
"""§3.5.5 — Fleetbase sync SLO ≥98% with ops alerts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETRY_QUEUE = ROOT / "apps/api/src/porterchain_api/fleetbase_engine/retry_queue.py"
SYNC_HEALTH = ROOT / "apps/api/src/porterchain_api/fleetbase_engine/sync_health.py"
DIAGNOSTICS = ROOT / "apps/api/src/porterchain_api/admin_engine/diagnostics_workflows.py"
HEALTH = ROOT / "apps/api/src/porterchain_api/platform/health.py"
RUNBOOK = ROOT / "RUNBOOK.md"


def main() -> int:
    failures: list[str] = []
    rq = RETRY_QUEUE.read_text(encoding="utf-8", errors="ignore")
    sh = SYNC_HEALTH.read_text(encoding="utf-8", errors="ignore")
    diag = DIAGNOSTICS.read_text(encoding="utf-8", errors="ignore")
    health = HEALTH.read_text(encoding="utf-8", errors="ignore")

    match = re.search(r"FLEETBASE_SYNC_SLO_TARGET_PCT\s*=\s*([\d.]+)", rq)
    if not match or float(match.group(1)) < 98.0:
        failures.append("§3.5.5 retry_queue.py must set FLEETBASE_SYNC_SLO_TARGET_PCT >= 98")
    if "FLEETBASE_SYNC_SLO_TARGET_PCT" not in sh:
        failures.append("§3.5.5 sync_health.py must import FLEETBASE_SYNC_SLO_TARGET_PCT")
    if "build_fleetbase_sync_alerts" not in sh:
        failures.append("§3.5.5 sync_health.py missing build_fleetbase_sync_alerts")
    if '"alerts"' not in sh:
        failures.append("§3.5.5 assess_fleetbase_sync must return alerts")
    if 'slo.get("alerts"' not in diag:
        failures.append("§3.5.5 diagnostics fleetbase_sync_monitor must surface alerts")
    if "meets_slo" not in health:
        failures.append("§3.5.5 health/ready must check fleetbase_sync.meets_slo")
    if RUNBOOK.is_file():
        rb = RUNBOOK.read_text(encoding="utf-8", errors="ignore")
        if "≥98%" not in rb and ">=98%" not in rb:
            failures.append("§3.5.5 RUNBOOK G2 must document ≥98% sync SLO")

    if failures:
        print("Fleetbase sync SLO guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Fleetbase sync SLO guard passed (§3.5.5 — 98% target + alerts).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
