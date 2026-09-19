#!/usr/bin/env python3
"""§6.1.4 — enterprise visuals via curated site-images (Unsplash + stock)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_IMAGES = ROOT / "website/src/data/site-images.ts"


def main() -> int:
    failures: list[str] = []

    if not SITE_IMAGES.is_file():
        failures.append("§6.1.4 missing website/src/data/site-images.ts")
    else:
        text = SITE_IMAGES.read_text(encoding="utf-8", errors="ignore")
        for needle in (
            "export const siteImages",
            "hero:",
            "industries:",
            "images.unsplash.com",
            "TORONTO_GTA_SKYLINE",
            "ECOMMERCE_TRUCK",
        ):
            if needle not in text:
                failures.append(f"§6.1.4 site-images.ts missing {needle}")

    if failures:
        print("Enterprise visuals guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Enterprise visuals guard passed (§6.1.4 — curated B2B imagery catalog).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
