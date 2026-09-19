#!/usr/bin/env python3
"""§11.2 enterprise identity + §11.3 product — dev-layer guards."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "saml scim adr": ROOT / "docs/architecture/ADR-017-enterprise-saml-scim.md",
    "enterprise billing doc": ROOT / "docs/compliance/ENTERPRISE_BILLING.md",
    "sla doc": ROOT / "docs/compliance/SLA.md",
    "priority support doc": ROOT / "docs/compliance/PRIORITY_SUPPORT.md",
    "parent migration": ROOT / "apps/api/alembic/versions/r1s2t3u4v5w6_parent_merchant.py",
    "merchant service": ROOT / "apps/api/src/porterchain_api/admin_engine/merchant_service.py",
    "merchants router": ROOT / "apps/api/src/porterchain_api/routers/merchants.py",
    "claims query": ROOT / "apps/api/src/porterchain_api/support_engine/claims_query.py",
    "claims router": ROOT / "apps/api/src/porterchain_api/routers/admin/claims.py",
    "drivers admin router": ROOT / "apps/api/src/porterchain_api/routers/drivers_admin.py",
    "test file": ROOT / "apps/api/tests/test_enterprise_identity.py",
}


def main() -> int:
    failures: list[str] = []
    for label, path in PATHS.items():
        if path.suffix == ".md" and not path.is_file():
            continue
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    adr_path = PATHS["saml scim adr"]
    if adr_path.is_file():
        adr = adr_path.read_text(encoding="utf-8")
        if "Clerk Enterprise SAML" not in adr or "SCIM" not in adr:
            failures.append("ADR-017 incomplete")

    billing_path = PATHS["enterprise billing doc"]
    if billing_path.is_file():
        billing = billing_path.read_text(encoding="utf-8")
        if "NET_30" not in billing or "PATCH /v1/admin/merchants" not in billing:
            failures.append("enterprise billing doc incomplete")

    svc = PATHS["merchant service"].read_text(encoding="utf-8")
    for token in ("list_subsidiaries", "parent_merchant_id", "support_tier"):
        if token not in svc:
            failures.append(f"merchant service missing {token}")

    merchants = PATHS["merchants router"].read_text(encoding="utf-8")
    if "/subsidiaries" not in merchants:
        failures.append("merchants router missing subsidiaries endpoint")

    migration = PATHS["parent migration"].read_text(encoding="utf-8")
    if "parent_merchant_id" not in migration:
        failures.append("parent merchant migration missing")

    claims_q = PATHS["claims query"].read_text(encoding="utf-8")
    for fn in ("dashboard", "reports", "export_csv"):
        if fn not in claims_q:
            failures.append(f"claims query missing {fn}")

    claims_r = PATHS["claims router"].read_text(encoding="utf-8")
    for route in ("/claims/dashboard", "/claims/bulk", "/claims/export.csv", "/claims/{claim_id}/insurance"):
        if route not in claims_r:
            failures.append(f"claims router missing {route}")

    drivers = PATHS["drivers admin router"].read_text(encoding="utf-8")
    if "/documents" not in drivers or "add_document" not in drivers:
        failures.append("driver compliance documents API missing")

    models = (ROOT / "apps/api/src/porterchain_api/merchant_models.py").read_text(encoding="utf-8")
    if "parent_merchant_id" not in models:
        failures.append("merchant model missing parent_merchant_id")

    print("Enterprise identity + product guard (§11.2 · §11.3)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — SAML ADR, parent orgs, NET-30, SLA docs, claims export, driver docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
