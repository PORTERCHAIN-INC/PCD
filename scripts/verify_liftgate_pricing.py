#!/usr/bin/env python3
"""§8.1.7 — Construction liftgate pricing surcharge in porterchain_pricing."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "services/pricing-engine/porterchain_pricing/catalog.py"
ENGINE = ROOT / "services/pricing-engine/porterchain_pricing/engine/__init__.py"
TYPES = ROOT / "services/pricing-engine/porterchain_pricing/types.py"
SCHEMA = ROOT / "apps/api/src/porterchain_api/schemas_merchant.py"
BOOKING = ROOT / "apps/api/src/porterchain_api/merchant_engine/booking_service.py"
UI = ROOT / "apps/merchant-portal/src/components/booking/BookDeliveryClient.tsx"
TEST = ROOT / "services/pricing-engine/tests/test_liftgate_pricing.py"


def main() -> int:
    failures: list[str] = []

    for label, path in (
        ("catalog", CATALOG),
        ("engine", ENGINE),
        ("types", TYPES),
        ("schema", SCHEMA),
        ("booking service", BOOKING),
        ("merchant UI", UI),
        ("unit test", TEST),
    ):
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    catalog = CATALOG.read_text(encoding="utf-8")
    if "LIFTGATE_SURCHARGE_CENTS" not in catalog:
        failures.append("catalog missing LIFTGATE_SURCHARGE_CENTS")

    engine = ENGINE.read_text(encoding="utf-8")
    if "requires_liftgate" not in engine or 'add_item("liftgate"' not in engine:
        failures.append("pricing engine missing liftgate surcharge line item")

    schema = SCHEMA.read_text(encoding="utf-8")
    if "requires_liftgate" not in schema:
        failures.append("MerchantBookDeliveryRequest missing requires_liftgate")

    ui = UI.read_text(encoding="utf-8")
    if "requiresLiftgate" not in ui or "requires_liftgate" not in ui:
        failures.append("BookDeliveryClient missing liftgate checkbox")

    booking = BOOKING.read_text(encoding="utf-8")
    if "requires_liftgate=body.requires_liftgate" not in booking:
        failures.append("booking service must pass requires_liftgate to PricingRequest")

    print("Liftgate pricing guard (§8.1.7)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — catalog surcharge, engine line item, merchant booking UI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
