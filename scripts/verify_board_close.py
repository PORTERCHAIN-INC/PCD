#!/usr/bin/env python3
"""Board-close guard — neighbourhood hyperlocal, E-E-A-T success stories, edge cache, no zip landings."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEIGHBOURHOODS = ROOT / "website/src/lib/seo/city-neighbourhoods.ts"
SERVICE_AREA_PAGE = ROOT / "website/src/app/[locale]/service-areas/[slug]/page.tsx"
SUCCESS_PAGE = ROOT / "website/src/app/[locale]/success-stories/[slug]/page.tsx"
SUCCESS_DATA = ROOT / "website/src/lib/seo/content/success-stories.ts"
SCHEMA = ROOT / "website/src/lib/seo/schema.ts"
CADDY = ROOT / "infrastructure/deploy/Caddyfile"
SITEMAP = ROOT / "website/src/lib/seo/sitemap-entries.ts"


def main() -> int:
    failures: list[str] = []

    if not NEIGHBOURHOODS.is_file():
        failures.append("missing city-neighbourhoods.ts")
    else:
        text = NEIGHBOURHOODS.read_text(encoding="utf-8")
        for city in ("toronto", "mississauga", "brampton", "hamilton"):
            if f"{city}:" not in text and f'"{city}"' not in text:
                failures.append(f"city-neighbourhoods missing {city}")
        if "do NOT generate zip" not in text and "do NOT generate zip/FSA" not in text:
            failures.append("city-neighbourhoods missing charter zip ban comment")

    sa = SERVICE_AREA_PAGE.read_text(encoding="utf-8")
    for marker in ("getCityNeighbourhoods", "PostalCoverageChecker", "postalCodes"):
        if marker not in sa:
            failures.append(f"service-area page missing {marker}")

    schema = SCHEMA.read_text(encoding="utf-8")
    if "postalCodes" not in schema or "postalCode" not in schema:
        failures.append("schema.ts missing postalCode/postalCodes hyperlocal support")

    success_page = SUCCESS_PAGE.read_text(encoding="utf-8")
    for marker in ("AuthorCard", "authorPerson", "permissioned", "anonymizedStoryNote"):
        if marker not in success_page:
            failures.append(f"success-story page missing {marker}")

    success_data = SUCCESS_DATA.read_text(encoding="utf-8")
    if "permissioned: true" not in success_data:
        failures.append("success-stories.ts needs at least one permissioned: true story")
    if "authorId:" not in success_data:
        failures.append("success-stories.ts missing authorId E-E-A-T fields")

    caddy = CADDY.read_text(encoding="utf-8")
    if "_next/static" not in caddy or "stale-while-revalidate" not in caddy:
        failures.append("Caddyfile missing static/HTML edge cache headers")

    # Forbid zip/FSA route generators in sitemap
    if SITEMAP.is_file():
        sm = SITEMAP.read_text(encoding="utf-8")
        if re.search(r'["\']/fsa/|["\']/postal/|["\']/zip/', sm):
            failures.append("sitemap must not include zip/FSA landing routes")

    print("Board-close hyperlocal / E-E-A-T / edge guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: neighbourhood depth + permissioned stories + Caddy cache; no zip landings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
