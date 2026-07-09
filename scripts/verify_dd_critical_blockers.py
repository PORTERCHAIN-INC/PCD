#!/usr/bin/env python3
"""FND-G5 progress — DD-01–DD-08 critical blockers (7/8 closed; DD-05 prod bridge optional)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKLIST = ROOT / "docs/SILICON_VALLEY_READINESS_CHECKLIST.md"

_DD_ROWS = ("0.7.1", "0.7.2", "0.7.3", "0.7.4", "0.7.6", "0.7.7", "0.7.8")


def main() -> int:
    failures: list[str] = []

    if CHECKLIST.is_file():
        text = CHECKLIST.read_text(encoding="utf-8", errors="ignore")
        for row_id in _DD_ROWS:
            segment = f"| {row_id} |"
            if segment not in text:
                failures.append(f"FND-G5 missing checklist row {row_id}")
                continue
            block = text.split(segment, 1)[1].split("\n", 1)[0]
            if "| [x]" not in block and "| [x] " not in block:
                failures.append(f"FND-G5 {row_id} not marked done")
        if "| 0.7.5 |" in text:
            row = text.split("| 0.7.5 |", 1)[1].split("\n", 1)[0]
            if "[~]" not in row and "[x]" not in row:
                failures.append("FND-G5 0.7.5 must be [~] or [x] with documented prod bridge")
    else:
        failures.append("FND-G5 missing checklist")

    for script in (
        "verify_dispatch_worker.py",
        "verify_engineering_gates.py",
    ):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            failures.append(f"FND-G5 {script} failed")

    if failures:
        print("DD critical blockers guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("DD critical blockers guard passed (FND-G5 — 7/8 closed; 0.7.5 dev complete, prod bridge [~]).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
