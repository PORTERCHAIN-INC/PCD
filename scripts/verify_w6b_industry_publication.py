#!/usr/bin/env python3
"""W6b industry publication guard — chocolate, lab-sample, ecommerce city×industry."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLICATION_TS = ROOT / "website/src/lib/seo/city-segment-publication.ts"
EN = ROOT / "website/messages/en.json"

W6B_SLUGS = ("chocolate-delivery", "lab-sample-delivery", "ecommerce-delivery")
NICHE_KEYS = ("chocolate", "labSampleDelivery", "ecommerce")


def _parse_w6b_slugs() -> list[str]:
    text = PUBLICATION_TS.read_text(encoding="utf-8")
    match = re.search(r"W6B_PUBLISHABLE_INDUSTRY_SEO_SLUGS\s*=\s*\[([^\]]+)\]", text, re.S)
    if not match:
        raise ValueError("W6B_PUBLISHABLE_INDUSTRY_SEO_SLUGS not found")
    return re.findall(r'"([^"]+)"', match.group(1))


def _niche_publishable(block: dict) -> bool:
    required = (
        ("hero", "title"),
        ("hero", "subtitle"),
        ("meta", "title"),
        ("meta", "description"),
        ("painPoints", "item1"),
        ("solution", "title"),
        ("faq", "q1"),
        ("cta", "primary"),
    )
    for path in required:
        cur: object = block
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                return False
            cur = cur[key]
        if not cur:
            return False
    return True


def main() -> int:
    failures: list[str] = []

    slugs = _parse_w6b_slugs()
    if list(slugs) != list(W6B_SLUGS):
        failures.append(f"W6B slugs drifted: {slugs!r}")

    data = json.loads(EN.read_text(encoding="utf-8"))
    niches = data.get("nicheLanding", {})
    for key in NICHE_KEYS:
        block = niches.get(key)
        if not block:
            failures.append(f"nicheLanding.{key} missing")
        elif not _niche_publishable(block):
            failures.append(f"nicheLanding.{key} fails publication gate")

    template = data.get("cityIndustryDelivery", {})
    subtitle = template.get("hero", {}).get("subtitlePattern", "")
    if "vehicle" not in subtitle.lower() and "capacity" not in subtitle.lower():
        failures.append("cityIndustryDelivery.hero.subtitlePattern must lead with B2B capacity")
    if "quote" not in (template.get("faq", {}).get("a4") or "").lower():
        failures.append("cityIndustryDelivery.faq.a4 must mention quote-based pricing")

    print("W6b industry publication guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: chocolate, lab-sample, ecommerce city×industry routes publishable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
