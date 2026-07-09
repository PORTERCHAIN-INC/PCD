#!/usr/bin/env python3
"""§8.1.6 — Construction jobsite: site access notes on merchant booking flow."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "apps/api/src/porterchain_api/schemas_merchant.py"
SITE_ACCESS = ROOT / "apps/api/src/porterchain_api/booking_engine/site_access.py"
BOOKING_SVC = ROOT / "apps/api/src/porterchain_api/merchant_engine/booking_service.py"
FLOW_SVC = ROOT / "apps/api/src/porterchain_api/merchant_engine/booking_flow_service.py"
MERCHANT_UI = ROOT / "apps/merchant-portal/src/components/booking/BookDeliveryClient.tsx"
MERCHANT_API = ROOT / "apps/merchant-portal/src/lib/api.ts"
TEST = ROOT / "apps/api/tests/test_site_access_notes.py"


def main() -> int:
    failures: list[str] = []

    for label, path in (
        ("schema", SCHEMA),
        ("site_access helper", SITE_ACCESS),
        ("booking service", BOOKING_SVC),
        ("booking flow", FLOW_SVC),
        ("merchant UI", MERCHANT_UI),
        ("merchant api types", MERCHANT_API),
        ("unit test", TEST),
    ):
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    schema_text = SCHEMA.read_text(encoding="utf-8")
    if "site_access_notes" not in schema_text:
        failures.append("MerchantBookDeliveryRequest missing site_access_notes")

    flow_text = FLOW_SVC.read_text(encoding="utf-8")
    if "enrich_dropoff" not in flow_text or "extract_site_access_notes" not in flow_text:
        failures.append("booking_flow_service must enrich/extract site_access_notes")

    ui_text = MERCHANT_UI.read_text(encoding="utf-8")
    if "siteAccessNotes" not in ui_text or "Site access" not in ui_text:
        failures.append("BookDeliveryClient missing site access field")
    if "site_access_notes" not in ui_text:
        failures.append("BookDeliveryClient must send site_access_notes in payload")

    api_text = MERCHANT_API.read_text(encoding="utf-8")
    if "site_access_notes" not in api_text:
        failures.append("BookDeliveryPayload missing site_access_notes")

    site_text = SITE_ACCESS.read_text(encoding="utf-8")
    if not re.search(r'SITE_ACCESS_DROP_KEY\s*=\s*"site_access_notes"', site_text):
        failures.append("site_access drop key must be site_access_notes")

    print("Construction site access guard (§8.1.6)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — schema, API persistence, merchant booking UI, tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
