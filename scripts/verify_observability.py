#!/usr/bin/env python3
"""Appendix B.1–B.3, B.6, B.11–B.12 — observability and security guards."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MIDDLEWARE = ROOT / "apps/api/src/porterchain_api/platform/middleware.py"
OBSERVABILITY = ROOT / "apps/api/src/porterchain_api/platform/observability.py"
METRICS = ROOT / "apps/api/src/porterchain_api/platform/metrics.py"
MAIN = ROOT / "apps/api/src/porterchain_api/main.py"
ERRORS = ROOT / "apps/api/src/porterchain_api/platform/errors.py"
DAY_PLAN = ROOT / "apps/api/src/porterchain_api/dispatch_engine/day_plan.py"
SEQUENCER = ROOT / "apps/api/src/porterchain_api/dispatch_engine/sequencer.py"
WEBHOOK_HEALTH = ROOT / "apps/api/src/porterchain_api/merchant_engine/webhook_delivery_health.py"
IDOR_TEST = ROOT / "apps/api/tests/test_idor.py"
ROUTERS = ROOT / "apps/api/src/porterchain_api/routers"

RAW_SQL_PATTERNS = (
    re.compile(r"db\.execute\s*\("),
    re.compile(r"session\.execute\s*\("),
    re.compile(r"text\s*\(\s*['\"]"),
)


def routers_use_raw_sql() -> list[str]:
    hits: list[str] = []
    for path in ROUTERS.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in RAW_SQL_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path.relative_to(ROOT)} matches {pattern.pattern}")
    return hits


def main() -> int:
    failures: list[str] = []

    for label, path in (
        ("middleware", MIDDLEWARE),
        ("observability", OBSERVABILITY),
        ("metrics", METRICS),
        ("main", MAIN),
        ("errors", ERRORS),
        ("webhook_health", WEBHOOK_HEALTH),
        ("idor test", IDOR_TEST),
    ):
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    mw = MIDDLEWARE.read_text(encoding="utf-8")
    if "RequestIdMiddleware" not in mw or "request_id" not in mw:
        failures.append("B.1 middleware missing correlation ID")

    obs = OBSERVABILITY.read_text(encoding="utf-8")
    if "bind_request_context" not in obs:
        failures.append("B.1 observability missing bind_request_context")

    err = ERRORS.read_text(encoding="utf-8")
    if "request_id" not in err:
        failures.append("B.2 error envelope missing request_id")

    main_py = MAIN.read_text(encoding="utf-8")
    if "request_id=rid" not in main_py or "/metrics" not in main_py:
        failures.append("B.2/B.3 main.py missing request_id in handlers or /metrics route")

    metrics = METRICS.read_text(encoding="utf-8")
    if "prometheus" not in metrics.lower() or "porterchain_" not in metrics:
        failures.append("B.3 metrics missing Prometheus exposition")

    if not DAY_PLAN.is_file() or not SEQUENCER.is_file():
        failures.append("B.6 day-plan scorecard modules missing (day_plan/sequencer)")
    else:
        plan = DAY_PLAN.read_text(encoding="utf-8")
        seq = SEQUENCER.read_text(encoding="utf-8")
        if "unassigned" not in plan or "metrics" not in plan:
            failures.append("B.6 day_plan missing unassigned/metrics scorecard")
        if "ortools" not in seq and "pywrapcp" not in seq:
            failures.append("B.6 sequencer must use OR-Tools for day-plan scorecard")

    webhook = WEBHOOK_HEALTH.read_text(encoding="utf-8")
    if "build_merchant_webhook_delivery_alerts" not in webhook:
        failures.append("B.8 merchant webhook SLO alerts missing")

    if "porterchain_queue_depth" not in metrics:
        failures.append("B.5 metrics missing porterchain_queue_depth")

    health = (ROOT / "apps/api/src/porterchain_api/platform/health.py").read_text(encoding="utf-8")
    if "_queue_health" not in health or "depths" not in health:
        failures.append("B.5 health missing queue depth probe")

    caddy = ROOT / "infrastructure/deploy/Caddyfile"
    if caddy.is_file():
        caddy_text = caddy.read_text(encoding="utf-8")
        for header in ("Strict-Transport-Security", "X-Frame-Options", "X-Content-Type-Options"):
            if header not in caddy_text:
                failures.append(f"B.9 Caddyfile missing {header}")
    else:
        failures.append("B.9 missing Caddyfile")

    portal_headers = list((ROOT / "apps").glob("*/next.config.ts"))
    if not portal_headers:
        failures.append("B.9 no portal next.config.ts for security headers")
    else:
        found_frame = any(
            "X-Frame-Options" in path.read_text(encoding="utf-8", errors="ignore") for path in portal_headers
        )
        if not found_frame:
            failures.append("B.9 portal next.config.ts missing X-Frame-Options")

    # Latency SLO lives in live health/sync guards, not a deleted runbook novel.

    raw_hits = routers_use_raw_sql()
    if raw_hits:
        failures.extend([f"B.11 raw SQL in routers: {hit}" for hit in raw_hits])

    idor = IDOR_TEST.read_text(encoding="utf-8")
    for needle in ("cross-tenant", "MerchantOrdersService", "tracking"):
        if needle.lower() not in idor.lower():
            failures.append(f"B.12 IDOR test missing {needle!r}")

    slo_script = ROOT / "scripts/verify_day_plan_scorecard.py"
    if slo_script.is_file():
        proc = subprocess.run([sys.executable, str(slo_script)], cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            failures.append("B.6 day-plan scorecard guard (verify_day_plan_scorecard) failed")
            if proc.stdout:
                failures.append(proc.stdout.strip()[:400])

    print("Observability guard (Appendix B.1–B.3, B.5–B.9, B.11–B.12)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — correlation IDs, Prometheus, queue depth, day-plan scorecard, security headers, IDOR tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
