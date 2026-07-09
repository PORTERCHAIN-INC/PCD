#!/usr/bin/env python3
"""Appendix E.3 · §7.1.10 — apps/api/README links live OpenAPI surface."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "apps/api/README.md"
OPENAPI_JSON = ROOT / "docs/api/openapi.json"
OPENAPI_EXPORT = ROOT / "apps/api/scripts/export_openapi.py"


def main() -> int:
    failures: list[str] = []

    if not README.is_file():
        failures.append("missing apps/api/README.md")
    else:
        text = README.read_text(encoding="utf-8")
        for needle in ("/docs", "openapi.json", "PARTNER_GUIDE.md", "pnpm docs:openapi"):
            if needle not in text:
                failures.append(f"README missing {needle!r}")

    if not OPENAPI_JSON.is_file():
        failures.append("missing docs/api/openapi.json snapshot")
    if not OPENAPI_EXPORT.is_file():
        failures.append("missing export_openapi.py")

    print("API README OpenAPI guard (Appendix E.3 · §7.1.10)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: README links OpenAPI docs + repo snapshot")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
