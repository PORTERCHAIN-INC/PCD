#!/usr/bin/env python3
"""§3.3.3 — notification templates resolve from notification_engine catalog."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src/porterchain_api"
TEMPLATES_FILE = API_SRC / "notification_engine/templates.py"
EVENT_ROUTER = API_SRC / "notification_engine/event_router.py"

# Legacy modules that call dispatch() directly (shrink over time).
_LEGACY_DIRECT_DISPATCH: frozenset[str] = frozenset(
    {
        "notification_engine/orchestrator.py",
        "admin_engine/notification_admin_service.py",
        "admin_engine/e2e_validation_forward.py",
        "admin_engine/order_assist_service.py",
        "routers/drivers_admin.py",
    }
)

_EVENT_ROUTER_LITERAL_TEMPLATES: frozenset[str] = frozenset(
    {
        "order_created",
        "order_booked",
    }
)


def _catalog_keys() -> set[str]:
    text = TEMPLATES_FILE.read_text(encoding="utf-8", errors="ignore")
    in_templates = False
    keys: set[str] = set()
    for line in text.splitlines():
        if line.startswith("TEMPLATES:"):
            in_templates = True
            continue
        if in_templates and line.startswith("def "):
            break
        if in_templates:
            match = re.match(r'\s+"([a-z_]+)":\s*\{', line)
            if match:
                keys.add(match.group(1))
    return keys


def _event_router_templates() -> set[str]:
    text = EVENT_ROUTER.read_text(encoding="utf-8", errors="ignore")
    keys = set(re.findall(r'add\(\s*"([a-z_]+)"', text))
    keys.update(_EVENT_ROUTER_LITERAL_TEMPLATES)
    return keys


def _direct_dispatch_templates() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    pattern = re.compile(r'template_key\s*=\s*"([a-z_]+)"')
    for path in sorted(API_SRC.rglob("*.py")):
        rel = str(path.relative_to(API_SRC))
        if rel == "notification_engine/event_router.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "template_key" not in text:
            continue
        for match in pattern.finditer(text):
            found.append((rel, match.group(1)))
    return found


def main() -> int:
    failures: list[str] = []
    catalog = _catalog_keys()
    if not catalog:
        failures.append("§3.3.3 could not load TEMPLATES catalog")

    for key in sorted(_event_router_templates()):
        if key not in catalog:
            failures.append(f"§3.3.3 event_router template not in catalog: {key}")

    for rel, key in _direct_dispatch_templates():
        if key not in catalog:
            failures.append(f"§3.3.3 template not in catalog ({rel}): {key}")
        if rel not in _LEGACY_DIRECT_DISPATCH and rel != "notification_engine/engine.py":
            failures.append(f"§3.3.3 new direct dispatch outside event_router: {rel}")

    if failures:
        print("Notification catalog guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        f"Notification catalog guard passed (§3.3.3 — {len(catalog)} templates; "
        f"{len(_LEGACY_DIRECT_DISPATCH)} legacy dispatch modules)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
