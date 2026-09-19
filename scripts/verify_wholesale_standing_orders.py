#!/usr/bin/env python3
"""§8.1.10 · §8.1.11 — Wholesale route templates + recurring standing orders."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE_SVC = ROOT / "apps/api/src/porterchain_api/admin_engine/route_template_service.py"
ROUTE_ROUTER = ROOT / "apps/api/src/porterchain_api/routers/admin/route_templates.py"
ADMIN_MODELS = ROOT / "apps/api/src/porterchain_api/admin_models.py"
STANDING_SVC = ROOT / "apps/api/src/porterchain_api/merchant_engine/standing_order_service.py"
STANDING_ROUTER = ROOT / "apps/api/src/porterchain_api/routers/merchant/standing_orders.py"
MERCHANT_MODELS = ROOT / "apps/api/src/porterchain_api/merchant_models.py"
MIGRATION = ROOT / "apps/api/alembic/versions/q0r1s2t3u4v5_standing_orders.py"
WORKER = ROOT / "apps/worker/run.py"
TEST_ROUTE = ROOT / "apps/api/tests/test_route_templates.py"
TEST_STANDING = ROOT / "apps/api/tests/test_standing_orders.py"


def main() -> int:
    failures: list[str] = []

    for label, path in (
        ("route template service", ROUTE_SVC),
        ("admin route-templates router", ROUTE_ROUTER),
        ("standing order service", STANDING_SVC),
        ("merchant standing-orders router", STANDING_ROUTER),
        ("standing_orders migration", MIGRATION),
        ("route template test", TEST_ROUTE),
        ("standing order test", TEST_STANDING),
    ):
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    admin_text = ADMIN_MODELS.read_text(encoding="utf-8")
    if "RouteTemplate = RouteCenterTemplate" not in admin_text:
        failures.append("admin_models missing RouteTemplate alias")

    route_svc_text = ROUTE_SVC.read_text(encoding="utf-8") if ROUTE_SVC.is_file() else ""
    if 'WHOLESALE_TYPE = "wholesale"' not in route_svc_text:
        failures.append("route_template_service must filter template_type wholesale")

    route_router_text = ROUTE_ROUTER.read_text(encoding="utf-8") if ROUTE_ROUTER.is_file() else ""
    if "/route-templates" not in route_router_text:
        failures.append("admin router missing /route-templates endpoints")

    merchant_text = MERCHANT_MODELS.read_text(encoding="utf-8")
    if "class StandingOrder" not in merchant_text:
        failures.append("merchant_models missing StandingOrder")

    standing_svc_text = STANDING_SVC.read_text(encoding="utf-8") if STANDING_SVC.is_file() else ""
    if "run_due_orders" not in standing_svc_text:
        failures.append("standing_order_service missing run_due_orders")

    worker_text = WORKER.read_text(encoding="utf-8")
    if "_drain_standing_orders" not in worker_text:
        failures.append("worker missing _drain_standing_orders cron")
    if not re.search(r"STANDING_ORDERS_INTERVAL_SECONDS\s*=\s*300", worker_text):
        failures.append("worker missing STANDING_ORDERS_INTERVAL_SECONDS")

    standing_router_text = STANDING_ROUTER.read_text(encoding="utf-8") if STANDING_ROUTER.is_file() else ""
    if "/standing-orders" not in standing_router_text:
        failures.append("merchant router missing /standing-orders endpoints")

    print("Wholesale route templates + standing orders guard (§8.1.10 · §8.1.11)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — admin route templates, standing orders API, worker cron, tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
