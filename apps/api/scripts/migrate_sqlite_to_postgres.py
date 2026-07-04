#!/usr/bin/env python3
"""Optional SQLite → PostgreSQL migration with row-count validation.

Usage:
  cd apps/api && source .venv/bin/activate
  export PYTHONPATH=src
  python scripts/migrate_sqlite_to_postgres.py --sqlite ./porterchain.db --dry-run
  python scripts/migrate_sqlite_to_postgres.py --sqlite ./porterchain.db --execute

Stops on row-count mismatch or FK errors. Does NOT modify Fleetbase MySQL.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

API_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PG = "postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain"

SKIP_TABLES = {"alembic_version", "sqlite_sequence"}


def sqlite_tables(path: Path) -> list[str]:
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return [r[0] for r in rows if r[0] not in SKIP_TABLES]
    finally:
        conn.close()


def row_count_sqlite(path: Path, table: str) -> int:
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def row_count_pg(engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()


def migrate_table(sqlite_path: Path, pg_engine, table: str, *, execute: bool) -> tuple[int, int]:
    src_count = row_count_sqlite(sqlite_path, table)
    if not execute:
        print(f"  [dry-run] {table}: {src_count} rows (would copy)")
        return src_count, 0

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    finally:
        conn.close()

    if not rows:
        return 0, 0

    columns = rows[0].keys()
    col_list = ", ".join(columns)
    placeholders = ", ".join(f":{c}" for c in columns)
    insert_sql = text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING")

    inserted = 0
    with pg_engine.begin() as pg:
        for row in rows:
            pg.execute(insert_sql, dict(row))
            inserted += 1

    dst_count = row_count_pg(pg_engine, table)
    if dst_count < src_count:
        raise RuntimeError(f"{table}: source={src_count} destination={dst_count} — count mismatch")
    return src_count, inserted


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Porterchain SQLite file to PostgreSQL")
    parser.add_argument("--sqlite", type=Path, default=API_ROOT / "porterchain.db")
    parser.add_argument("--postgres", default=DEFAULT_PG)
    parser.add_argument("--execute", action="store_true", help="Perform copy (default is dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    if not args.sqlite.exists():
        print(f"No SQLite file at {args.sqlite} — nothing to migrate.")
        return 0

    if args.postgres.startswith("sqlite"):
        print("ERROR: --postgres must be a PostgreSQL URL", file=sys.stderr)
        return 1

    execute = args.execute and not args.dry_run
    pg_engine = create_engine(args.postgres, pool_pre_ping=True)

    if execute:
        insp = inspect(pg_engine)
        if not insp.get_table_names():
            print("ERROR: PostgreSQL has no tables. Run `pnpm db:migrate` first.", file=sys.stderr)
            return 1

    tables = sqlite_tables(args.sqlite)
    print(f"SQLite: {args.sqlite} ({len(tables)} tables)")
    print(f"PostgreSQL: {args.postgres}")
    print(f"Mode: {'EXECUTE' if execute else 'DRY-RUN'}")
    print("-" * 48)

    try:
        for table in tables:
            migrate_table(args.sqlite, pg_engine, table, execute=execute)
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print("-" * 48)
    print("SUCCESS" if execute else "DRY-RUN complete — re-run with --execute to copy data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
