#!/usr/bin/env python3
"""ARCH-G1 — architecture validation report has zero open P0 issues."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/architecture/ARCHITECTURE_VALIDATION_REPORT.md"


def main() -> int:
    if not REPORT.is_file():
        print("Architecture validation guard failed: report missing")
        return 1
    text = REPORT.read_text(encoding="utf-8", errors="ignore")
    failures: list[str] = []

    if "## P0 register" not in text:
        failures.append("ARCH-G1 missing ## P0 register section")
    if "Open P0: **0**" not in text and "Open P0: 0" not in text:
        failures.append("ARCH-G1 report must state Open P0: 0")

    open_p0 = re.findall(r"### ISSUE-\d+:[^\n]*\n(?:.*?\n)*?\| \*\*Priority\*\* \| \*\*P0", text, re.MULTILINE)
    for block in open_p0:
        if "— OPEN" in block or "OPEN\n" in block:
            failures.append("ARCH-G1 open P0 issue found in validation report")

    if failures:
        print("Architecture validation guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Architecture validation guard passed (ARCH-G1 — 0 open P0).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
