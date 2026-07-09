#!/usr/bin/env python3
"""§3.4.4 — read replica path documented for analytics workloads."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "DATABASE_ARCHITECTURE.md"
ADR = ROOT / "docs/architecture/ADR-012-scaling.md"

_REQUIRED_SNIPPETS: tuple[str, ...] = (
    "## Read replica",
    "analytics",
    "DATABASE_URL",
    "read-only",
    "primary",
)


def main() -> int:
    failures: list[str] = []
    if not DOC.is_file():
        failures.append("§3.4.4 missing DATABASE_ARCHITECTURE.md")
    else:
        text = DOC.read_text(encoding="utf-8", errors="ignore")
        for snippet in _REQUIRED_SNIPPETS:
            if snippet not in text:
                failures.append(f"§3.4.4 DATABASE_ARCHITECTURE.md missing: {snippet}")
    if ADR.is_file():
        adr = ADR.read_text(encoding="utf-8", errors="ignore")
        if "read replica" not in adr.lower():
            failures.append("§3.4.4 ADR-012 must reference read replica")
    else:
        failures.append("§3.4.4 missing ADR-012-scaling.md")

    if failures:
        print("Read replica doc guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Read replica doc guard passed (§3.4.4 — analytics off primary documented).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
