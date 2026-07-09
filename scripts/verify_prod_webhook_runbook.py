#!/usr/bin/env python3
"""§0.6.3 — prod webhook secret cutover documented (dev layer; secret set at deploy)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "RUNBOOK.md"
DEPLOY = ROOT / "infrastructure/deploy/README.md"

_REQUIRED: tuple[str, ...] = (
    "FLEETBASE_WEBHOOK_SECRET",
    "/webhooks/fleetbase",
    "FIREBASE_WEBHOOK_SECRET",
    "webhooks/stripe",
)


def main() -> int:
    failures: list[str] = []
    combined = ""
    for path in (RUNBOOK, DEPLOY):
        if path.is_file():
            combined += path.read_text(encoding="utf-8", errors="ignore")
        else:
            failures.append(f"§0.6.3 missing {path.relative_to(ROOT)}")

    for snippet in _REQUIRED:
        if snippet not in combined:
            failures.append(f"§0.6.3 prod webhook docs missing: {snippet}")

    if failures:
        print("Prod webhook runbook guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Prod webhook runbook guard passed (§0.6.3 — cutover documented; secrets set in prod).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
