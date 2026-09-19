#!/usr/bin/env python3
"""§3.3.2 — Fleetbase sync handlers are event-bus entry points only."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDLER_FILE = ROOT / "apps/api/src/porterchain_api/booking_engine/fleetbase_sync_handler.py"
EVENT_BUS_HANDLERS = ROOT / "services/event-bus/porterchain_event_bus/handlers/__init__.py"

_IMPORT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "services/event-bus/porterchain_event_bus/handlers/__init__.py",
        "apps/api/src/porterchain_api/booking_engine/fleetbase_sync_handler.py",
        "apps/api/tests/test_customer_persona_p0_integrations.py",
    }
)

_HANDLER_SUFFIX = "_from_event"


def _check_import_sites() -> list[str]:
    failures: list[str] = []
    pattern = "fleetbase_sync_handler"
    for path in sorted(ROOT.rglob("*.py")):
        rel = str(path.relative_to(ROOT))
        if "node_modules" in rel or ".venv" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern not in text:
            continue
        if rel in _IMPORT_ALLOWLIST:
            continue
        if f"from porterchain_api.booking_engine.{pattern}" in text or f"import {pattern}" in text:
            failures.append(f"§3.3.2 direct fleetbase_sync_handler import: {rel}")
    return failures


def _check_handler_shape() -> list[str]:
    failures: list[str] = []
    if not HANDLER_FILE.is_file():
        return [f"§3.3.2 missing handler module: {HANDLER_FILE.relative_to(ROOT)}"]
    tree = ast.parse(HANDLER_FILE.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name.startswith("_"):
            continue
        if not node.name.endswith(_HANDLER_SUFFIX):
            failures.append(f"§3.3.2 handler must end with {_HANDLER_SUFFIX!r}: {node.name}")
        arg_names = [a.arg for a in node.args.args]
        if arg_names != ["envelope"]:
            failures.append(f"§3.3.2 handler {node.name} must accept envelope only")
    return failures


def main() -> int:
    failures = _check_import_sites() + _check_handler_shape()
    if failures:
        print("Fleetbase event-handler guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Fleetbase event-handler guard passed (§3.3.2 — event-bus only, envelope handlers).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
