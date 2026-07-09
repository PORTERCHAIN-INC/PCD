#!/usr/bin/env python3
"""§2 Engineering gate — ENG-G1–G6 satisfied in CI and guards."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github/workflows/ci.yml"
SECURITY = ROOT / ".github/workflows/security.yml"
PACKAGE = ROOT / "package.json"
D2 = ROOT / "apps/api/scripts/verify_d2_contracts.py"
P0 = ROOT / "apps/api/scripts/verify_p0_loop.py"
TESTS = ROOT / "apps/api/tests"


def _text(*paths: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in paths if p.is_file())


def main() -> int:
    failures: list[str] = []
    ci = _text(CI, PACKAGE)
    sec = _text(SECURITY)

    test_files = list(TESTS.glob("test_*.py")) if TESTS.is_dir() else []
    if len(test_files) < 20:
        failures.append(f"ENG-G1 need ≥20 API test files (found {len(test_files)})")
    if "test \"$count\" -ge 20" not in ci:
        failures.append("ENG-G1 CI test count gate missing")

    if D2.is_file():
        d2 = D2.read_text(encoding="utf-8", errors="ignore")
        if "MAX_ENGINE_SERVICE_LOC" not in d2:
            failures.append("ENG-G2 verify_d2_contracts missing engine LOC guard")
    else:
        failures.append("ENG-G2 missing verify_d2_contracts.py")

    for needle in ("pytest tests/", "validate:d2", "validate:d3"):
        if needle not in ci:
            failures.append(f"ENG-G3 CI missing {needle}")

    if P0.is_file():
        p0 = P0.read_text(encoding="utf-8", errors="ignore")
        if "max_seconds" not in p0 and "max-seconds" not in p0:
            failures.append("ENG-G4 verify_p0_loop missing runtime budget")
    if "validate:p0:fast" not in ci:
        failures.append("ENG-G4 validate:p0:fast not in package.json/CI")

    for needle in ("bandit", "trivy"):
        if needle not in sec.lower():
            failures.append(f"ENG-G6 security workflow missing {needle}")

    if failures:
        print("Engineering gates guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"Engineering gates guard passed (ENG-G1–G6 — {len(test_files)} test files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
