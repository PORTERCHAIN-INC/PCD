"""§5.3.7 — merchant outbound webhook delivery SLO (≥99%)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEALTH = ROOT / "apps/api/src/porterchain_api/merchant_engine/webhook_delivery_health.py"
READY = ROOT / "apps/api/src/porterchain_api/platform/health.py"
METRICS = ROOT / "apps/api/src/porterchain_api/platform/metrics.py"
DIAG = ROOT / "apps/api/src/porterchain_api/admin_engine/diagnostics_workflows.py"
RUNBOOK = ROOT / "RUNBOOK.md"


def main() -> int:
    failures: list[str] = []

    if HEALTH.is_file():
        text = HEALTH.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"MERCHANT_WEBHOOK_DELIVERY_SLO_TARGET_PCT\s*=\s*([\d.]+)", text)
        if not match or float(match.group(1)) < 99.0:
            failures.append("§5.3.7 webhook_delivery_health.py must set SLO target >= 99")
        for needle in ("assess_merchant_webhook_delivery", "build_merchant_webhook_delivery_alerts"):
            if needle not in text:
                failures.append(f"§5.3.7 missing {needle}")

    for path, needle in (
        (READY, "merchant_webhook_delivery"),
        (METRICS, "porterchain_merchant_webhook_delivery_success_pct"),
        (DIAG, "merchant_webhook_delivery_monitor"),
    ):
        if not path.is_file():
            failures.append(f"§5.3.7 missing {path.relative_to(ROOT)}")
        elif needle not in path.read_text(encoding="utf-8", errors="ignore"):
            failures.append(f"§5.3.7 {path.name} missing {needle}")

    if RUNBOOK.is_file():
        rb = RUNBOOK.read_text(encoding="utf-8", errors="ignore")
        if "≥99%" not in rb and ">=99%" not in rb:
            failures.append("§5.3.7 RUNBOOK missing ≥99% merchant webhook delivery SLO")

    if failures:
        print("Webhook delivery SLO guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Webhook delivery SLO guard passed (§5.3.7 — ≥99% target + metrics).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
