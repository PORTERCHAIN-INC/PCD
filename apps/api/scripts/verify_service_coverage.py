#!/usr/bin/env python3
"""Verify *_service.py coverage floor (§2.1.11). Target 60%; CI enforces regression floor."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COVERAGE_JSON = ROOT / "coverage.json"

# Raised as tests land; target remains 60% per checklist.
MIN_SERVICE_COVERAGE = 60.0
TARGET_SERVICE_COVERAGE = 60.0


def _aggregate_service_coverage(data: dict) -> tuple[float, int, int]:
    statements = missing = 0
    for path, info in data.get("files", {}).items():
        if "_service.py" not in path:
            continue
        statements += info["summary"]["num_statements"]
        missing += info["summary"]["missing_lines"]
    covered = statements - missing
    pct = (covered / statements * 100) if statements else 0.0
    return pct, covered, statements


def main() -> int:
    if not COVERAGE_JSON.is_file():
        print("FAIL: run pytest with --cov-report=json first")
        return 1

    pct, covered, total = _aggregate_service_coverage(json.loads(COVERAGE_JSON.read_text()))
    print(f"Service coverage: {pct:.1f}% ({covered}/{total} stmts on *_service.py)")
    print(f"  floor: {MIN_SERVICE_COVERAGE:.0f}%  target: {TARGET_SERVICE_COVERAGE:.0f}%")

    if pct + 1e-9 < MIN_SERVICE_COVERAGE:
        print(f"FAIL: below floor {MIN_SERVICE_COVERAGE:.0f}%")
        return 1
    if pct + 1e-9 < TARGET_SERVICE_COVERAGE:
        print(f"WARN: below target {TARGET_SERVICE_COVERAGE:.0f}% — add service integration tests")
    else:
        print("PASS: target met")
    print("PASS: service coverage floor OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
