#!/usr/bin/env python3
"""Verify partitioned sitemap implementation — no fabricated lastModified."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITEMAP_TS = ROOT / "website/src/app/sitemap.ts"
ENTRIES_TS = ROOT / "website/src/lib/seo/sitemap-entries.ts"


def main() -> int:
    failures: list[str] = []
    sitemap = SITEMAP_TS.read_text(encoding="utf-8")
    entries = ENTRIES_TS.read_text(encoding="utf-8")

    if "generateSitemaps" not in sitemap:
        failures.append("sitemap.ts: expected generateSitemaps() for partitioned sitemaps")
    if "lastModified: new Date()" in entries:
        failures.append("sitemap-entries.ts: must not use lastModified: new Date()")
    if "SITEMAP_PARTITIONS" not in entries and "buildStaticSitemapEntries" not in entries:
        failures.append("sitemap-entries.ts: expected partition builders")

    partitions = [
        "static",
        "industry",
        "service",
        "vehicle",
        "location",
        "resource",
        "article",
    ]
    for part in partitions:
        if f'"{part}"' not in entries and f"'{part}'" not in entries:
            failures.append(f"sitemap-entries.ts: missing partition {part}")

    print("Website sitemap guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: partitioned sitemap without fabricated lastModified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
