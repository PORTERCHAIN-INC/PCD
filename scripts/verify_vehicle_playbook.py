#!/usr/bin/env python3
"""Vehicle route publication guard — playbook §2.3 index policy + copy gate."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_TS = ROOT / "website/src/lib/seo/vehicle-publication.ts"
MESSAGES_DIR = ROOT / "website/messages"

INDEXABLE_SEGMENTS = (
    "trade-van-delivery",
    "box-truck-delivery",
    "cargo-van-delivery",
    "pickup-truck-delivery",
)
NON_INDEXABLE_SEGMENTS = ("sedan-delivery", "suv-delivery")
MESSAGE_KEYS = ("van", "mediumTruck", "cargoVan", "pickupTruck")
MIN_COPY_CHARS = 200
PRICE_FAQ_KEYS = ("faqPricingQ", "faqPricingA")
GEO_MARKERS = ("GTA", "RGT", "Greater Toronto", "Ontario")


def _parse_indexable_from_ts() -> list[str]:
    text = PUBLICATION_TS.read_text(encoding="utf-8")
    match = re.search(r"INDEXABLE_VEHICLE_SEGMENTS\s*=\s*\[([^\]]+)\]", text, re.S)
    if not match:
        raise ValueError("INDEXABLE_VEHICLE_SEGMENTS not found in vehicle-publication.ts")
    return re.findall(r'"([^"]+)"', match.group(1))


def _copy_total(block: dict) -> int:
    return len(block.get("whenYouNeed", "")) + len(block.get("useCases", "")) + len(block.get("whoFor", ""))


def main() -> int:
    failures: list[str] = []

    ts_segments = _parse_indexable_from_ts()
    if list(ts_segments) != list(INDEXABLE_SEGMENTS):
        failures.append(
            f"vehicle-publication.ts segments {ts_segments!r} != expected {list(INDEXABLE_SEGMENTS)!r}"
        )
    for segment in NON_INDEXABLE_SEGMENTS:
        if segment in ts_segments:
            failures.append(f"consumer-adjacent segment must stay non-indexable: {segment}")

    for name in ("en.json", "fr.json"):
        data = json.loads((MESSAGES_DIR / name).read_text(encoding="utf-8"))
        vehicles = data.get("vehicleDelivery", {})
        for key in MESSAGE_KEYS:
            block = vehicles.get(key)
            if not block:
                failures.append(f"{name}: vehicleDelivery.{key} missing")
                continue
            for field in ("whenYouNeedTitle", "whenYouNeed", "useCases", "whoFor", *PRICE_FAQ_KEYS):
                if not block.get(field):
                    failures.append(f"{name}: vehicleDelivery.{key}.{field} missing for index gate")
            sub = block.get("subheadline") or ""
            if not any(marker in sub for marker in GEO_MARKERS):
                failures.append(
                    f"{name}: vehicleDelivery.{key}.subheadline must mention GTA/RGT above fold"
                )
            total = _copy_total(block)
            if total < MIN_COPY_CHARS:
                failures.append(
                    f"{name}: vehicleDelivery.{key} copy total {total} < {MIN_COPY_CHARS} (thin page)"
                )

        for key in ("sedan", "suv"):
            if vehicles.get(key, {}).get("whenYouNeed"):
                failures.append(f"{name}: vehicleDelivery.{key} should not have whenYouNeed (noindex)")

    print("Vehicle playbook guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print(
        f"  PASS: 4 B2B vehicle routes indexable when copy gate passes; sedan/SUV remain noindex"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
