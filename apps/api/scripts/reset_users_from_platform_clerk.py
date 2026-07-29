#!/usr/bin/env python3
"""LOCAL ONLY: wipe public tables, then import users from PorterChain Platform Clerk.

Usage:
  PYTHONPATH=src:../../shared/python .venv/bin/python scripts/reset_users_from_platform_clerk.py --dry-run
  PYTHONPATH=src:../../shared/python .venv/bin/python scripts/reset_users_from_platform_clerk.py --confirm WIPE_LOCAL

Never runs against non-local APP_ENV. Never deletes Clerk applications.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parents[1] / "shared" / "python"))

from sqlalchemy import text  # noqa: E402

from porterchain_api.admin_models import AdminUser, Driver  # noqa: E402
from porterchain_api.auth.clerk_client import ClerkClient  # noqa: E402
from porterchain_api.auth.clerk_registry import (  # noqa: E402
    clerk_client_for_kind,
    resolve_platform_clerk_config,
)
from porterchain_api.auth.unified_catalog import AccountStatus, AssignableRole  # noqa: E402
from porterchain_api.config import Settings  # noqa: E402
from porterchain_api.db import SessionLocal, engine  # noqa: E402
from porterchain_api.identity_models import IdentityLink  # noqa: E402
from porterchain_api.merchant_models import Merchant, MerchantUser  # noqa: E402
from porterchain_api.models import Customer  # noqa: E402
from porterchain_api.user_models import PorterchainUser  # noqa: E402
from porterchain_shared.redis_health import is_local_env  # noqa: E402

FOUNDER_ADMIN_EMAILS = frozenset(
    {
        "porterchaininc@gmail.com",
        "admin@porterchain.com",
    }
)


def _mask(email: str | None) -> str:
    if not email:
        return "(none)"
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}" if domain else "***"


def _primary_email(user: dict) -> str | None:
    return ClerkClient.primary_email(user)


def _list_platform_users(client: ClerkClient) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while True:
        batch, _total = client.list_users(limit=100, offset=offset)
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
        offset += 100
        if offset > 5000:
            break
    return out


def _wipe_all_public_tables() -> list[str]:
    wiped: list[str] = []
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
                """
            )
        ).fetchall()
        # Disable triggers briefly for truncate speed; CASCADE handles FKs.
        for (name,) in rows:
            conn.execute(text(f'TRUNCATE TABLE "{name}" RESTART IDENTITY CASCADE'))
            wiped.append(name)
    return wiped


def _role_for_clerk_user(email: str | None, metadata: dict) -> tuple[str, str]:
    """Return (assignable_role, user_type)."""
    meta_type = str(metadata.get("user_type") or "").lower().strip()
    meta_role = str(metadata.get("role") or metadata.get("porterchain_role") or "").lower().strip()
    email_l = (email or "").lower().strip()

    if email_l in FOUNDER_ADMIN_EMAILS or meta_type in ("admin", "staff") or meta_role in (
        "super_admin",
        "admin",
    ):
        return AssignableRole.SUPER_ADMIN.value, "admin"
    if meta_type == "merchant" or meta_role in ("owner", "admin", "ops", "billing", "viewer"):
        # merchant portal roles map via merchant_role_to_assignable; store owner-ish
        role = meta_role if meta_role in ("owner", "admin", "ops", "billing", "viewer") else "owner"
        return role if role in {r.value for r in AssignableRole} else AssignableRole.MERCHANT_OWNER.value, "merchant"
    if meta_type == "driver" or meta_role == "driver":
        return AssignableRole.DRIVER.value, "driver"
    return AssignableRole.CUSTOMER.value, "customer"


