#!/usr/bin/env python3
"""§3.3.4 — merchant webhook fanout is worker/event-bus driven only."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_IMPORT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "apps/worker/processors/webhooks.py",
        "apps/api/src/porterchain_api/merchant_engine/webhook_delivery_service.py",
    }
)


def main() -> int:
    failures: list[str] = []
    needle = "deliver_merchant_fanout"
    for path in sorted(ROOT.rglob("*.py")):
        rel = str(path.relative_to(ROOT))
        if "node_modules" in rel or ".venv" in rel or "/tests/" in rel or rel.startswith("apps/api/tests"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if needle not in text:
            continue
        if rel in _IMPORT_ALLOWLIST:
            continue
        if f"import {needle}" in text or f".{needle}" in text:
            failures.append(f"§3.3.4 merchant fanout outside worker pipeline: {rel}")
    if failures:
        print("Merchant webhook event-path guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Merchant webhook event-path guard passed (§3.3.4 — fanout via event bus → worker).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
