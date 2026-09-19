#!/usr/bin/env python3
"""Authz guards — SpiceDB SSOT + ban deleted login/RBAC surfaces."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "authz ADR": ROOT / "docs/architecture/auth-clerk-spicedb.md",
    "spicedb schema": ROOT / "apps/api/src/porterchain_api/authz/schema.zed",
    "platform roles": ROOT / "apps/api/src/porterchain_api/authz/platform_roles.py",
    "admin rbac": ROOT / "apps/api/src/porterchain_api/admin_engine/rbac.py",
    "merchant rbac": ROOT / "apps/api/src/porterchain_api/merchant_engine/rbac.py",
    "audit export service": ROOT / "apps/api/src/porterchain_api/admin_engine/audit_export_service.py",
    "audit router": ROOT / "apps/api/src/porterchain_api/routers/admin/audit.py",
    "test file": ROOT / "apps/api/tests/test_audit_export.py",
    "retired matrix stub": ROOT / "RBAC_MATRIX.md",
    "openapi": ROOT / "docs/api/openapi.json",
    "session-context ts": ROOT / "packages/auth/src/session-context.ts",
}


def main() -> int:
    failures: list[str] = []
    for label, path in PATHS.items():
        if path.suffix == ".md" and not path.is_file():
            continue
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    admin_rbac = PATHS["admin rbac"].read_text(encoding="utf-8")
    if "require_module" not in admin_rbac:
        failures.append("admin rbac missing require_module")
    if 'permission="admin"' in admin_rbac and "or client.check" in admin_rbac:
        failures.append("require_module must not OR-bypass via platform#admin")

    schema = PATHS["spicedb schema"].read_text(encoding="utf-8")
    if "definition " not in schema:
        failures.append("spicedb schema missing definitions")
    if "relation staff:" in schema and "relation super_admin:" not in schema:
        failures.append("schema still uses monolithic staff without role relations")
    if "permission system_all = super_admin" not in schema:
        failures.append("schema missing system_all = super_admin only")
    if "permission portal =" not in schema:
        failures.append("schema missing portal permission (staff entry)")
    if re.search(r"permission admin\s*=", schema):
        failures.append("schema must not define permission admin (collides with relation admin)")
    # Collisions are only illegal within the same definition — scan platform block.
    platform_block = re.search(
        r"definition platform \{(.*?)\}",
        schema,
        flags=re.DOTALL,
    )
    if platform_block:
        body = platform_block.group(1)
        if re.search(r"(?m)^\s*permission finance\s*=", body):
            failures.append("schema must use mod_finance (collides with relation finance)")
        if re.search(r"(?m)^\s*permission support\s*=", body):
            failures.append("schema must use mod_support (collides with relation support)")
        if "permission mod_finance =" not in body or "permission mod_support =" not in body:
            failures.append("schema missing mod_finance / mod_support permissions")
    else:
        failures.append("schema missing definition platform")

    roles = PATHS["platform roles"].read_text(encoding="utf-8")
    if "SYSTEM_ALL_ROLES" not in roles:
        failures.append("platform_roles.py missing SYSTEM_ALL_ROLES")
    if "to_schema_permission" not in roles:
        failures.append("platform_roles.py missing to_schema_permission")

    adr_path = PATHS["authz ADR"]
    if adr_path.is_file():
        adr = adr_path.read_text(encoding="utf-8")
        if "SpiceDB" not in adr:
            failures.append("auth-clerk-spicedb.md missing SpiceDB")

    stub_path = PATHS["retired matrix stub"]
    if stub_path.is_file():
        stub = stub_path.read_text(encoding="utf-8")
        if "RETIRED" not in stub and "superseded" not in stub.lower():
            failures.append("RBAC_MATRIX.md must mark retirement / SpiceDB SSOT")

    openapi = json.loads(PATHS["openapi"].read_text(encoding="utf-8"))
    for path in openapi.get("paths", {}):
        if re.search(r"/v1/auth/(admin|merchant|customer|driver)/access$", path):
            failures.append(f"openapi still documents deleted {path}")

    session_ts = PATHS["session-context ts"].read_text(encoding="utf-8")
    if 'portal === "admin"' not in session_ts:
        failures.append("canAccessPortal must treat system:all as admin-only")

    prod_compose = ROOT / "infrastructure/deploy/docker-compose.prod.yml"
    if prod_compose.is_file():
        prod = prod_compose.read_text(encoding="utf-8")
        if "spicedb:" not in prod or "authzed/spicedb:" not in prod:
            failures.append("prod compose must define SpiceDB service (not only env vars)")
        if "SPICEDB_REQUIRED: ${SPICEDB_REQUIRED:-true}" not in prod:
            failures.append("prod compose must default SPICEDB_REQUIRED=true")
        if "spicedb-db-init:" not in prod:
            failures.append("prod compose missing spicedb-db-init (CREATE DATABASE)")

    # Forbidden legacy paths
    for banned in (
        ROOT / "apps/api/src/porterchain_api/auth/enterprise_rbac.py",
        ROOT / "apps/api/src/porterchain_api/auth/rbac.py",
        ROOT / "apps/api/src/porterchain_api/auth/principal_resolver.py",
        ROOT / "apps/api/src/porterchain_api/auth/permission_adapter.py",
        ROOT / "apps/api/src/porterchain_api/routers/admin/permission_overrides.py",
    ):
        if banned.is_file():
            failures.append(f"legacy file must be deleted: {banned.relative_to(ROOT)}")

    # Ban resurrection of wrong-portal helpers in auth package
    auth_pkg = ROOT / "packages/auth/src"
    for py in auth_pkg.rglob("*.ts"):
        text = py.read_text(encoding="utf-8")
        if "wrongPortalMessage" in text or "checkPortalAccess" in text:
            failures.append(f"resurrected wrong-portal helper in {py.relative_to(ROOT)}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("ok: authz audit paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
