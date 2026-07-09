#!/usr/bin/env python3
"""§7.2.5 — Merchant integration marketplace UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS_CLIENT = ROOT / "apps/merchant-portal/src/components/integrations/IntegrationsClient.tsx"
GATEWAY = ROOT / "apps/api/src/porterchain_api/gateway_engine/merchant_api.py"


def main() -> int:
    failures: list[str] = []

    if not INTEGRATIONS_CLIENT.is_file():
        failures.append("missing IntegrationsClient.tsx")
    else:
        text = INTEGRATIONS_CLIENT.read_text(encoding="utf-8")
        if "Marketplace" not in text:
            failures.append("integrations UI missing Marketplace tab label")
        if "Integration marketplace" not in text:
            failures.append("integrations UI missing marketplace section heading")

    if GATEWAY.is_file():
        gateway = GATEWAY.read_text(encoding="utf-8")
        for platform in ("shopify", "woocommerce", "netsuite"):
            if f'"id": "{platform}"' not in gateway:
                failures.append(f"gateway missing {platform} in ERP_READINESS")

    print("Integration marketplace guard (§7.2.5)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: merchant portal marketplace tab + Shopify/WooCommerce readiness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
