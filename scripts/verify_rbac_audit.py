#!/usr/bin/env python3
"""§11.1.6 RBAC matrix = code · §11.1.7 audit export API — dev-layer guards."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "rbac matrix doc": ROOT / "RBAC_MATRIX.md",
    "unified rbac": ROOT / "apps/api/src/porterchain_api/auth/rbac.py",
    "admin rbac": ROOT / "apps/api/src/porterchain_api/admin_engine/rbac.py",
    "merchant rbac": ROOT / "apps/api/src/porterchain_api/merchant_engine/rbac.py",
    "audit export service": ROOT / "apps/api/src/porterchain_api/admin_engine/audit_export_service.py",
    "audit router": ROOT / "apps/api/src/porterchain_api/routers/admin/audit.py",
    "test file": ROOT / "apps/api/tests/test_audit_export.py",
}


def main() -> int:
    failures: list[str] = []
    for label, path in PATHS.items():
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    admin_rbac = PATHS["admin rbac"].read_text(encoding="utf-8")
    if "MODULE_PERMISSIONS" not in admin_rbac or "require_module" not in admin_rbac:
        failures.append("admin rbac missing MODULE_PERMISSIONS / require_module")

    merchant_rbac = PATHS["merchant rbac"].read_text(encoding="utf-8")
    if "MODULE_PERMISSIONS" not in merchant_rbac:
        failures.append("merchant rbac missing MODULE_PERMISSIONS")

    unified = PATHS["unified rbac"].read_text(encoding="utf-8")
    if "ADMIN_MODULES" not in unified or "MERCHANT_MODULES" not in unified:
        failures.append("auth/rbac.py missing admin + merchant module imports")

    matrix = PATHS["rbac matrix doc"].read_text(encoding="utf-8")
    for token in ("require_module", "admin_engine/rbac.py", "Enterprise roles"):
        if token not in matrix:
            failures.append(f"RBAC_MATRIX.md missing {token}")

    audit_svc = PATHS["audit export service"].read_text(encoding="utf-8")
    for fn in ("list_logs", "export_bundle", "export_csv", "domain_events"):
        if fn not in audit_svc:
            failures.append(f"audit export service missing {fn}")

    audit_router = PATHS["audit router"].read_text(encoding="utf-8")
    for route in ("/audit-logs", "/audit-logs/export", "/audit-logs/export.csv", "/audit-logs/domain-events"):
        if route not in audit_router:
            failures.append(f"audit router missing {route}")

    admin_init = (ROOT / "apps/api/src/porterchain_api/routers/admin/__init__.py").read_text(encoding="utf-8")
    if "audit" not in admin_init:
        failures.append("admin __init__ missing audit import")

    deps = (ROOT / "apps/api/src/porterchain_api/routers/admin/_deps.py").read_text(encoding="utf-8")
    if "_audit_export" not in deps:
        failures.append("admin _deps missing _audit_export")

    print("RBAC + audit export guard (§11.1.6 · §11.1.7)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — RBAC matrices in code, admin audit export API")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
