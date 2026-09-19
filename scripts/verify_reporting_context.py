#!/usr/bin/env python3
"""§3.2.12 — reporting lives in merchant_engine; hollow reporting_engine stays deleted."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTING_ENGINE = ROOT / "apps/api/src/porterchain_api/reporting_engine"
REPORTING_METRICS = ROOT / "apps/api/src/porterchain_api/merchant_engine/reporting_metrics.py"


def main() -> int:
    failures: list[str] = []
    if REPORTING_ENGINE.exists():
        failures.append("§3.2.12 forbidden reporting_engine/ package present — use merchant_engine/reporting_metrics.py")
    if not REPORTING_METRICS.is_file():
        failures.append("§3.2.12 missing merchant_engine/reporting_metrics.py")
    else:
        text = REPORTING_METRICS.read_text(encoding="utf-8", errors="ignore")
        if "REPORT_TYPES" not in text:
            failures.append("§3.2.12 reporting_metrics.py missing REPORT_TYPES catalog")

    if failures:
        print("Reporting context guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Reporting context guard passed (§3.2.12 — deleted reporting_engine; metrics in merchant_engine).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
