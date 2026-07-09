#!/usr/bin/env python3
"""§8.2 data moat + §8.3 switching costs — dev-layer guards."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "data moat reporting": ROOT / "apps/api/src/porterchain_api/reporting/data_moat.py",
    "switching costs reporting": ROOT / "apps/api/src/porterchain_api/reporting/switching_costs.py",
    "admin data moat service": ROOT / "apps/api/src/porterchain_api/admin_engine/data_moat_service.py",
    "admin data moat router": ROOT / "apps/api/src/porterchain_api/routers/admin/data_moat.py",
    "merchant reports router": ROOT / "apps/api/src/porterchain_api/routers/merchant/reports.py",
    "merchant integrations router": ROOT / "apps/api/src/porterchain_api/routers/merchant/integrations.py",
    "merchant settings router": ROOT / "apps/api/src/porterchain_api/routers/merchant/settings.py",
    "admin pricing router": ROOT / "apps/api/src/porterchain_api/routers/admin/pricing.py",
    "merchant billing router": ROOT / "apps/api/src/porterchain_api/routers/merchant/billing.py",
    "merchant rbac": ROOT / "apps/api/src/porterchain_api/merchant_engine/rbac.py",
    "test file": ROOT / "apps/api/tests/test_data_moat_switching.py",
}


def main() -> int:
    failures: list[str] = []
    for label, path in PATHS.items():
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    data_moat = PATHS["data moat reporting"].read_text(encoding="utf-8")
    for fn in ("dwell_time_dataset", "network_sla_benchmark", "margin_intelligence", "own_ping_eta"):
        if fn not in data_moat:
            failures.append(f"data_moat missing {fn}")

    switching = PATHS["switching costs reporting"].read_text(encoding="utf-8")
    for fn in ("integration_depth", "sla_history_12mo", "custom_tariffs_summary", "rbac_and_audit_snapshot"):
        if fn not in switching:
            failures.append(f"switching_costs missing {fn}")

    admin_router = PATHS["admin data moat router"].read_text(encoding="utf-8")
    if "/data-moat/network" not in admin_router or "own-ping-eta" not in admin_router:
        failures.append("admin data moat router incomplete")

    reports = PATHS["merchant reports router"].read_text(encoding="utf-8")
    if "/reports/sla-history" not in reports or "/reports/switching-costs" not in reports:
        failures.append("merchant reports missing SLA / switching-costs endpoints")

    integrations = PATHS["merchant integrations router"].read_text(encoding="utf-8")
    if "/integrations/depth" not in integrations:
        failures.append("merchant integrations missing depth endpoint")

    settings = PATHS["merchant settings router"].read_text(encoding="utf-8")
    if "/audit-logs" not in settings:
        failures.append("merchant settings missing audit-logs endpoint")

    pricing = PATHS["admin pricing router"].read_text(encoding="utf-8")
    if "/pricing/contracts" not in pricing:
        failures.append("admin pricing missing merchant contracts")

    billing = PATHS["merchant billing router"].read_text(encoding="utf-8")
    if "/billing/contract" not in billing:
        failures.append("merchant billing missing contract endpoint")

    rbac = PATHS["merchant rbac"].read_text(encoding="utf-8")
    if "permissions_catalog" not in rbac or "MODULE_PERMISSIONS" not in rbac:
        failures.append("merchant RBAC matrix missing")

    print("Data moat + switching costs guard (§8.2 · §8.3)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — data moat metrics, switching-cost APIs, tariffs, RBAC audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
