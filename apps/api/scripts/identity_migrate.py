#!/usr/bin/env python3
"""Clerk → PorterChain identity migration CLI (Phase 7).

Dry-run is the default. Apply requires --confirm APPLY.
Exports must live outside the git repository.

Usage:
  pnpm identity:migrate -- audit --exports-dir ~/porterchain-migration-exports
  pnpm identity:migrate -- plan --exports-dir ... --label local-1 \\
      --map ~/porterchain-migration-exports/map.json \\
      --admin-allowlist ~/porterchain-migration-exports/admin-allowlist.json
  pnpm identity:migrate -- dry-run --run-id <id>
  pnpm identity:migrate -- apply --run-id <id> --confirm APPLY
  pnpm identity:migrate -- verify --run-id <id>
  pnpm identity:migrate -- conflicts --run-id <id>

Does not call production Clerk or Doppler. Does not delete legacy apps.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
_REPO = _ROOT.parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
_SHARED = _REPO / "shared" / "python"
if _SHARED.is_dir() and str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))


def _print(obj: object) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, default=str))


def _session():
    from porterchain_api.db import SessionLocal

    return SessionLocal()


def cmd_audit(args: argparse.Namespace) -> int:
    from porterchain_api.auth.identity_migration import audit_exports, audit_legacy_db, load_exports_dir

    report: dict = {"repo_root": str(_REPO)}
    if args.exports_dir:
        sources = load_exports_dir(Path(args.exports_dir), repo_root=_REPO if not args.allow_in_repo else None)
        report["exports"] = audit_exports(sources)
    if args.db:
        db = _session()
        try:
            report["legacy_db"] = audit_legacy_db(db)
        finally:
            db.close()
    if "exports" not in report and "legacy_db" not in report:
        print("Provide --exports-dir and/or --db", file=sys.stderr)
        return 2
    _print(report)
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    from porterchain_api.auth.identity_migration import (
        build_migration_plan,
        load_admin_allowlist,
        load_explicit_map,
        load_exports_dir,
        persist_plan,
    )

    sources = load_exports_dir(
        Path(args.exports_dir),
        repo_root=_REPO if not args.allow_in_repo else None,
    )
    allowlist = load_admin_allowlist(Path(args.admin_allowlist) if args.admin_allowlist else None)
    explicit = load_explicit_map(Path(args.map) if args.map else None)

    db = _session()
    try:
        plan = build_migration_plan(
            label=args.label,
            sources=sources,
            explicit_map=explicit,
            allowlist=allowlist,
            db=db,
        )
        run = persist_plan(db, plan, dry_run=True)
        _print(
            {
                "run_id": run.id,
                "label": run.label,
                "status": run.status,
                "dry_run": run.dry_run,
                "counts": run.counts,
                "source_summary": run.source_summary,
                "next": f"pnpm identity:migrate -- dry-run --run-id {run.id}",
            }
        )
    finally:
        db.close()
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    from porterchain_api.auth.identity_migration import apply_run, conflict_report

    db = _session()
    try:
        result = apply_run(db, args.run_id, dry_run=True, accept_email_candidates=args.accept_email_candidates)
        result["conflicts"] = conflict_report(db, args.run_id)
        _print(result)
    finally:
        db.close()
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    from porterchain_api.auth.identity_migration import apply_run

    db = _session()
    try:
        result = apply_run(
            db,
            args.run_id,
            dry_run=False,
            accept_email_candidates=args.accept_email_candidates,
            confirm=args.confirm,
        )
        _print(result)
    finally:
        db.close()
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from porterchain_api.auth.identity_migration import verify_run

    db = _session()
    try:
        result = verify_run(db, args.run_id)
        _print(result)
        return 0 if result.get("ok") else 1
    finally:
        db.close()


def cmd_conflicts(args: argparse.Namespace) -> int:
    from porterchain_api.auth.identity_migration import conflict_report

    db = _session()
    try:
        _print(conflict_report(db, args.run_id))
    finally:
        db.close()
    return 0


def cmd_backfill_audit(args: argparse.Namespace) -> int:
    from porterchain_api.auth.identity_fk_backfill import audit_fk_coverage

    db = _session()
    try:
        _print(audit_fk_coverage(db))
    finally:
        db.close()
    return 0


def cmd_backfill(args: argparse.Namespace) -> int:
    from porterchain_api.auth.identity_fk_backfill import backfill_profile_fks

    dry_run = not args.apply
    if args.apply and args.confirm != "APPLY":
        print('backfill --apply requires --confirm APPLY', file=sys.stderr)
        return 2

    db = _session()
    try:
        report = backfill_profile_fks(
            db,
            dry_run=dry_run,
            create_missing=args.create_missing,
            heal_identity_links=not args.skip_heal_links,
        )
        _print(report.to_dict())
    finally:
        db.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PorterChain identity migration (Phase 7/8)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help="Summarize exports and/or legacy DB clerk links")
    p_audit.add_argument("--exports-dir", help="Directory of Clerk export JSON (outside repo)")
    p_audit.add_argument("--db", action="store_true", help="Also audit legacy clerk_user_id counts in Postgres")
    p_audit.add_argument(
        "--allow-in-repo",
        action="store_true",
        help="Unsafe: allow reading exports from inside the git tree (tests only)",
    )
    p_audit.set_defaults(func=cmd_audit)

    p_plan = sub.add_parser("plan", help="Build and persist a migration plan (always dry_run=true)")
    p_plan.add_argument("--exports-dir", required=True)
    p_plan.add_argument("--label", required=True)
    p_plan.add_argument("--map", help="Reviewed explicit mapping JSON")
    p_plan.add_argument("--admin-allowlist", help="Reviewed admin clerk user id allowlist JSON")
    p_plan.add_argument("--allow-in-repo", action="store_true")
    p_plan.set_defaults(func=cmd_plan)

    p_dry = sub.add_parser("dry-run", help="Simulate apply; no user mutations")
    p_dry.add_argument("--run-id", required=True)
    p_dry.add_argument("--accept-email-candidates", action="store_true")
    p_dry.set_defaults(func=cmd_dry_run)

    p_apply = sub.add_parser("apply", help="Apply plan (requires --confirm APPLY)")
    p_apply.add_argument("--run-id", required=True)
    p_apply.add_argument("--confirm", required=True, help='Must be exactly "APPLY"')
    p_apply.add_argument("--accept-email-candidates", action="store_true")
    p_apply.set_defaults(func=cmd_apply)

    p_verify = sub.add_parser("verify", help="Verify run completeness")
    p_verify.add_argument("--run-id", required=True)
    p_verify.set_defaults(func=cmd_verify)

    p_conflicts = sub.add_parser("conflicts", help="Print conflict report for a run")
    p_conflicts.add_argument("--run-id", required=True)
    p_conflicts.set_defaults(func=cmd_conflicts)

    p_bf_audit = sub.add_parser(
        "backfill-audit",
        help="Phase 8: coverage of porterchain_user_id on profile tables (counts only)",
    )
    p_bf_audit.set_defaults(func=cmd_backfill_audit)

    p_bf = sub.add_parser(
        "backfill",
        help="Phase 8: backfill porterchain_user_id (dry-run default; --apply --confirm APPLY)",
    )
    p_bf.add_argument(
        "--apply",
        action="store_true",
        help="Write FKs (default is dry-run)",
    )
    p_bf.add_argument("--confirm", default="", help='Required as "APPLY" when using --apply')
    p_bf.add_argument(
        "--create-missing",
        action="store_true",
        help="Create unprovisioned porterchain_users when no match (apply only)",
    )
    p_bf.add_argument(
        "--skip-heal-links",
        action="store_true",
        help="Do not repair identity_links.platform_user_id mis-points",
    )
    p_bf.set_defaults(func=cmd_backfill)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
