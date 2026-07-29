#!/usr/bin/env python3
"""Clerk / Doppler config audit CLI — names + validity only (never secret values).

Usage (from repo root):
  pnpm config:audit
  cd apps/api && PYTHONPATH=src .venv/bin/python scripts/config_audit.py
  cd apps/api && PYTHONPATH=src .venv/bin/python scripts/config_audit.py --strict
  cd apps/api && PYTHONPATH=src .venv/bin/python scripts/config_audit.py --json

Does not call Doppler. Does not mutate secrets.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running without installing the package
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Clerk config (names + validity only)")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON report",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when production_errors are present (also fails local if APP_ENV is production-like)",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="Optional path to .env (default: apps/api/.env via Settings)",
    )
    args = parser.parse_args(argv)

    from porterchain_api.auth.clerk_config_audit import audit_report_dict
    from porterchain_api.config import Settings

    if args.env_file:
        settings = Settings(_env_file=args.env_file)
    else:
        settings = Settings()

    report = audit_report_dict(settings)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"mode={report['mode']}  registry_mode={report['registry_mode']}  app_env={report['app_env']}")
        print("--- findings (names only; no secret values) ---")
        for f in report["findings"]:
            detail = f" — {f['detail']}" if f.get("detail") else ""
            print(f"  [{f['status']}] {f['name']}{detail}")
        errs = report.get("production_errors") or []
        if errs:
            print("--- production_errors ---")
            for e in errs:
                print(f"  ERROR {e}")
        else:
            print("--- production_errors: none ---")
        print("Note: Doppler was not contacted. Cutover remains manual (see docs/runbooks/clerk-consolidation.md).")

    if args.strict and report.get("production_errors"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
