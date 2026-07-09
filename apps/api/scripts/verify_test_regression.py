#!/usr/bin/env python3
"""Test count regression guard (§2.1.12) — no delete without ADR."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Baseline after §2.1 service integration suite (2026-07-08).
MIN_TESTS = 583


def main() -> int:
    result = subprocess.run(
        ["pytest", "--collect-only", "-q", "tests/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    count_line = next((line for line in result.stdout.splitlines() if " tests collected" in line), "")
    if not count_line:
        print("FAIL: could not parse pytest collection output")
        print(result.stdout)
        print(result.stderr)
        return 1

    count = int(count_line.strip().split()[0])
    print(f"API tests collected: {count} (minimum {MIN_TESTS})")
    if count < MIN_TESTS:
        print("FAIL: test count regressed — restore tests or add ADR for intentional deletion")
        return 1
    print("PASS: test count regression guard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