def _import_users(users: list[dict]) -> dict:
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    summary = {"created": 0, "by_type": {}, "skipped": 0}
    try:
        # Shared merchant org for any merchant-type imports
        default_merchant: Merchant | None = None

        for raw in users:
            clerk_id = str(raw.get("id") or "")
            if not clerk_id.startswith("user_"):
                summary["skipped"] += 1
                continue
            email = (_primary_email(raw) or "").lower().strip() or None
            meta = raw.get("public_metadata") if isinstance(raw.get("public_metadata"), dict) else {}
            role_key, user_type = _role_for_clerk_user(email, meta)
            first = raw.get("first_name") or ""
            last = raw.get("last_name") or ""
            name = f"{first} {last}".strip() or (email.split("@")[0] if email else "User")

            pc_id = str(uuid.uuid4())
            pc = PorterchainUser(
                id=pc_id,
                clerk_user_id=clerk_id,
                email=email,
                phone=ClerkClient.primary_phone(raw),
                role=role_key if user_type == "admin" else user_type,
                status=AccountStatus.ACTIVE.value,
                onboarding_status="complete" if user_type == "admin" else "not_started",
                default_workspace="admin" if user_type == "admin" else user_type,
                profile={
                    "provisioned": True,
                    "user_type": user_type,
                    "name": name,
                    "public_metadata": meta,
                },
                last_synced_at=now,
            )
            db.add(pc)
            db.flush()  # porterchain_users must exist before profile FKs

            db.add(
                IdentityLink(
                    id=str(uuid.uuid4()),
                    clerk_user_id=clerk_id,
                    provider="clerk",
                    issuer="https://relaxing-warthog-11.clerk.accounts.dev",
                    subject=clerk_id,
                    is_current=True,
                    email=email,
                    user_type=user_type,
                    platform_user_id=pc_id,
                    last_synced_at=now,
                )
            )

            scope_type = "platform" if user_type == "admin" else "self"
            scope_id = ""
            profile_id = None

            if user_type == "admin":
                admin = AdminUser(
                    id=str(uuid.uuid4()),
                    clerk_user_id=clerk_id,
                    email=email or f"admin-{clerk_id[-8:]}@example.com",
                    name=name,
                    role="super_admin" if role_key == AssignableRole.SUPER_ADMIN.value else "admin",
                    is_active=True,
                )
                if hasattr(admin, "porterchain_user_id"):
                    admin.porterchain_user_id = pc_id
                db.add(admin)
                profile_id = admin.id
                scope_type = "platform"
            elif user_type == "merchant":
                if default_merchant is None:
                    default_merchant = Merchant(
                        id=str(uuid.uuid4()),
                        company_name="Platform Imported Merchants",
                        status="active",
                        email=email or "merchants@example.com",
                    )
                    db.add(default_merchant)
                    db.flush()
                mu = MerchantUser(
                    id=str(uuid.uuid4()),
                    merchant_id=default_merchant.id,
                    clerk_user_id=clerk_id,
                    email=email or f"merchant-{clerk_id[-8:]}@example.com",
                    role="owner",
                    is_active=True,
                )
                if hasattr(mu, "porterchain_user_id"):
                    mu.porterchain_user_id = pc_id
                db.add(mu)
                profile_id = mu.id
                scope_type = "organization"
                scope_id = default_merchant.id
            elif user_type == "driver":
                dr = Driver(
                    id=str(uuid.uuid4()),
                    clerk_user_id=clerk_id,
                    email=email or f"driver-{clerk_id[-8:]}@example.com",
                    full_name=name,
                    status="active",
                )
                if hasattr(dr, "porterchain_user_id"):
                    dr.porterchain_user_id = pc_id
                db.add(dr)
                profile_id = dr.id
            else:
                cu = Customer(
                    id=str(uuid.uuid4()),
                    clerk_user_id=clerk_id,
                    email=email,
                )
                if hasattr(cu, "porterchain_user_id"):
                    cu.porterchain_user_id = pc_id
                db.add(cu)
                profile_id = cu.id

            # Persona profiles + SpiceDB tuples carry access — never Postgres ACL rows.
            assignable = role_key
            if user_type == "merchant":
                assignable = AssignableRole.MERCHANT_OWNER.value
            elif user_type == "admin" and assignable not in {r.value for r in AssignableRole}:
                assignable = AssignableRole.SUPER_ADMIN.value

            summary["created"] += 1
            summary["by_type"][user_type] = summary["by_type"].get(user_type, 0) + 1
            summary.setdefault("users", []).append(
                {
                    "clerk_user_id": clerk_id,
                    "email": _mask(email),
                    "user_type": user_type,
                    "role": assignable,
                    "profile_id": profile_id,
                }
            )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--confirm",
        default="",
        help="Must be WIPE_LOCAL to truncate all public tables and re-import",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path.home() / "porterchain-migration-exports" / "platform-user-reset.json",
    )
    args = parser.parse_args()

    settings = Settings()
    if not is_local_env(settings.app_env):
        raise SystemExit(f"refusing: APP_ENV={settings.app_env!r} is not local")
    if not settings.clerk_unified_mode:
        raise SystemExit("refusing: CLERK_UNIFIED_MODE must be true")

    platform = resolve_platform_clerk_config(settings)
    if not platform or not platform.secret_key:
        raise SystemExit("Platform Clerk secret missing")
    host = platform.jwks_url.split("/")[2]
    if "porterchain.com" in host and not host.endswith(".clerk.accounts.dev"):
        raise SystemExit(f"refusing live JWKS host: {host}")

    client = clerk_client_for_kind(settings, "admin")
    users = _list_platform_users(client)
    preview = []
    for u in users:
        email = _primary_email(u)
        meta = u.get("public_metadata") if isinstance(u.get("public_metadata"), dict) else {}
        role, utype = _role_for_clerk_user(email, meta)
        preview.append({"email": _mask(email), "user_type": utype, "role": role, "clerk_id_suffix": str(u.get("id", ""))[-8:]})

    report = {
        "app_env": settings.app_env,
        "platform_host": host,
        "clerk_user_count": len(users),
        "preview": preview,
        "dry_run": bool(args.dry_run),
    }

    if args.dry_run or args.confirm != "WIPE_LOCAL":
        report["status"] = "dry_run" if args.dry_run else "need_confirm_WIPE_LOCAL"
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({k: report[k] for k in ("status", "app_env", "platform_host", "clerk_user_count")}, indent=2))
        print("by_type_plan=", {t: sum(1 for p in preview if p["user_type"] == t) for t in ("admin", "merchant", "driver", "customer")})
        print(f"report={args.out}")
        if args.confirm != "WIPE_LOCAL" and not args.dry_run:
            print("Re-run with --confirm WIPE_LOCAL to truncate local DB and import.")
        return

    wiped = _wipe_all_public_tables()
    summary = _import_users(users)
    report.update({"status": "wiped_and_imported", "tables_truncated": len(wiped), "import": summary})
    # Don't dump full wiped table list into stdout; keep in file
    report["tables"] = wiped
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "wiped_and_imported",
                "tables_truncated": len(wiped),
                "clerk_user_count": len(users),
                "created": summary["created"],
                "by_type": summary["by_type"],
            },
            indent=2,
        )
    )
    print(f"report={args.out}")


if __name__ == "__main__":
    main()
