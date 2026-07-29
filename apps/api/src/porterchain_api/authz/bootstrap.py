#!/usr/bin/env python3
"""Bootstrap SpiceDB relationships from Postgres profile rows (one-shot).

Usage (from apps/api with venv):
  PYTHONPATH=src python -m porterchain_api.authz.bootstrap
"""

from __future__ import annotations

from porterchain_api.authz.tuples import bootstrap_all_profiles
from porterchain_api.db import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        result = bootstrap_all_profiles(db)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
