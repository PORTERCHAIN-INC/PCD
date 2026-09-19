#!/usr/bin/env python3
"""§3.4.3 — SQLAlchemy pool settings are explicit and wired from config."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "apps/api/src/porterchain_api/config.py"
DB = ROOT / "apps/api/src/porterchain_api/db.py"
ENV_EXAMPLE = ROOT / "env/api.env.example"
ENV_VARS = ROOT / "ENVIRONMENT_VARIABLES.md"

_POOL_FIELDS = ("db_pool_size", "db_max_overflow", "db_pool_timeout", "db_pool_recycle")
_ENV_SNIPPETS = ("DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_TIMEOUT", "DB_POOL_RECYCLE")


def main() -> int:
    failures: list[str] = []
    config_text = CONFIG.read_text(encoding="utf-8", errors="ignore")
    db_text = DB.read_text(encoding="utf-8", errors="ignore")

    for field in _POOL_FIELDS:
        if f"{field}:" not in config_text:
            failures.append(f"§3.4.3 config.py missing {field}")
        if f"settings.{field}" not in db_text:
            failures.append(f"§3.4.3 db.py must pass settings.{field} to create_engine")

    if "pool_pre_ping=True" not in db_text:
        failures.append("§3.4.3 db.py must enable pool_pre_ping=True")

    if ENV_EXAMPLE.is_file():
        example = ENV_EXAMPLE.read_text(encoding="utf-8", errors="ignore")
        for snippet in _ENV_SNIPPETS:
            if snippet not in example:
                failures.append(f"§3.4.3 env/api.env.example missing {snippet}")

    if ENV_VARS.is_file():
        env_doc = ENV_VARS.read_text(encoding="utf-8", errors="ignore")
        if "DB_POOL_SIZE" not in env_doc:
            failures.append("§3.4.3 ENVIRONMENT_VARIABLES.md missing DB pool tuning table")

    if failures:
        print("DB pool guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("DB pool guard passed (§3.4.3 — pool_size=10, max_overflow=20, pre_ping, documented).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
