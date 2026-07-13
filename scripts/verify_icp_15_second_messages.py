#!/usr/bin/env python3
"""ICP 15-second test prep — message keys for construction, pharmacy, electrical paths."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ICP_NICHES = (
    "constructionMaterials",
    "pharmacyMedical",
    "electricalDistribution",
)

CAPACITY_MARKERS = (
    "delivery",
    "capacity",
    "courier",
    "livraison",
    "capacité",
)


def main() -> int:
    failures: list[str] = []

    corporate = json.loads((ROOT / "website/messages/corporate-en.json").read_text(encoding="utf-8"))
    business = json.loads((ROOT / "website/messages/business-en.json").read_text(encoding="utf-8"))
    root = json.loads((ROOT / "website/messages/en.json").read_text(encoding="utf-8"))

    hero = corporate.get("home", {}).get("hero", {})
    if hero.get("primaryCta") != "Get a quote":
        failures.append("home primaryCta must be Get a quote")
    if "quote-based" not in (hero.get("trustLine") or "").lower():
        failures.append("home trustLine must state quote-based pricing")

    biz_hero = business.get("hero", {})
    if "vehicle and driver capacity" not in (biz_hero.get("titleLine1") or "").lower():
        failures.append("/business hero must lead with vehicle and driver capacity")

    niches = root.get("nicheLanding", {})
    for key in ICP_NICHES:
        block = niches.get(key)
        if not block:
            failures.append(f"nicheLanding.{key} missing")
            continue
        title = (block.get("hero", {}).get("title") or "").lower()
        if not any(marker in title for marker in CAPACITY_MARKERS):
            failures.append(f"nicheLanding.{key}.hero.title lacks capacity/delivery framing")
        cta_primary = (block.get("cta", {}).get("primary") or "").lower()
        if "quote" not in cta_primary and "devis" not in cta_primary:
            failures.append(f"nicheLanding.{key}.cta.primary must be Get a quote")

    print("ICP 15-second message prep")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        print("  NOTE: Run human test — 3 personas on /, /business, /industry/{slug}")
        print("        Must answer: vehicle+driver capacity · when fleet can't cover · Get a quote")
        return 1
    print("  PASS: ICP message infrastructure ready for human 15-second test")
    print("  HUMAN GATE: construction + pharmacy + electrical ops buyers — 3/3 pass log required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
