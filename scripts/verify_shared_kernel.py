#!/usr/bin/env python3
"""§3.2.11 — shared kernel lifecycle states live only in domain/states.py."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src/porterchain_api"
STATES_FILE = API_SRC / "domain/states.py"

_ORDER_STATE_ALLOWLIST: frozenset[str] = frozenset(
    {
        "domain/states.py",
    }
)

_TRANSITIONS_ALLOWLIST: frozenset[str] = frozenset(
    {
        "domain/states.py",
    }
)


def _check_unique_definitions() -> list[str]:
    failures: list[str] = []
    for path in sorted(API_SRC.rglob("*.py")):
        rel = str(path.relative_to(API_SRC))
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\bclass OrderState\b", text) and rel not in _ORDER_STATE_ALLOWLIST:
            failures.append(f"§3.2.11 OrderState defined outside shared kernel: {rel}")
        if re.search(r"\bORDER_TRANSITIONS\s*[:=]", text) and rel not in _TRANSITIONS_ALLOWLIST:
            failures.append(f"§3.2.11 ORDER_TRANSITIONS defined outside shared kernel: {rel}")
    return failures


def _check_states_module_purity() -> list[str]:
    failures: list[str] = []
    if not STATES_FILE.is_file():
        return ["§3.2.11 missing domain/states.py"]
    text = STATES_FILE.read_text(encoding="utf-8", errors="ignore")
    if "sqlalchemy" in text.lower():
        failures.append("§3.2.11 domain/states.py must not import SQLAlchemy")
    if re.search(r"from porterchain_api\.(models|booking_models|merchant_models)", text):
        failures.append("§3.2.11 domain/states.py must not import ORM models")
    return failures


def main() -> int:
    failures = _check_unique_definitions() + _check_states_module_purity()
    if failures:
        print("Shared kernel guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Shared kernel guard passed (§3.2.11 — OrderState/ORDER_TRANSITIONS canonical in domain/states.py).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
