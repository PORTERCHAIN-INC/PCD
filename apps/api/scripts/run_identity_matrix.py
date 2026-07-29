#!/usr/bin/env python3
"""Run the unified-identity Phase 1–9 pytest matrix.

Usage:
  pnpm identity:test
  cd apps/api && PYTHONPATH=src .venv/bin/python scripts/run_identity_matrix.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = [
    "tests/test_unified_identity_characterization.py",
    "tests/test_clerk_registry.py",
    "tests/test_unified_identity_phase2.py",
    "tests/test_unified_identity_phase3.py",
    "tests/test_unified_identity_phase4.py",
    "tests/test_unified_identity_phase5.py",
    "tests/test_unified_identity_phase6.py",
    "tests/test_unified_identity_phase7.py",
    "tests/test_unified_identity_phase8.py",
    "tests/test_unified_identity_phase9.py",
    "tests/test_unified_identity_phase10.py",
]


def main() -> int:
    cmd = [
        str(ROOT / ".venv" / "bin" / "python"),
        "-m",
        "pytest",
        *TESTS,
        "-q",
        "--tb=line",
    ]
    print("identity matrix:", " ".join(TESTS))
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
