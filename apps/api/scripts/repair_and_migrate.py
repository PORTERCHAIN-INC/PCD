#!/usr/bin/env python3
"""Repair common Alembic drift on production and apply pending migrations."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

# Allow `from ensure_production_basics import ...` when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from porterchain_api.db import SessionLocal, engine


def _table_exists(name: str) -> bool:
    return inspect(engine).has_table(name)


def _alembic_version() -> str | None:
    if not _table_exists("alembic_version"):
        return None
    with SessionLocal() as db:
        row = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
        return row[0] if row else None


def _repair_partial_initial_migration() -> bool:
    """Drop orphaned first table so the initial migration can run from scratch."""
    if not _table_exists("abandoned_checkouts"):
        return False
    if _table_exists("quotes"):
        return False
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS abandoned_checkouts CASCADE"))
    print("repair: dropped orphaned abandoned_checkouts (partial initial migration)")
    return True


def main() -> int:
    version = _alembic_version()
    quotes = _table_exists("quotes")
    print(f"repair: alembic_version={version!r} quotes_table={quotes}")

    if quotes and version is None:
        print("repair: schema present without alembic_version — will stamp after upgrade attempt")

    _repair_partial_initial_migration()

    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    try:
        command.upgrade(cfg, "head")
        print("repair: alembic upgrade head OK")
    except Exception as exc:
        err = str(exc)
        print(f"repair: alembic upgrade failed: {err}", file=sys.stderr)
        if quotes and ("DuplicateTable" in err or "already exists" in err.lower()):
            print("repair: stamping head (tables already present)")
            command.stamp(cfg, "head")
            try:
                command.upgrade(cfg, "head")
                print("repair: alembic upgrade after stamp OK")
            except Exception as exc2:
                print(f"repair: upgrade after stamp failed: {exc2}", file=sys.stderr)
                return 1
        elif _table_exists("quotes"):
            print("repair: quotes exist — stamping head as fallback")
            command.stamp(cfg, "head")
        else:
            return 1

    from ensure_production_basics import ensure_production_basics

    ensure_production_basics()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
