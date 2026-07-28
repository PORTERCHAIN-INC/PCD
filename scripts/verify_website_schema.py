#!/usr/bin/env python3
"""Verify structured data helpers include entity @id graph and BreadcrumbList."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "website/src/lib/seo/schema.ts"
LAYOUT = ROOT / "website/src/app/[locale]/layout.tsx"


def main() -> int:
    failures: list[str] = []
    schema = SCHEMA.read_text(encoding="utf-8")
    layout = LAYOUT.read_text(encoding="utf-8")

    for symbol in (
        "organizationId",
        "websiteId",
        "buildWebSiteSchema",
        "buildBreadcrumbListSchema",
        "buildHowToSchema",
        "buildCorporationSchema",
        "buildDatasetSchema",
        "serviceEntityId",
    ):
        if f"function {symbol}" not in schema and f"export function {symbol}" not in schema:
            failures.append(f"schema.ts: missing {symbol}")

    if "buildWebSiteSchema" not in layout:
        failures.append("layout.tsx: should emit WebSite JSON-LD")

    print("Website schema guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: entity graph helpers and WebSite schema wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
