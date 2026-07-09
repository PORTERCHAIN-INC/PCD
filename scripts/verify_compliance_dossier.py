#!/usr/bin/env python3
"""§8.1.13 — Compliance PDF dossier (reporting/compliance)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "reporting module": ROOT / "apps/api/src/porterchain_api/reporting/compliance_dossier.py",
    "admin orders service": ROOT / "apps/api/src/porterchain_api/admin_engine/orders_service.py",
    "merchant orders service": ROOT / "apps/api/src/porterchain_api/merchant_engine/orders_service.py",
    "admin router": ROOT / "apps/api/src/porterchain_api/routers/admin/orders.py",
    "merchant router": ROOT / "apps/api/src/porterchain_api/routers/merchant/orders_tracking.py",
    "unit test": ROOT / "apps/api/tests/test_compliance_dossier.py",
}


def main() -> int:
    failures: list[str] = []
    for label, path in PATHS.items():
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    dossier = PATHS["reporting module"].read_text(encoding="utf-8")
    if "build_compliance_dossier_pdf" not in dossier or "render_compliance_pdf" not in dossier:
        failures.append("compliance_dossier missing PDF builders")

    admin_svc = PATHS["admin orders service"].read_text(encoding="utf-8")
    if "compliance_dossier_pdf" not in admin_svc:
        failures.append("AdminOrdersService missing compliance_dossier_pdf")

    merchant_svc = PATHS["merchant orders service"].read_text(encoding="utf-8")
    if "compliance_dossier_pdf" not in merchant_svc:
        failures.append("MerchantOrdersService missing compliance_dossier_pdf")

    admin_router = PATHS["admin router"].read_text(encoding="utf-8")
    if "/compliance-dossier.pdf" not in admin_router:
        failures.append("admin orders router missing compliance-dossier.pdf endpoint")

    merchant_router = PATHS["merchant router"].read_text(encoding="utf-8")
    if "/compliance-dossier.pdf" not in merchant_router:
        failures.append("merchant orders router missing compliance-dossier.pdf endpoint")

    print("Compliance PDF dossier guard (§8.1.13)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — reporting/compliance PDF, admin + merchant download endpoints, tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
