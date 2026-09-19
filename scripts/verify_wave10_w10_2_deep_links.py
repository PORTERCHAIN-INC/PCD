#!/usr/bin/env python3
"""Wave 10 w10-2 guard — Universal Links (AASA) + Android App Links."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AASA = ROOT / "website/src/app/.well-known/apple-app-site-association/route.ts"
ASSETLINKS = ROOT / "website/src/app/.well-known/assetlinks.json/route.ts"
CONFIG = ROOT / "website/src/lib/mobile-deep-links.ts"
CUSTOMER_APP = ROOT / "apps/mobile-customer/app.json"
DRIVER_APP = ROOT / "apps/mobile-driver/app.json"
CUSTOMER_TSX = ROOT / "apps/mobile-customer/App.tsx"
DRIVER_TSX = ROOT / "apps/mobile-driver/App.tsx"


def main() -> int:
    failures: list[str] = []

    config = CONFIG.read_text(encoding="utf-8")
    if "buildAppleAppSiteAssociationDocument" not in config:
        failures.append("mobile-deep-links.ts missing AASA builder")
    if "com.porterchain.customer" not in config or "com.porterchain.PCD" not in config:
        failures.append("mobile-deep-links.ts missing bundle ids")

    aasa = AASA.read_text(encoding="utf-8")
    if "buildAppleAppSiteAssociationDocument" not in aasa:
        failures.append("apple-app-site-association route missing")

    asset = ASSETLINKS.read_text(encoding="utf-8")
    if "buildAndroidAssetLinks" not in asset:
        failures.append("assetlinks.json route missing")

    customer = CUSTOMER_APP.read_text(encoding="utf-8")
    if "associatedDomains" not in customer or "intentFilters" not in customer:
        failures.append("mobile-customer app.json missing universal/app links")

    driver = DRIVER_APP.read_text(encoding="utf-8")
    if "associatedDomains" not in driver or "driver-invite" not in driver:
        failures.append("mobile-driver app.json missing universal/app links")

    customer_tsx = CUSTOMER_TSX.read_text(encoding="utf-8")
    if "expo-linking" not in customer_tsx or "Linking.addEventListener" not in customer_tsx:
        failures.append("mobile-customer App.tsx missing Linking handler")

    driver_tsx = DRIVER_TSX.read_text(encoding="utf-8")
    driver_src = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (ROOT / "apps/mobile-driver/src").rglob("*.ts*")
        if "node_modules" not in p.parts
    )
    driver_blob = driver_tsx + "\n" + driver_src
    if "driver-invite" not in driver_blob or "expo-linking" not in driver_blob:
        failures.append("mobile-driver missing invite deep link handler (App/hooks/linking)")
    if "useDriverDeepLinks" not in driver_blob and "Linking.addEventListener" not in driver_blob:
        failures.append("mobile-driver missing Linking subscription")

    print("Wave 10 w10-2 guard (Universal / App Links)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: AASA, assetlinks, Expo associatedDomains/intentFilters, Linking handlers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
