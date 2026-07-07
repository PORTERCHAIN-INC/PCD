#!/usr/bin/env python3
"""Run Enterprise E2E Operations Validation Framework (masterrule §16).

Usage:
    cd apps/api && PYTHONPATH=src python scripts/run_e2e_validation.py
    cd apps/api && PYTHONPATH=src python scripts/run_e2e_validation.py --write-files
    cd apps/api && PYTHONPATH=src python scripts/run_e2e_validation.py --merchant-orders 10 --no-cleanup
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))

from porterchain_api.admin_engine.e2e_validation_catalog import DEFAULT_MERCHANT_BULK_COUNT
from porterchain_api.admin_engine.e2e_validation_service import E2EValidationService
from porterchain_api.config import get_settings
from porterchain_api.db import SessionLocal, init_db


def main() -> int:
    parser = argparse.ArgumentParser(description="Porterchain E2E validation framework")
    parser.add_argument("--write-files", action="store_true", help="Write markdown reports to repo root")
    parser.add_argument("--no-cleanup", action="store_true", help="Keep E2E test orders in database")
    parser.add_argument(
        "--merchant-orders",
        type=int,
        default=DEFAULT_MERCHANT_BULK_COUNT,
        help=f"Merchant bulk order count (default {DEFAULT_MERCHANT_BULK_COUNT})",
    )
    args = parser.parse_args()

    init_db()
    settings = get_settings()
    svc = E2EValidationService()

    print("Porterchain Enterprise E2E Validation")
    print(f"Environment: {settings.app_env}")
    print("-" * 48)

    with SessionLocal() as db:
        result = svc.run_full(
            db,
            settings,
            write_files=args.write_files,
            cleanup=not args.no_cleanup,
            merchant_order_count=args.merchant_orders,
        )

    summary = result["summary"]
    print(f"Overall: {result['overall']}")
    print(f"Production ready: {result['production_ready']}")
    print(f"Pass={summary['pass']} Warning={summary['warning']} Fail={summary['fails']} Blocker={summary['blockers']}")
    print(f"Execution: {result['execution_ms']}ms")
    print("-" * 48)

    for key, phase in result["phases"].items():
        print(f"  {phase.get('name', key)}: {phase.get('overall', '—')}")

    if result.get("auto_fixes"):
        print("-" * 48)
        print("Auto-fixes:")
        for fix in result["auto_fixes"]:
            print(f"  - {fix.get('fix')}: {fix.get('action')}")

    if args.write_files and result.get("written_files"):
        print("-" * 48)
        print("Reports written:")
        for path in result["written_files"]:
            print(f"  {path}")

    if result["overall"] in ("BLOCKER", "FAIL"):
        print("-" * 48)
        print("RESULT: FAILED")
        return 1

    print("-" * 48)
    print("RESULT: PASSED" if result["production_ready"] else "RESULT: PASSED WITH WARNINGS")
    return 0 if result["production_ready"] or result["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
