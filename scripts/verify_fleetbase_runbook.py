#!/usr/bin/env python3
"""§5.1.5 / §5.1.6 / §5.1.11 — Fleetbase runbook + verify command + incidents."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "RUNBOOK.md"
VERIFY = ROOT / "infrastructure/docker/scripts/fleetbase-verify.sh"
PACKAGE = ROOT / "package.json"


def main() -> int:
    failures: list[str] = []

    if not VERIFY.is_file():
        failures.append("§5.1.11 missing fleetbase-verify.sh")

    if PACKAGE.is_file():
        if "docker:fleetbase:verify" not in PACKAGE.read_text(encoding="utf-8", errors="ignore"):
            failures.append("§5.1.11 package.json missing docker:fleetbase:verify")
    else:
        failures.append("§5.1.11 missing package.json")

    if RUNBOOK.is_file():
        text = RUNBOOK.read_text(encoding="utf-8", errors="ignore")
        for needle in (
            "pnpm docker:fleetbase:verify",
            "Fleetbase stack",
            "## Incident response",
            "Dispatch not syncing",
        ):
            if needle not in text:
                failures.append(f"§5.1.5/5.1.6 RUNBOOK missing: {needle}")
    else:
        failures.append("§5.1.5 missing RUNBOOK.md")

    if failures:
        print("Fleetbase runbook guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Fleetbase runbook guard passed (§5.1.5/5.1.6/5.1.11).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
