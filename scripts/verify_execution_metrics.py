#!/usr/bin/env python3
"""§5.3 — execution business metrics + §5.1 ops guards in CI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_GUARDS = (
    "verify_fleetbase_sync_slo.py",
    "verify_webhook_delivery_slo.py",
    "verify_deploy_frequency.py",
    "verify_orders_per_week_metric.py",
    "verify_fleetbase_sync_dashboard.py",
    "verify_fleetbase_runbook.py",
    "verify_rollback_runbook.py",
    "verify_execution_validation_scripts.py",
    "verify_backup_restore_doc.py",
    "verify_uptime_monitor_doc.py",
    "verify_secrets_rotation_doc.py",
    "verify_incident_drill_doc.py",
    "verify_fleetbase_replay_prod_doc.py",
    "verify_business_metrics.py",
)


def main() -> int:
    failures: list[str] = []

    for name in _GUARDS:
        path = ROOT / "scripts" / name
        if not path.is_file():
            failures.append(f"§5 missing {name}")
            continue
        result = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            failures.append(f"{name} failed:\n{result.stdout}\n{result.stderr}")

    runbook = ROOT / "RUNBOOK.md"
    if runbook.is_file():
        text = runbook.read_text(encoding="utf-8", errors="ignore")
        if "≥98%" not in text and ">=98%" not in text:
            failures.append("§5.3.6 RUNBOOK missing ≥98% Fleetbase sync criteria")
    else:
        failures.append("§5 missing RUNBOOK.md")

    if failures:
        print("Execution metrics guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Execution metrics guard passed (§5.3 + §5.1 ops instrumentation in CI).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
