#!/usr/bin/env python3
"""§5.3.2–5.3.4 — business metrics instrumented in dashboard + /metrics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "apps/api/src/porterchain_api/admin_engine/business_metrics.py"
EXEC = ROOT / "apps/api/src/porterchain_api/admin_engine/execution_metrics.py"
METRICS = ROOT / "apps/api/src/porterchain_api/platform/metrics.py"
DOC = ROOT / "docs/EXECUTION_METRICS.md"
TEST = ROOT / "apps/api/tests/test_business_metrics.py"


def main() -> int:
    failures: list[str] = []

    for path in (MODULE, EXEC, METRICS, DOC, TEST):
        if not path.is_file():
            failures.append(f"§5.3.2-4 missing {path.relative_to(ROOT)}")

    if MODULE.is_file():
        text = MODULE.read_text(encoding="utf-8", errors="ignore")
        for needle in (
            "AUTO_DISPATCH_TARGET_PCT",
            "ON_TIME_TARGET_PCT",
            "SUPPORT_FIRST_RESPONSE_MAX_HOURS",
            "assess_auto_dispatch",
            "assess_on_time_delivery",
            "assess_support_first_response",
        ):
            if needle not in text:
                failures.append(f"§5.3.2-4 business_metrics.py missing {needle}")

    if METRICS.is_file():
        metrics = METRICS.read_text(encoding="utf-8", errors="ignore")
        for needle in (
            "porterchain_auto_dispatch_pct",
            "porterchain_on_time_delivery_pct",
            "porterchain_support_first_response_avg_hours",
        ):
            if needle not in metrics:
                failures.append(f"§5.3.2-4 /metrics missing {needle}")

    if DOC.is_file():
        doc = DOC.read_text(encoding="utf-8", errors="ignore")
        for needle in ("5.3.2", "5.3.3", "5.3.4", "≥90%", "≥95%", "<4h"):
            if needle not in doc:
                failures.append(f"§5.3.2-4 EXECUTION_METRICS.md missing {needle}")

    if failures:
        print("Business metrics guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Business metrics guard passed (§5.3.2–5.3.4 — dispatch, on-time, support SLA).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
