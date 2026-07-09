#!/usr/bin/env python3
"""§5.2 — fleetbase:replay documented for prod ops."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "RUNBOOK.md"
PACKAGE = ROOT / "package.json"


def main() -> int:
    failures: list[str] = []

    if PACKAGE.is_file():
        if "fleetbase:replay" not in PACKAGE.read_text(encoding="utf-8", errors="ignore"):
            failures.append("§5.2 package.json missing fleetbase:replay")
    else:
        failures.append("§5.2 missing package.json")

    if RUNBOOK.is_file():
        rb = RUNBOOK.read_text(encoding="utf-8", errors="ignore")
        if "pnpm fleetbase:replay" not in rb:
            failures.append("§5.2 RUNBOOK missing pnpm fleetbase:replay")
        if "Dead-letter replay" not in rb and "dead letter" not in rb.lower():
            failures.append("§5.2 RUNBOOK missing DLQ replay section")
    else:
        failures.append("§5.2 missing RUNBOOK.md")

    if failures:
        print("Fleetbase replay prod doc guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Fleetbase replay prod doc guard passed (§5.2 fleetbase:replay in RUNBOOK).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
