#!/usr/bin/env python3
"""Living architecture CI wiring — thin routers, D2, no Fleetbase in UI."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github/workflows/ci.yml"
PACKAGE = ROOT / "package.json"

_REQUIRED_SCRIPTS = (
    "validate:architecture",
    "validate:router-audit",
    "validate:d2",
    "validate:golden-rules",
)


def _ci_text() -> str:
    parts = []
    if CI.is_file():
        parts.append(CI.read_text(encoding="utf-8", errors="ignore"))
    if PACKAGE.is_file():
        parts.append(PACKAGE.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def main() -> int:
    failures: list[str] = []
    ci_text = _ci_text()

    for script in _REQUIRED_SCRIPTS:
        if script not in ci_text:
            failures.append(f"{script} not in CI/package.json")

    d2_script = ROOT / "apps/api/scripts/verify_d2_contracts.py"
    if d2_script.is_file():
        d2 = d2_script.read_text(encoding="utf-8", errors="ignore")
        if "FORBIDDEN_PATHS" not in d2:
            failures.append("verify_d2_contracts missing FORBIDDEN_PATHS")
        if "MAX_ENGINE_SERVICE_LOC" not in d2:
            failures.append("verify_d2_contracts missing MAX_ENGINE_SERVICE_LOC")
    else:
        failures.append("missing verify_d2_contracts.py")

    fleetbase = ROOT / "apps/fleetbase"
    if fleetbase.is_dir():
        for py in fleetbase.rglob("*.py"):
            text = py.read_text(encoding="utf-8", errors="ignore")
            if "porterchain_api" in text or "booking_engine" in text:
                failures.append(f"PorterChain logic in vendor tree: {py.relative_to(ROOT)}")
                break

    if failures:
        print("Golden rules CI guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Golden rules CI guard passed (living architecture scripts wired).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
