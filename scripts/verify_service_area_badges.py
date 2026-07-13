#!/usr/bin/env python3
"""Service-area trust guard — core metros vs confirmation-only markets."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE_AREAS_TS = ROOT / "website/src/lib/seo/service-areas.ts"
SERVICE_AREA_PAGE = ROOT / "website/src/app/[locale]/service-areas/[slug]/page.tsx"
CORPORATE_EN = ROOT / "website/messages/corporate-en.json"
CORPORATE_FR = ROOT / "website/messages/corporate-fr.json"
FR_ROOT = ROOT / "website/messages/fr.json"

EXPECTED_CORE = (
    "toronto",
    "mississauga",
    "brampton",
    "vaughan",
    "markham",
    "oakville",
    "hamilton",
    "kitchener-waterloo",
)
FR_CONFIRMATION_MARKETS = ("oshawa", "london", "stCatharines", "niagara")
BANNED_FR_CONSUMER_MARKERS = ("last-mile récurrent pour marchands", "volume de colis")


def _parse_core_slugs() -> list[str]:
    text = SERVICE_AREAS_TS.read_text(encoding="utf-8")
    match = re.search(r"CORE_SERVICE_AREA_SLUGS\s*=\s*\[([^\]]+)\]", text, re.S)
    if not match:
        raise ValueError("CORE_SERVICE_AREA_SLUGS not found")
    return re.findall(r'"([^"]+)"', match.group(1))


def main() -> int:
    failures: list[str] = []

    core_slugs = _parse_core_slugs()
    if tuple(core_slugs) != EXPECTED_CORE:
        failures.append(f"core service areas drifted: {core_slugs!r}")

    page = SERVICE_AREA_PAGE.read_text(encoding="utf-8")
    for marker in (
        "coreServiceArea",
        "availableByConfirmation",
        "isCoreServiceArea(slug)",
        "pricingFaqQ",
        "pricingFaqA",
    ):
        if marker not in page:
            failures.append(f"service-area page missing badge marker: {marker}")

    for name, path in (("en", CORPORATE_EN), ("fr", CORPORATE_FR)):
        labels = json.loads(path.read_text(encoding="utf-8")).get("seo", {}).get("sectionLabels", {})
        for key in ("coreServiceArea", "availableByConfirmation", "pricingFaqQ", "pricingFaqA"):
            if not labels.get(key):
                failures.append(f"{name}: corporate.seo.sectionLabels.{key} missing")

    fr_service_areas = json.loads(FR_ROOT.read_text(encoding="utf-8")).get("serviceAreaLanding", {})
    for key in FR_CONFIRMATION_MARKETS:
        block = fr_service_areas.get(key, {})
        text = json.dumps(block, ensure_ascii=False).lower()
        if "capacité" not in text or "b2b" not in text:
            failures.append(f"fr.json serviceAreaLanding.{key}: missing B2B capacity framing")
        for marker in BANNED_FR_CONSUMER_MARKERS:
            if marker in text:
                failures.append(f"fr.json serviceAreaLanding.{key}: consumer drift marker {marker!r}")

    print("Service-area badge guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: service areas distinguish core metros from confirmation-only markets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
