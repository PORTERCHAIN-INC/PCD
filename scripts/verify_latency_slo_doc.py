#!/usr/bin/env python3
"""§5.4.3 — published p95 API latency SLO documented and load-tested."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "RUNBOOK.md"
LOAD_README = ROOT / "tests/load/README.md"
BOOKING_JS = ROOT / "tests/load/booking.js"
WEBHOOKS_JS = ROOT / "tests/load/webhooks.js"
PACKAGE = ROOT / "package.json"

_REQUIRED: tuple[str, ...] = (
    "Published API latency SLOs",
    "p95 target",
    "GET /health",
    "POST /v1/quotes",
    "POST /webhooks/stripe",
    "load:booking",
    "/metrics",
)


def main() -> int:
    failures: list[str] = []

    if RUNBOOK.is_file():
        rb = RUNBOOK.read_text(encoding="utf-8", errors="ignore")
        for snippet in _REQUIRED:
            if snippet not in rb:
                failures.append(f"§5.4.3 RUNBOOK missing: {snippet}")
    else:
        failures.append("§5.4.3 missing RUNBOOK.md")

    for path in (LOAD_README, BOOKING_JS, WEBHOOKS_JS):
        if not path.is_file():
            failures.append(f"§5.4.3 missing {path.relative_to(ROOT)}")

    if BOOKING_JS.is_file():
        js = BOOKING_JS.read_text(encoding="utf-8", errors="ignore")
        if 'p(95)<200' not in js or 'p(95)<3000' not in js:
            failures.append("§5.4.3 booking.js missing p95 thresholds")

    if PACKAGE.is_file():
        pkg = PACKAGE.read_text(encoding="utf-8", errors="ignore")
        if "load:booking" not in pkg or "load:webhooks" not in pkg:
            failures.append("§5.4.3 package.json missing load scripts")

    if failures:
        print("Latency SLO doc guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Latency SLO doc guard passed (§5.4.3 — RUNBOOK + k6 thresholds).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
