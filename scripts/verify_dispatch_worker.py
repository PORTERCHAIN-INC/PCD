#!/usr/bin/env python3
"""§0.7.5 / DD-05 — dispatch worker processor wired (prod Fleetbase bridge optional)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "apps/worker/processors/dispatch.py"
PROCESSORS = ROOT / "apps/worker/processors/__init__.py"
TEST = ROOT / "apps/api/tests/test_dispatch_processor.py"
RUNBOOK = ROOT / "RUNBOOK.md"


def main() -> int:
    failures: list[str] = []

    if DISPATCH.is_file():
        text = DISPATCH.read_text(encoding="utf-8", errors="ignore")
        if "process_dispatch" not in text:
            failures.append("§0.7.5 dispatch.py missing process_dispatch")
        if "BookingSyncService" in text:
            failures.append("§0.7.5 dispatch.py must not push orders to Fleetbase")

    if PROCESSORS.is_file():
        init = PROCESSORS.read_text(encoding="utf-8", errors="ignore")
        if "process_dispatch" not in init:
            failures.append("§0.7.5 processors/__init__.py missing process_dispatch")

    if not TEST.is_file():
        failures.append("§0.7.5 missing tests/test_dispatch_processor.py")

    if failures:
        print("Dispatch worker guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Dispatch worker guard passed (§0.7.5 — processor + tests; prod bridge optional).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
