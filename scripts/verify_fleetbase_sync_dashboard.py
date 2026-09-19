#!/usr/bin/env python3
"""§5.1.14 / DD-13 — Fleetbase sync dashboard in admin diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAG_ROUTER = ROOT / "apps/api/src/porterchain_api/routers/diagnostics.py"
WORKFLOWS = ROOT / "apps/api/src/porterchain_api/admin_engine/diagnostics_workflows.py"
EXEC = ROOT / "apps/api/src/porterchain_api/admin_engine/execution_metrics.py"


def main() -> int:
    failures: list[str] = []

    for path, needles in (
        (DIAG_ROUTER, ("/fleetbase-sync", "/execution-metrics")),
        (WORKFLOWS, ("fleetbase_sync_monitor", "execution_metrics_dashboard")),
        (EXEC, ("fleetbase_sync", "assess_fleetbase_sync")),
    ):
        if not path.is_file():
            failures.append(f"§5.1.14 missing {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle not in text:
                failures.append(f"§5.1.14 {path.name} missing {needle}")

    if failures:
        print("Fleetbase sync dashboard guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Fleetbase sync dashboard guard passed (§5.1.14 — admin diagnostics + execution dashboard).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
