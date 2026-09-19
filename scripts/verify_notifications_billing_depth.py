#!/usr/bin/env python3
"""Appendix D.3–D.4, D.6–D.8 — notifications + billing depth guards."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "template catalog doc": ROOT / "docs/notifications/NOTIFICATION_TEMPLATE_CATALOG.md",
    "templates module": ROOT / "apps/api/src/porterchain_api/notification_engine/templates.py",
    "preference service": ROOT / "apps/api/src/porterchain_api/notification_engine/preference_service.py",
    "notification engine": ROOT / "apps/api/src/porterchain_api/notification_engine/engine.py",
    "billing ledger model": ROOT / "apps/api/src/porterchain_api/billing_engine/models.py",
    "driver finance": ROOT / "apps/api/src/porterchain_api/billing_engine/driver_finance_service.py",
    "merchant billing": ROOT / "apps/api/src/porterchain_api/merchant_engine/billing_service.py",
    "enterprise billing doc": ROOT / "docs/compliance/ENTERPRISE_BILLING.md",
}


def main() -> int:
    failures: list[str] = []

    for label, path in PATHS.items():
        if path.suffix == ".md" and not path.is_file():
            continue
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    catalog_path = PATHS["template catalog doc"]
    if catalog_path.is_file():
        catalog = catalog_path.read_text(encoding="utf-8")
        if "templates.py" not in catalog or "booking_confirmed" not in catalog:
            failures.append("NOTIFICATION_TEMPLATE_CATALOG.md incomplete")

    prefs = PATHS["preference service"].read_text(encoding="utf-8")
    if "is_enabled" not in prefs or "DEFAULT_CATEGORIES" not in prefs:
        failures.append("preference_service incomplete")

    engine = PATHS["notification engine"].read_text(encoding="utf-8")
    if "is_enabled" not in engine:
        failures.append("notification engine must enforce preferences via is_enabled")

    ledger = PATHS["billing ledger model"].read_text(encoding="utf-8")
    if "class BillingLedgerEntry" not in ledger:
        failures.append("BillingLedgerEntry model missing")

    driver = PATHS["driver finance"].read_text(encoding="utf-8")
    if "DriverFinanceService" not in driver or "driver_earnings_snapshot" not in driver:
        failures.append("driver_finance_service incomplete")

    billing = PATHS["merchant billing"].read_text(encoding="utf-8")
    for needle in ("net_terms_days", "BillingLedgerEntry", "list_invoices_enriched"):
        if needle not in billing:
            failures.append(f"merchant billing_service missing {needle}")

    ent_path = PATHS["enterprise billing doc"]
    if ent_path.is_file():
        ent = ent_path.read_text(encoding="utf-8")
        if "NET-30" not in ent and "NET_30" not in ent:
            failures.append("ENTERPRISE_BILLING.md missing NET-30 terms")

    templates = PATHS["templates module"].read_text(encoding="utf-8")
    if "TEMPLATES:" not in templates or "TEMPLATE_META" not in templates:
        failures.append("templates.py missing TEMPLATES/TEMPLATE_META")

    notif_script = ROOT / "scripts/verify_notification_catalog.py"
    if notif_script.is_file():
        proc = subprocess.run([sys.executable, str(notif_script)], cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0:
            failures.append("verify_notification_catalog.py failed (D.3 event-router path)")
    else:
        failures.append("missing verify_notification_catalog.py")

    print("Notifications + billing depth guard (Appendix D.3–D.4, D.6–D.8)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — template catalog, preferences, ledger, driver settlement, NET invoicing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
