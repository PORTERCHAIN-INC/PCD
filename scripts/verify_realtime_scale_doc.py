#!/usr/bin/env python3
"""§3.4.2 / §3.5.4 — REALTIME_FLOW documents multi-instance WebSocket scaling."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/architecture/REALTIME_FLOW.md"

_REQUIRED_SNIPPETS: tuple[str, ...] = (
    "## Multi-instance scaling",
    "porterchain:notifications:realtime",
    "live-map/ws",
    "Redis pub/sub",
    "round-robin",
    "ADR-012",
    "5 seconds",
    "db_pool",
)


def main() -> int:
    if not DOC.is_file():
        print("Realtime scale doc guard failed: REALTIME_FLOW.md missing")
        return 1
    text = DOC.read_text(encoding="utf-8", errors="ignore")
    missing = [snippet for snippet in _REQUIRED_SNIPPETS if snippet not in text]
    if missing:
        print("Realtime scale doc guard failed:")
        for item in missing:
            print(f"  - §3.4.2/§3.5.4 REALTIME_FLOW.md missing: {item}")
        return 1
    print("Realtime scale doc guard passed (§3.4.2 / §3.5.4 — WS scaling documented).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
