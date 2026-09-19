#!/usr/bin/env python3
"""Verify robots.ts references sitemap index and blocks sensitive paths."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROBOTS = ROOT / "website/src/app/robots.ts"


def main() -> int:
    failures: list[str] = []
    text = ROBOTS.read_text(encoding="utf-8")

    if "sitemap" not in text.lower():
        failures.append("robots.ts: must declare sitemap URL(s)")
    for blocked in ("/api/", "login", "book"):
        if blocked not in text:
            failures.append(f"robots.ts: expected disallow for {blocked}")

    print("Website robots guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: robots.ts sitemap + disallow rules present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
