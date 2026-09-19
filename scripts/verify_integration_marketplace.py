#!/usr/bin/env python3
"""Integrations are Shopify + partner API — not an ERP marketplace."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS_CLIENT = ROOT / "apps/merchant-portal/src/components/integrations/IntegrationsClient.tsx"
SHOPIFY_APP = ROOT / "apps/merchant-portal/src/app/(portal)/shopify/page.tsx"
GATEWAY = ROOT / "apps/api/src/porterchain_api/gateway_engine/merchant_api.py"


def main() -> int:
    failures: list[str] = []

    if not INTEGRATIONS_CLIENT.is_file():
        failures.append("missing IntegrationsClient.tsx")
    else:
        text = INTEGRATIONS_CLIENT.read_text(encoding="utf-8")
        if "Marketplace" in text or "ERP readiness" in text:
            failures.append("integrations UI still advertises an ERP marketplace")
        if "X-Api-Key" not in text:
            failures.append("integrations UI missing partner API key copy")
        if "ShopifyConnectCard" not in text:
            failures.append("integrations UI missing Shopify card")
        if "/shopify" not in text:
            failures.append("integrations UI missing /shopify setup link")

    if not SHOPIFY_APP.is_file():
        failures.append("missing merchant-portal /shopify app page")

    if GATEWAY.is_file():
        gateway = GATEWAY.read_text(encoding="utf-8")
        for platform in ("shopify", "woocommerce", "netsuite"):
            if f'"id": "{platform}"' not in gateway:
                failures.append(f"gateway missing {platform} in ERP_READINESS")
        if '"status": "not_offered"' not in gateway:
            failures.append("non-Shopify ERP rows must be not_offered")

    print("Integration honesty guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: Shopify + merchant-api; no ERP marketplace theater")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
