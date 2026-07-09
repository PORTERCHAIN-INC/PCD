#!/usr/bin/env python3
"""§3.4.7 — managed Postgres + optional read replica wired in config/db."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "apps/api/src/porterchain_api/config.py"
DB = ROOT / "apps/api/src/porterchain_api/db.py"
DOC = ROOT / "DATABASE_ARCHITECTURE.md"
ENV_EXAMPLE = ROOT / "env/api.env.example"

_DOC_SNIPPETS: tuple[str, ...] = (
    "## Managed Postgres",
    "DATABASE_URL_REPLICA",
    "get_read_db",
    "Analytics off primary",
    "DigitalOcean",
)


def main() -> int:
    failures: list[str] = []
    config = CONFIG.read_text(encoding="utf-8", errors="ignore")
    db_text = DB.read_text(encoding="utf-8", errors="ignore")

    if "database_url_replica" not in config:
        failures.append("§3.4.7 config.py missing database_url_replica")
    if "DATABASE_URL_REPLICA" not in config:
        failures.append("§3.4.7 config.py missing DATABASE_URL_REPLICA alias")
    if "get_read_db" not in db_text:
        failures.append("§3.4.7 db.py missing get_read_db()")
    if "_replica_db" not in db_text:
        failures.append("§3.4.7 db.py missing replica engine factory")

    if DOC.is_file():
        doc = DOC.read_text(encoding="utf-8", errors="ignore")
        for snippet in _DOC_SNIPPETS:
            if snippet not in doc:
                failures.append(f"§3.4.7 DATABASE_ARCHITECTURE.md missing: {snippet}")
    else:
        failures.append("§3.4.7 missing DATABASE_ARCHITECTURE.md")

    if ENV_EXAMPLE.is_file():
        env = ENV_EXAMPLE.read_text(encoding="utf-8", errors="ignore")
        if "DATABASE_URL_REPLICA" not in env:
            failures.append("§3.4.7 env/api.env.example missing DATABASE_URL_REPLICA")
    else:
        failures.append("§3.4.7 missing env/api.env.example")

    if failures:
        print("Managed Postgres guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("Managed Postgres guard passed (§3.4.7 — primary + optional replica documented and wired).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
