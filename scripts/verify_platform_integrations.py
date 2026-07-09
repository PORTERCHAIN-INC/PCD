#!/usr/bin/env python3
"""§7.2.3 NetSuite MVP · §7.2.4 Zapier · §7.3 platform metrics guards."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "netsuite readme": ROOT / "integrations/netsuite/README.md",
    "netsuite schema": ROOT / "integrations/netsuite/inbound.schema.json",
    "netsuite sample": ROOT / "integrations/netsuite/samples/fulfillment.json",
    "netsuite adapter": ROOT / "apps/api/src/porterchain_api/integrations/netsuite_adapter.py",
    "zapier readme": ROOT / "integrations/zapier/README.md",
    "zapier templates": ROOT / "integrations/zapier/templates.json",
    "zapier catalog": ROOT / "apps/api/src/porterchain_api/integrations/zapier_catalog.py",
    "merchant integrations router": ROOT / "apps/api/src/porterchain_api/routers/merchant/integrations.py",
    "platform metrics service": ROOT / "apps/api/src/porterchain_api/admin_engine/platform_metrics_service.py",
    "admin platform router": ROOT / "apps/api/src/porterchain_api/routers/admin/platform_metrics.py",
    "partners json": ROOT / "website/src/content/partners.json",
    "gateway erp": ROOT / "apps/api/src/porterchain_api/gateway_engine/merchant_api.py",
    "test file": ROOT / "apps/api/tests/test_netsuite_zapier.py",
}


def main() -> int:
    failures: list[str] = []
    for label, path in PATHS.items():
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    router = PATHS["merchant integrations router"].read_text(encoding="utf-8")
    for route in ("/integrations/netsuite/sync", "/integrations/zapier/templates", "/integrations/netsuite/setup"):
        if route not in router:
            failures.append(f"merchant router missing {route}")

    gateway = PATHS["gateway erp"].read_text(encoding="utf-8")
    if '"id": "netsuite"' not in gateway:
        failures.append("ERP_READINESS missing netsuite")

    admin_router = PATHS["admin platform router"].read_text(encoding="utf-8")
    if "/platform-metrics" not in admin_router:
        failures.append("admin missing /platform-metrics")

    partners = json.loads(PATHS["partners json"].read_text(encoding="utf-8"))
    partner_list = partners.get("partners") or partners.get("logos") or []
    if len(partner_list) < 3:
        failures.append("partners.json needs ≥3 partner logos")

    templates = json.loads(PATHS["zapier templates"].read_text(encoding="utf-8"))
    if len(templates.get("templates") or []) < 4:
        failures.append("zapier templates.json needs ≥4 templates")

    print("Platform integrations guard (§7.2.3 · §7.2.4 · §7.3)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — NetSuite MVP, Zapier catalog, platform metrics, partner logos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
