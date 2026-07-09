#!/usr/bin/env python3
"""§5.1.10 — external uptime monitor documented for prod API + portals."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "RUNBOOK.md"
DEPLOY = ROOT / "infrastructure/deploy/README.md"
METRICS = ROOT / "docs/EXECUTION_METRICS.md"


def main() -> int:
    failures: list[str] = []

    for path, needles in (
        (RUNBOOK, ("/health/ready", "api.porterchain.com", "uptime", "External uptime")),
        (DEPLOY, ("/health",)),
    ):
        if not path.is_file():
            failures.append(f"§5.1.10 missing {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle not in text:
                failures.append(f"§5.1.10 {path.name} missing: {needle}")

    if failures:
        print("Uptime monitor guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Uptime monitor guard passed (§5.1.10 — external probe doc; configure alert in prod).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
