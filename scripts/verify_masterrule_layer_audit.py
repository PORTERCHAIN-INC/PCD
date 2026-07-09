#!/usr/bin/env python3
"""ARCH-G3 — quarterly masterrule §3 layered architecture grep audit."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src/porterchain_api"
ADAPTER_SRC = ROOT / "services/fleetbase-adapter"
AUDIT_LOG = ROOT / "docs/architecture/MASTERRULE_LAYER_AUDIT.md"

_WEB_ROOTS = (
    ROOT / "apps/admin/src",
    ROOT / "apps/merchant-portal/src",
    ROOT / "apps/driver-portal/src",
    ROOT / "apps/customer/src",
    ROOT / "website/src",
)

_MODEL_GLOBS = ("*_models.py", "models.py", "booking_models.py")


def _check_ui_no_fleetbase_fetch() -> list[str]:
    failures: list[str] = []
    for root in _WEB_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            rel = str(path.relative_to(ROOT))
            if "system-links" in rel:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"fetch\([^)]*localhost:8000", text):
                failures.append(f"masterrule §3.7 UI fetch to Fleetbase :8000: {rel}")
            if re.search(r"fetch\([^)]*fleetbase", text, re.IGNORECASE):
                failures.append(f"masterrule §3.7 UI fetch to Fleetbase: {rel}")
    return failures


def _check_adapter_no_domain_logic() -> list[str]:
    failures: list[str] = []
    if not ADAPTER_SRC.is_dir():
        return failures
    for path in sorted(ADAPTER_SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "porterchain_api.domain" in text or "booking_engine" in text:
            rel = path.relative_to(ROOT)
            failures.append(f"masterrule §3.6 adapter imports domain logic: {rel}")
        if re.search(r"(^|\n)\s*from sqlalchemy|import sqlalchemy", text):
            rel = path.relative_to(ROOT)
            failures.append(f"masterrule §3.6 adapter must not use SQLAlchemy: {rel}")
    return failures


def _check_models_no_http() -> list[str]:
    failures: list[str] = []
    for pattern in _MODEL_GLOBS:
        for path in sorted(API_SRC.glob(pattern)):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "import httpx" in text or "import requests" in text:
                rel = path.relative_to(API_SRC)
                failures.append(f"masterrule §3.5 ORM module has HTTP client: {rel}")
    return failures


def _check_audit_log() -> list[str]:
    failures: list[str] = []
    if not AUDIT_LOG.is_file():
        failures.append("ARCH-G3 missing docs/architecture/MASTERRULE_LAYER_AUDIT.md")
        return failures
    text = AUDIT_LOG.read_text(encoding="utf-8", errors="ignore")
    if "2026-Q3" not in text:
        failures.append("ARCH-G3 audit log missing 2026-Q3 entry")
    if "PASS" not in text:
        failures.append("ARCH-G3 audit log missing PASS result row")
    if "verify_masterrule_layer_audit.py" not in text:
        failures.append("ARCH-G3 audit log must reference verify_masterrule_layer_audit.py")
    return failures


def main() -> int:
    failures = (
        _check_ui_no_fleetbase_fetch()
        + _check_adapter_no_domain_logic()
        + _check_models_no_http()
        + _check_audit_log()
    )
    if failures:
        print("Masterrule §3 layer audit failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Masterrule §3 layer audit passed (ARCH-G3 — UI, adapter, ORM layers clean).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
