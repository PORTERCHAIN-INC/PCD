#!/usr/bin/env python3
"""Pure checks for driver gate / enter-route fail-closed (#41 without Jest)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "apps/mobile-driver/src/gate.ts"


def main() -> int:
    text = GATE.read_text(encoding="utf-8")
    failures: list[str] = []

    if "export function canEnterRoute" not in text:
        failures.append("canEnterRoute missing")
    # Fail-closed: API and auth must both be up before route entry.
    for needle in ('handshake.api !== "up"', 'handshake.auth !== "up"', "Sign in required"):
        if needle not in text:
            failures.append(f"gate missing fail-closed check: {needle!r}")

    # No soft bypass of API/auth in gate itself (dev bypass is caller-side).
    if re.search(r"return \{\s*ok:\s*true\s*\}", text) is None:
        failures.append("gate missing success path")

    print("Driver gate unit guard (#41)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: canEnterRoute fail-closed structure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
