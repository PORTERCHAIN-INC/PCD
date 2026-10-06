#!/usr/bin/env python3
"""Day-plan cutover — no Fleetbase sync handlers remain on the event bus."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENT_BUS_HANDLERS = ROOT / "services/event-bus/porterchain_event_bus/handlers/__init__.py"
RETIRED_HANDLER = ROOT / "apps/api/src/porterchain_api/booking_engine/fleetbase_sync_handler.py"
SEQUENCER = ROOT / "apps/api/src/porterchain_api/dispatch_engine/sequencer.py"

_FORBIDDEN_IMPORT = "fleetbase_sync_handler"
_ALLOW_SELF = frozenset(
    {
        "scripts/verify_fleetbase_event_handlers.py",
    }
)


def _check_no_handler_module() -> list[str]:
    if RETIRED_HANDLER.is_file():
        return [f"retired Fleetbase handler still present: {RETIRED_HANDLER.relative_to(ROOT)}"]
    return []


def _check_event_bus_clean() -> list[str]:
    if not EVENT_BUS_HANDLERS.is_file():
        return [f"missing event bus handlers: {EVENT_BUS_HANDLERS.relative_to(ROOT)}"]
    text = EVENT_BUS_HANDLERS.read_text(encoding="utf-8")
    failures: list[str] = []
    if _FORBIDDEN_IMPORT in text or "BookingSyncService" in text:
        failures.append("event bus still registers Fleetbase sync")
    return failures


def _check_no_import_sites() -> list[str]:
    failures: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = str(path.relative_to(ROOT))
        if "node_modules" in rel or ".venv" in rel or "/build/" in rel:
            continue
        if rel in _ALLOW_SELF:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if _FORBIDDEN_IMPORT not in text:
            continue
        if f"from porterchain_api.booking_engine.{_FORBIDDEN_IMPORT}" in text or f"import {_FORBIDDEN_IMPORT}" in text:
            failures.append(f"direct fleetbase_sync_handler import: {rel}")
    return failures


def _check_day_solver() -> list[str]:
    if not SEQUENCER.is_file():
        return ["dispatch_engine/sequencer.py missing — day plan required after Fleetbase removal"]
    text = SEQUENCER.read_text(encoding="utf-8")
    if "ortools" not in text and "OR-Tools" not in text and "pywrapcp" not in text:
        return ["dispatch_engine/sequencer.py must use OR-Tools for the day plan"]
    return []


def main() -> int:
    failures = (
        _check_no_handler_module()
        + _check_event_bus_clean()
        + _check_no_import_sites()
        + _check_day_solver()
    )
    if failures:
        print("Day-plan event-handler guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Day-plan event-handler guard passed — no Fleetbase sync handlers; OR-Tools sequencer present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
