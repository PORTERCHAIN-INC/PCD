#!/usr/bin/env python3
"""§5.3.1 — orders/week metric instrumented in admin diagnostics + /metrics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "apps/api/src/porterchain_api/admin_engine/execution_metrics.py"
METRICS = ROOT / "apps/api/src/porterchain_api/platform/metrics.py"
DIAG = ROOT / "apps/api/src/porterchain_api/routers/diagnostics.py"
TEST = ROOT / "apps/api/tests/test_execution_metrics.py"


def main() -> int:
    failures: list[str] = []

    for path in (MODULE, METRICS, DIAG, TEST):
        if not path.is_file():
            failures.append(f"§5.3.1 missing {path.relative_to(ROOT)}")

    if MODULE.is_file():
        text = MODULE.read_text(encoding="utf-8", errors="ignore")
        for needle in ("ORDERS_PER_WEEK_TARGET", "assess_orders_per_week", "orders_last_7d"):
            if needle not in text:
                failures.append(f"§5.3.1 execution_metrics.py missing {needle}")

    if METRICS.is_file():
        if "porterchain_orders_last_7d" not in METRICS.read_text(encoding="utf-8", errors="ignore"):
            failures.append("§5.3.1 /metrics missing porterchain_orders_last_7d")

    if DIAG.is_file():
        if "/execution-metrics" not in DIAG.read_text(encoding="utf-8", errors="ignore"):
            failures.append("§5.3.1 diagnostics missing /execution-metrics route")

    if failures:
        print("Orders/week metric guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Orders/week metric guard passed (§5.3.1 — dashboard + Prometheus; prod target ≥50).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
