#!/usr/bin/env python3
"""LOCAL ONLY: prune Postgres identity/persona rows to live Platform Clerk users.

Keeps business rows that FKs need (orders → customers) but strips Clerk linkage
and deletes porterchain_users / admin / merchant personas not in Clerk.
Revokes SpiceDB tuples for removed accounts.

Usage:
  PYTHONPATH=src:../../shared/python .venv/bin/python scripts/prune_users_to_clerk.py --dry-run
  PYTHONPATH=src:../../shared/python .venv/bin/python scripts/prune_users_to_clerk.py --confirm PRUNE_LOCAL
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parents[1] / "shared" / "python"))

from porterchain_api.admin_models import AdminUser, Driver  # noqa: E402
from porterchain_api.auth.clerk_client import ClerkClient  # noqa: E402
from porterchain_api.auth.clerk_registry import (  # noqa: E402
    clerk_client_for_kind,
    resolve_platform_clerk_config,
)
from porterchain_api.authz.tuples import TupleWriter  # noqa: E402
from porterchain_api.config import Settings  # noqa: E402
from porterchain_api.db import SessionLocal  # noqa: E402
from porterchain_api.identity_models import IdentityLink  # noqa: E402
from porterchain_api.merchant_models import MerchantUser  # noqa: E402
from porterchain_api.models import Customer  # noqa: E402
from porterchain_api.unified_identity_models import UserEmail  # noqa: E402
from porterchain_api.user_models import PorterchainUser  # noqa: E402
from porterchain_shared.redis_health import is_local_env  # noqa: E402


def _list_clerk_ids(client: ClerkClient) -> dict[str, str]:
    """clerk_user_id → primary email."""
    out: dict[str, str] = {}
    offset = 0
    while True:
        batch, _ = client.list_users(limit=100, offset=offset)
        if not batch:
            break
        for u in batch:
            cid = str(u.get("id") or "")
            if not cid:
                continue
            out[cid] = (ClerkClient.primary_email(u) or "").lower()
        if len(batch) < 100:
            break
        offset += 100
        if offset > 5000:
            break
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", default="", help="Must be PRUNE_LOCAL")
    args = parser.parse_args()

    settings = Settings()
    if not is_local_env(settings.app_env):
        raise SystemExit(f"refusing: APP_ENV={settings.app_env!r} is not local")
    platform = resolve_platform_clerk_config(settings)
    if not platform or not platform.secret_key:
        raise SystemExit("Platform Clerk secret missing")
    host = platform.jwks_url.split("/")[2]
    if "porterchain.com" in host and not host.endswith(".clerk.accounts.dev"):
        raise SystemExit(f"refusing live JWKS host: {host}")

    client = clerk_client_for_kind(settings, "admin")
    clerk_map = _list_clerk_ids(client)
    clerk_ids = set(clerk_map.keys())
    print(json.dumps({"clerk_host": host, "clerk_users": len(clerk_ids), "emails": list(clerk_map.values())}, indent=2))

    if not clerk_ids:
        raise SystemExit("refusing: Clerk returned 0 users — abort prune")

    if args.dry_run or args.confirm != "PRUNE_LOCAL":
        db = SessionLocal()
        try:
            pc = db.query(PorterchainUser).all()
            ghost = [u for u in pc if not u.clerk_user_id or u.clerk_user_id not in clerk_ids]
            print(f"dry_run: would remove {len(ghost)}/{len(pc)} porterchain_users")
            print(f"keep: {[u.email for u in pc if u.clerk_user_id in clerk_ids]}")
        finally:
            db.close()
        if args.confirm != "PRUNE_LOCAL":
            print("Re-run with --confirm PRUNE_LOCAL to apply.")
        return

    db = SessionLocal()
    summary: dict[str, int] = {}
    try:
        # 1) Revoke SpiceDB + delete ghost porterchain_users (+ emails / links / ACL leftovers)
        ghosts = [
            u
            for u in db.query(PorterchainUser).all()
            if not u.clerk_user_id or u.clerk_user_id not in clerk_ids
        ]
        ghost_ids = [u.id for u in ghosts]
        if ghost_ids:
            # Legacy ACL tables still FK to porterchain_users on local DBs.
            from sqlalchemy import text

            db.execute(
                text("DELETE FROM user_role_assignments WHERE user_id = ANY(:ids)"),
                {"ids": ghost_ids},
            )
            db.execute(
                text("DELETE FROM user_permission_overrides WHERE user_id = ANY(:ids)"),
                {"ids": ghost_ids},
            )
            summary["acl_rows_deleted"] = len(ghost_ids)
        for u in ghosts:
            try:
                TupleWriter().revoke_all_for_user(db, u)
            except Exception as exc:  # noqa: BLE001
                print(f"  warn revoke {u.email}: {exc}")
            db.query(UserEmail).filter(UserEmail.user_id == u.id).delete(synchronize_session=False)
            db.query(IdentityLink).filter(IdentityLink.platform_user_id == u.id).delete(
                synchronize_session=False
            )
            db.delete(u)
            summary["porterchain_users_deleted"] = summary.get("porterchain_users_deleted", 0) + 1

        # 2) Admin / merchant — hard delete if not in Clerk
        for row in db.query(AdminUser).all():
            if not row.clerk_user_id or row.clerk_user_id not in clerk_ids:
                db.delete(row)
                summary["admin_users_deleted"] = summary.get("admin_users_deleted", 0) + 1
        for row in db.query(MerchantUser).all():
            if not row.clerk_user_id or row.clerk_user_id not in clerk_ids:
                db.delete(row)
                summary["merchant_users_deleted"] = summary.get("merchant_users_deleted", 0) + 1

        # 3) Drivers — unlink Clerk (nullable)
        for row in db.query(Driver).all():
            if row.clerk_user_id and row.clerk_user_id not in clerk_ids:
                row.clerk_user_id = None
                if hasattr(row, "porterchain_user_id"):
                    row.porterchain_user_id = None
                summary["drivers_unlinked"] = summary.get("drivers_unlinked", 0) + 1

        # 4) Customers — clerk_user_id is NOT NULL; delete row or tombstone id
        for row in list(db.query(Customer).all()):
            if not row.clerk_user_id or row.clerk_user_id in clerk_ids:
                continue
            try:
                with db.begin_nested():
                    db.delete(row)
                summary["customers_deleted"] = summary.get("customers_deleted", 0) + 1
            except Exception:  # noqa: BLE001
                row.clerk_user_id = f"unlinked:{row.id}"
                if hasattr(row, "porterchain_user_id"):
                    try:
                        row.porterchain_user_id = None
                    except Exception:  # noqa: BLE001
                        pass
                summary["customers_tombstoned"] = summary.get("customers_tombstoned", 0) + 1

        # 4) Orphan identity_links
        for link in db.query(IdentityLink).all():
            sub = link.subject or link.clerk_user_id
            if not sub or sub not in clerk_ids:
                db.delete(link)
                summary["identity_links_deleted"] = summary.get("identity_links_deleted", 0) + 1

        db.commit()

        # 5) Re-sync SpiceDB for survivors
        for u in db.query(PorterchainUser).all():
            TupleWriter().sync_user_from_profiles(db, u)
        db.commit()

        kept = [
            {"email": u.email, "clerk_user_id": u.clerk_user_id}
            for u in db.query(PorterchainUser).all()
        ]
        print(json.dumps({"status": "ok", "summary": summary, "kept": kept}, indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
