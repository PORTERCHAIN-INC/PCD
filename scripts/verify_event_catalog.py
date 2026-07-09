#!/usr/bin/env python3
"""§3.3.4 — versioned event catalog parity (TS ↔ Python)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TS_CATALOG = ROOT / "packages/events/src/catalog.ts"
PY_CATALOG = ROOT / "shared/python/porterchain_shared/events/catalog.py"


def _read_version(text: str, *, lang: str) -> str | None:
    if lang == "ts":
        match = re.search(r'export const CATALOG_VERSION = "([^"]+)"', text)
    else:
        match = re.search(r'^CATALOG_VERSION = "([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else None


def _ts_event_values(text: str) -> set[str]:
    return set(re.findall(r'"([a-z][a-z0-9_.]*)"', text))


def _py_event_values(text: str) -> set[str]:
    return set(re.findall(r'= "([a-z][a-z0-9_.]*)"', text))


def main() -> int:
    failures: list[str] = []
    ts_text = TS_CATALOG.read_text(encoding="utf-8")
    py_text = PY_CATALOG.read_text(encoding="utf-8")

    ts_version = _read_version(ts_text, lang="ts")
    py_version = _read_version(py_text, lang="py")
    if not ts_version or not py_version:
        failures.append("§3.3.4 missing CATALOG_VERSION in TS or Python catalog")
    elif ts_version != py_version:
        failures.append(f"§3.3.4 catalog version drift: TS={ts_version} PY={py_version}")

    ts_events = _ts_event_values(ts_text)
    py_events = _py_event_values(py_text)
    if ts_events != py_events:
        failures.append(f"§3.3.4 event drift: TS-only={sorted(ts_events - py_events)} PY-only={sorted(py_events - ts_events)}")

    if failures:
        print("Event catalog guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"Event catalog guard passed (§3.3.4 — v{ts_version}, {len(ts_events)} events).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
