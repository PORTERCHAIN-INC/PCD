"""Event catalog parity — TS DomainEvents ↔ Python DomainEventType (§2.1.6)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TS_CATALOG = ROOT / "packages/events/src/catalog.ts"
PY_CATALOG = ROOT / "shared/python/porterchain_shared/events/catalog.py"


def _ts_event_values(text: str) -> set[str]:
    return set(re.findall(r'"([a-z][a-z0-9_.]*)"', text))


def _py_event_values(text: str) -> set[str]:
    return set(re.findall(r'= "([a-z][a-z0-9_.]*)"', text))


def test_event_catalog_parity() -> None:
    ts = _ts_event_values(TS_CATALOG.read_text())
    py = _py_event_values(PY_CATALOG.read_text())
    assert ts == py, f"catalog drift: TS-only={ts - py} PY-only={py - ts}"
