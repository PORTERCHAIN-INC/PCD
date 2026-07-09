#!/usr/bin/env python3
"""§5.4.4 — print EXPLAIN plans for load-test hot paths (local Postgres)."""

from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text


def main() -> int:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://porterchain:porterchain@localhost:5432/porterchain",
    )
    if url.startswith("sqlite"):
        print("PostgreSQL required for EXPLAIN plans")
        return 1

    engine = create_engine(url)
    statements = (
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT id FROM orders ORDER BY created_at DESC LIMIT 50",
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT id FROM orders WHERE merchant_id IS NOT NULL ORDER BY created_at DESC LIMIT 50",
        "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT id FROM quotes ORDER BY created_at DESC LIMIT 20",
    )

    with engine.connect() as conn:
        for stmt in statements:
            print(f"\n--- {stmt.split('FROM', 1)[1].strip()} ---")
            rows = conn.execute(text(stmt)).fetchall()
            for row in rows:
                print(row[0])

    print("\nReview: prefer Index Scan / limit rows; avoid Seq Scan on large tables under load.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
