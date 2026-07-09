#!/usr/bin/env python3
"""§3.4.5 — RUNBOOK documents queue backpressure thresholds and DLQ surfaces."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "RUNBOOK.md"

_REQUIRED_SNIPPETS: tuple[str, ...] = (
    "### Queue backpressure",
    "porterchain_queue_depth",
    "GET /v1/admin/operations/queues",
    "porterchain:events:dlq",
    "### Dead-letter replay",
    "Merchant webhooks",
)


def main() -> int:
    if not RUNBOOK.is_file():
        print("Queue runbook guard failed: RUNBOOK.md missing")
        return 1
    text = RUNBOOK.read_text(encoding="utf-8", errors="ignore")
    missing = [snippet for snippet in _REQUIRED_SNIPPETS if snippet not in text]
    if missing:
        print("Queue runbook guard failed:")
        for item in missing:
            print(f"  - §3.4.5 RUNBOOK missing: {item}")
        return 1
    print("Queue runbook guard passed (§3.4.5 — backpressure + DLQ documented).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
