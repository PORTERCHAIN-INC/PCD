#!/usr/bin/env python3
"""Draft expansion gates — niches/areas exist but stay noindex / out of core sitemap."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "website/src/lib/seo/content/draft-expansions.ts"
INDUSTRY_PAGE = ROOT / "website/src/app/[locale]/industry/[slug]/page.tsx"
SITEMAP = ROOT / "website/src/lib/seo/sitemap-entries.ts"
EN = ROOT / "website/messages/en.json"


def main() -> int:
    failures: list[str] = []
    draft = DRAFT.read_text(encoding="utf-8")
    industry = INDUSTRY_PAGE.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    en = EN.read_text(encoding="utf-8")

    for slug in (
        "hvac-mechanical",
        "automotive-parts",
        "manufacturing",
        "retail-replenishment",
        "food-distribution",
    ):
        if slug not in draft:
            failures.append(f"draft-expansions.ts missing niche {slug}")

    for key in (
        "hvacMechanical",
        "richmondHill",
        "scarborough",
        "etobicoke",
        "northYork",
        "milton",
        "whitby",
    ):
        if f'"{key}"' not in en:
            failures.append(f"en.json missing draft stub key {key}")

    if "isDraftNicheSlug" not in industry:
        failures.append("industry/[slug]/page.tsx must force noindex for draft niches")
    if "isDraftNicheSlug" not in sitemap:
        failures.append("sitemap-entries.ts must skip draft niches")
    city_pairs = (
        ROOT / "website/src/lib/seo/city-industry-delivery.ts"
    ).read_text(encoding="utf-8")
    if "isDraftNicheSlug" not in city_pairs:
        failures.append("city-industry-delivery must skip draft niches in slug pairs")

    print("Website draft expansion gate")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: draft niches/areas gated noindex")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
