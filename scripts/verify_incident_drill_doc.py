#!/usr/bin/env python3
"""EXE-G3 — incident response drill documented (dev tabletop; prod execution [~])."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "RUNBOOK.md"
CHECKLIST = ROOT / "docs/SILICON_VALLEY_READINESS_CHECKLIST.md"


def main() -> int:
    failures: list[str] = []

    if RUNBOOK.is_file():
        text = RUNBOOK.read_text(encoding="utf-8", errors="ignore")
        for needle in ("Incident drill", "Incident response", "tabletop"):
            if needle not in text:
                failures.append(f"EXE-G3 RUNBOOK missing: {needle}")
    else:
        failures.append("EXE-G3 missing RUNBOOK.md")

    if CHECKLIST.is_file():
        if "EXE-G3" not in CHECKLIST.read_text(encoding="utf-8", errors="ignore"):
            failures.append("EXE-G3 missing gate in checklist")
    else:
        failures.append("EXE-G3 missing checklist")

    if failures:
        print("Incident drill guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Incident drill guard passed (EXE-G3 — tabletop documented; live drill [prod]).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
