#!/usr/bin/env python3
"""Smoke-check internal linking registry and navbar hrefs are internal paths."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAVBAR = ROOT / "website/src/data/navbar-navigation.ts"
INTERNAL = ROOT / "website/src/lib/seo/internal-linking.ts"


def main() -> int:
    failures: list[str] = []
    navbar = NAVBAR.read_text(encoding="utf-8")

    for match in re.finditer(r'href:\s*"([^"]+)"', navbar):
        href = match.group(1)
        if href.startswith("http"):
            failures.append(f"navbar: external href not allowed in registry: {href}")
        if not href.startswith("/"):
            failures.append(f"navbar: href must be internal path: {href}")

    if not INTERNAL.exists():
        failures.append("internal-linking.ts missing")
    else:
        text = INTERNAL.read_text(encoding="utf-8")
        if "INDUSTRY_PAGE_LABELS" not in text:
            failures.append("internal-linking.ts: expected hub labels export")

    print("Website internal links guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: navbar and internal linking registry look valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
