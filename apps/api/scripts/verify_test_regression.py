#!/usr/bin/env python3
"""Test count regression guard (§2.1.12) — no delete without ADR."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]

# Baseline after §2.1 service integration suite (2026-07-08).
MIN_TESTS = 583

_PYTHONPATH = os.pathsep.join(
    [
        str(ROOT / "src"),
        str(REPO / "shared/python"),
        str(REPO / "services/python"),
        str(REPO / "services/pricing-engine"),
        str(REPO / "services/event-bus"),
        str(REPO / "services/driver-platform"),
        str(REPO / "apps/worker"),
    ]
)


def main() -> int:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "").strip()
    env["PYTHONPATH"] = f"{_PYTHONPATH}{os.pathsep}{existing}" if existing else _PYTHONPATH

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
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
