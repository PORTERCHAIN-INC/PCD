#!/usr/bin/env python3
"""§5.1.8 — secrets rotation via Doppler documented in RUNBOOK."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "RUNBOOK.md"
SECURITY = ROOT / "SECURITY.md"


def main() -> int:
    failures: list[str] = []

    if RUNBOOK.is_file():
        text = RUNBOOK.read_text(encoding="utf-8", errors="ignore")
        for needle in ("Secrets rotation", "Doppler", "rotate"):
            if needle.lower() not in text.lower():
                failures.append(f"§5.1.8 RUNBOOK missing secrets rotation: {needle}")
    else:
        failures.append("§5.1.8 missing RUNBOOK.md")

    if SECURITY.is_file():
        sec = SECURITY.read_text(encoding="utf-8", errors="ignore")
        if "rotation" not in sec.lower():
            failures.append("§5.1.8 SECURITY.md missing rotation policy")
    else:
        failures.append("§5.1.8 missing SECURITY.md")

    if failures:
        print("Secrets rotation guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Secrets rotation guard passed (§5.1.8 — Doppler rotation runbook).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
