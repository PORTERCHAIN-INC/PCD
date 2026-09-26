#!/usr/bin/env python3
"""§3.2.13 — Pydantic schemas owned per bounded context."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "apps/api/src/porterchain_api"

_CONTEXT_SCHEMA_MODULES: tuple[str, ...] = (
    "schemas_booking.py",
    "schemas_admin.py",
    "schemas_auth.py",
    "schemas_crm.py",
    "schemas_driver.py",
    "schemas_health.py",
    "schemas_merchant.py",
    "schemas_notifications.py",
    "schemas_oauth.py",
    "schemas_pricing.py",
    "schemas_public.py",
)

_CLASS_DEF_RE = re.compile(r"^class \w+\(.*BaseModel", re.MULTILINE)


def main() -> int:
    failures: list[str] = []

    for rel in _CONTEXT_SCHEMA_MODULES:
        if not (API_SRC / rel).is_file():
            failures.append(f"§3.2.13 missing schema module: {rel}")

    root_schemas = API_SRC / "schemas.py"
    if root_schemas.is_file():
        text = root_schemas.read_text(encoding="utf-8", errors="ignore")
        if _CLASS_DEF_RE.search(text):
            failures.append("§3.2.13 root schemas.py must be a re-export shim only")

    for path in sorted(API_SRC.glob("schemas_*.py")):
        rel = str(path.relative_to(API_SRC))
        if rel not in _CONTEXT_SCHEMA_MODULES:
            failures.append(f"§3.2.13 unexpected root schema module (add to guard): {rel}")

    if failures:
        print("Schema context guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"Schema context guard passed (§3.2.13 — {len(_CONTEXT_SCHEMA_MODULES)} context modules).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
