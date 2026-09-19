#!/usr/bin/env python3
"""§7 PLT-G4 — integration adapter interface stability guard."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOC = ROOT / "docs/integrations/ADAPTER_INTERFACE.md"
BASE = ROOT / "apps/api/src/porterchain_api/integrations/base_adapter.py"
NETSUITE = ROOT / "apps/api/src/porterchain_api/integrations/netsuite_adapter.py"
NETSUITE_TEST = ROOT / "apps/api/tests/test_netsuite_zapier.py"
PARTNER = ROOT / "docs/api/PARTNER_GUIDE.md"


def main() -> int:
    failures: list[str] = []

    for label, path in (
        ("base adapter", BASE),
        ("netsuite adapter", NETSUITE),
        ("netsuite test", NETSUITE_TEST),
    ):
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    if DOC.is_file():
        doc = DOC.read_text(encoding="utf-8")
        for needle in ("MerchantBookDeliveryRequest", "map_", "2 quarters", "netsuite_adapter"):
            if needle not in doc:
                failures.append(f"ADAPTER_INTERFACE.md missing {needle!r}")

    netsuite = NETSUITE.read_text(encoding="utf-8")
    if "map_netsuite_fulfillment" not in netsuite:
        failures.append("netsuite_adapter missing map_netsuite_fulfillment")

    base = BASE.read_text(encoding="utf-8")
    if "ErpFulfillmentAdapter" not in base:
        failures.append("base_adapter missing ErpFulfillmentAdapter protocol")

    if PARTNER.is_file():
        partner = PARTNER.read_text(encoding="utf-8")
        if "integration" not in partner.lower():
            failures.append("PARTNER_GUIDE.md should reference integrations")

    print("Integration adapter guard (PLT-G4)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — adapter interface doc, protocol, NetSuite reference implementation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
