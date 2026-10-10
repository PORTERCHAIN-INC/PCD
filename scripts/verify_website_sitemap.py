#!/usr/bin/env python3
"""Verify partitioned sitemap implementation — no fabricated lastModified."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITEMAP_INDEX = ROOT / "website/src/app/sitemap.xml/route.ts"
SITEMAP_PART = ROOT / "website/src/app/sitemap/[id]/route.ts"
SITEMAP_XML = ROOT / "website/src/lib/seo/sitemap-xml.ts"
ENTRIES_TS = ROOT / "website/src/lib/seo/sitemap-entries.ts"


def main() -> int:
    failures: list[str] = []
    entries = ENTRIES_TS.read_text(encoding="utf-8")
    for path in (SITEMAP_INDEX, SITEMAP_PART, SITEMAP_XML):
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
    if not failures:
        index = SITEMAP_INDEX.read_text(encoding="utf-8")
        part = SITEMAP_PART.read_text(encoding="utf-8")
        xml = SITEMAP_XML.read_text(encoding="utf-8")
        if "sitemapIndexXml" not in index:
            failures.append("sitemap.xml/route.ts: expected sitemap index (sitemapIndexXml)")
        if "generateStaticParams" not in part or "SITEMAP_PARTITION_IDS" not in part:
            failures.append("sitemap/[id]/route.ts: expected static partitions from SITEMAP_PARTITION_IDS")
        if "<sitemapindex" not in xml or "<urlset" not in xml:
            failures.append("sitemap-xml.ts: expected sitemapindex + urlset serializers")
        if "new Date()" in xml:
            failures.append("sitemap-xml.ts: must not fabricate lastmod")
    if "lastModified: new Date()" in entries:
        failures.append("sitemap-entries.ts: must not use lastModified: new Date()")
    if "SITEMAP_PARTITIONS" not in entries and "buildStaticSitemapEntries" not in entries:
        failures.append("sitemap-entries.ts: expected partition builders")

    partitions = [
        "static",
        "industry",
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
