#!/usr/bin/env python3
"""ARCH-G3 — quarterly masterrule §3 layered architecture grep audit."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src/porterchain_api"
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
                failures.append(f"masterrule §3.7 UI fetch to retired vendor :8000: {rel}")
            if re.search(r"fetch\([^)]*fleetbase", text, re.IGNORECASE):
                failures.append(f"masterrule §3.7 UI fetch to retired Fleetbase host: {rel}")
    return failures


def _check_adapter_gone() -> list[str]:
    adapter = ROOT / "services/fleetbase-adapter"
    if adapter.is_dir():
        return ["masterrule §3.6 services/fleetbase-adapter still present — remove with cutover"]
    return []


def _check_models_no_http() -> list[str]:
    failures: list[str] = []
    for pattern in _MODEL_GLOBS:
        for path in sorted(API_SRC.glob(pattern)):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "import httpx" in text or "import requests" in text:
                rel = path.relative_to(API_SRC)
                failures.append(f"masterrule §3.5 ORM module has HTTP client: {rel}")
    return failures


def main() -> int:
    failures = (
        _check_ui_no_fleetbase_fetch()
        + _check_adapter_gone()
        + _check_models_no_http()
    )
    if failures:
        print("Masterrule §3 layer audit failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Masterrule §3 layer audit passed (ARCH-G3 — UI clean, adapter gone, ORM layers clean).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
