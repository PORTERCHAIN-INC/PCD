#!/usr/bin/env python3
"""Verify public/llms.txt exists with authoritative PorterChain routes."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LLMS = ROOT / "website/public/llms.txt"

REQUIRED_SNIPPETS = (
    "porterchain.com/en/company",
    "porterchain.com/en/business",
    "porterchain.com/en/developers",
    "porterchain.com/en/local-delivery",
)


def main() -> int:
    failures: list[str] = []
    if not LLMS.exists():
        failures.append("website/public/llms.txt missing")
    else:
        text = LLMS.read_text(encoding="utf-8")
        for snippet in REQUIRED_SNIPPETS:
            if snippet not in text:
                failures.append(f"llms.txt: missing route {snippet}")

    print("Website llms.txt guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: llms.txt present with core routes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
