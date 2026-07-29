#!/usr/bin/env python3
"""Import / re-invite merchant, customer, driver users into PorterChain Platform Clerk.

Local-only: uses CLERK_UNIFIED_MODE Platform triad from apps/api/.env.
Does not call production live keys. Does not delete Clerk apps.

Strategy:
  1. Load emails from local Postgres profiles
  2. If email already exists on Platform → link clerk_user_id + refresh metadata
  3. Else create_user (import, skip_password_requirement) with public_metadata
  4. For merchant/driver also create Clerk invitation (re-invite) when create succeeded
     or user already existed (notify / accept path)

Never prints secret values or full email addresses — domain + counts only.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

# Ensure imports when run as scripts/…
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parents[1] / "shared" / "python"))

from porterchain_api.admin_models import Driver  # noqa: E402
from porterchain_api.auth.clerk_client import ClerkClient  # noqa: E402
from porterchain_api.auth.clerk_registry import (  # noqa: E402
    clerk_client_for_kind,
    resolve_platform_clerk_config,
)
from porterchain_api.auth.invitation_service import pending_clerk_id  # noqa: E402
from porterchain_api.config import Settings  # noqa: E402
from porterchain_api.db import SessionLocal  # noqa: E402
from porterchain_api.invitation_models import UserInvitation  # noqa: E402
from porterchain_api.merchant_models import MerchantUser  # noqa: E402
from porterchain_api.models import Customer  # noqa: E402
from porterchain_api import user_models as _user_models  # noqa: E402,F401
from porterchain_api import identity_models as _identity_models  # noqa: E402,F401
from porterchain_api import unified_identity_models as _unified_identity_models  # noqa: E402,F401

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("reinvite_platform")


@dataclass
class RowResult:
    user_type: str
    platform_user_id: str
    domain: str
    action: str
    clerk_user_id: str | None = None
    error: str | None = None
    remapped_email: str | None = None


def _domain(email: str) -> str:
    return email.split("@")[-1].lower() if "@" in email else "?"


def _mask(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}" if domain else "***"


SYNTHETIC_DOMAINS = frozenset(
    {
        "svc.test",
        "idor.test",
        "test.local",
        "example.com",
        "test.porterchain.com",
        "validation.porterchain.com",
    }
)

# Clerk rejects some seed domains (e.g. svc.test). Map to a valid mailbox for Platform import.
INVALID_CLERK_DOMAINS = frozenset({"svc.test", "idor.test", "test.local", "porterchain.test"})


def _should_send_invite(email: str, send_invites: bool) -> bool:
    if not send_invites:
        return False
    # Never email synthetic / remapped domains
    if _domain(email) in SYNTHETIC_DOMAINS or _domain(email) == "example.com":
        return False
    return True


def _clerk_email(email: str) -> tuple[str, bool]:
    """Return (email_for_clerk, remapped?). Remap invalid seed domains to example.com."""
    normalized = email.lower().strip()
    if "@" not in normalized:
        return normalized, False
    local, domain = normalized.rsplit("@", 1)
    if domain in INVALID_CLERK_DOMAINS:
        safe_domain = domain.replace(".", "-")
        return f"{local}.{safe_domain}@example.com", True
    return normalized, False


def _ensure_platform(settings: Settings) -> ClerkClient:
    if not settings.clerk_unified_mode:
        raise SystemExit("CLERK_UNIFIED_MODE must be true — refuse multi-app invite")
    platform = resolve_platform_clerk_config(settings)
    if not platform or not platform.secret_key or not platform.jwks_url:
        raise SystemExit("Platform triad missing")
    host = platform.jwks_url.split("/")[2]
    if "porterchain.com" in host and not host.endswith(".clerk.accounts.dev"):
        # live custom domain — require explicit --allow-live
        raise SystemExit(f"refusing live-looking JWKS host without --allow-live: {host}")
    logger.info("platform_jwks_host=%s", host)
    return clerk_client_for_kind(settings, "admin")


def _upsert_invitation(
    db: Session,
    *,
    email: str,
    user_type: str,
    role: str,
    clerk_user_id: str | None,
    clerk_invitation_id: str | None,
    platform_user_id: str,
    redirect_url: str,
) -> None:
    row = (
        db.query(UserInvitation)
        .filter(
            UserInvitation.email == email,
            UserInvitation.user_type == user_type,
            UserInvitation.status.in_(("pending", "sent", "accepted")),
        )
        .order_by(UserInvitation.created_at.desc())
        .first()
    )
    if row is None:
        row = UserInvitation(
            email=email,
            user_type=user_type,
            role=role,
            status="pending",
            platform_user_id=platform_user_id,
            redirect_url=redirect_url,
            invitation_metadata={"source": "reinvite_to_platform"},
        )
        db.add(row)
    row.role = role
    row.clerk_user_id = clerk_user_id or row.clerk_user_id
    row.clerk_invitation_id = clerk_invitation_id or row.clerk_invitation_id
    row.redirect_url = redirect_url
    row.platform_user_id = platform_user_id
    if clerk_user_id and row.status == "pending":
        row.status = "accepted"
        row.accepted_at = datetime.now(UTC)


def _import_one(
    client: ClerkClient,
    db: Session,
    settings: Settings,
    *,
    user_type: str,
    email: str,
    role: str,
    platform_user_id: str,
    redirect_url: str,
    metadata: dict,
    send_invite: bool,
    dry_run: bool,
) -> RowResult:
    original = email.lower().strip()
    normalized, remapped = _clerk_email(original)
    domain = _domain(original)
    base = RowResult(
        user_type=user_type,
        platform_user_id=platform_user_id,
        domain=domain,
        action="noop",
    )

    existing = client.find_user_by_email(normalized)
    if existing and existing.get("id"):
        clerk_id = str(existing["id"])
        if dry_run:
            base.action = "would_link_remapped" if remapped else "would_link"
            base.clerk_user_id = clerk_id
            return base
        try:
            client.update_user(clerk_id, public_metadata=metadata)
        except Exception as exc:  # noqa: BLE001
            logger.warning("metadata_update_failed %s %s", _mask(normalized), type(exc).__name__)
        invite_id = None
        if send_invite:
            try:
                inv = client.invite_user(
                    normalized, redirect_url=redirect_url, public_metadata=metadata
                )
                invite_id = inv.clerk_invitation_id
            except Exception as exc:  # noqa: BLE001
                logger.info("invite_skip %s %s", _mask(normalized), type(exc).__name__)
        _upsert_invitation(
            db,
            email=normalized,
            user_type=user_type,
            role=role,
            clerk_user_id=clerk_id,
            clerk_invitation_id=invite_id,
            platform_user_id=platform_user_id,
            redirect_url=redirect_url,
        )
        base.action = "linked_remapped" if remapped else "linked"
        base.clerk_user_id = clerk_id
        return base

    if dry_run:
        base.action = "would_create_remapped" if remapped else "would_create"
        return base

    try:
        created = client.create_user(
            normalized,
            skip_password_requirement=True,
            public_metadata=metadata,
        )
        clerk_id = str(created["id"])
    except Exception as exc:  # noqa: BLE001
        existing = client.find_user_by_email(normalized)
        if existing and existing.get("id"):
            clerk_id = str(existing["id"])
            base.action = "linked_after_race"
            base.clerk_user_id = clerk_id
        else:
            detail = type(exc).__name__
            if hasattr(exc, "response") and getattr(exc, "response", None) is not None:
                try:
                    detail = str(exc.response.status_code)
                except Exception:  # noqa: BLE001
                    pass
            base.action = "create_failed"
            base.error = detail
            logger.warning("create_failed %s %s", _mask(normalized), detail)
            return base
    else:
        base.action = "created_remapped" if remapped else "created"
        base.clerk_user_id = clerk_id

    invite_id = None
    if send_invite:
        try:
            inv = client.invite_user(
                normalized, redirect_url=redirect_url, public_metadata=metadata
            )
            invite_id = inv.clerk_invitation_id
            if inv.clerk_user_id:
                clerk_id = inv.clerk_user_id
                base.clerk_user_id = clerk_id
            base.action = f"{base.action}+invited"
        except Exception as exc:  # noqa: BLE001
            logger.info("invite_after_create_skip %s %s", _mask(normalized), type(exc).__name__)

    _upsert_invitation(
        db,
        email=normalized,
        user_type=user_type,
        role=role,
        clerk_user_id=clerk_id,
        clerk_invitation_id=invite_id,
        platform_user_id=platform_user_id,
        redirect_url=redirect_url,
    )
    if remapped:
        base.remapped_email = normalized
    return base


def run(*, dry_run: bool, send_invites: bool, sleep_s: float) -> dict:
    settings = Settings()
    client = _ensure_platform(settings)
    db = SessionLocal()
    results: list[RowResult] = []

    try:
        # Merchants
        merchants = db.query(MerchantUser).filter(MerchantUser.email.isnot(None)).all()
        for mu in merchants:
            email = (mu.email or "").strip()
            if not email:
                continue
            role = mu.role or "ops"
            meta = {
                "user_type": "merchant",
                "role": role,
                "porterchain_role": role,
                "merchant_id": mu.merchant_id,
                "invitation_only": True,
            }
            redirect = f"{settings.merchant_portal_url.rstrip('/')}/sign-in"
            r = _import_one(
                client,
                db,
                settings,
                user_type="merchant",
                email=email,
                role=role,
                platform_user_id=mu.id,
                redirect_url=redirect,
                metadata=meta,
                send_invite=_should_send_invite(email, send_invites),
                dry_run=dry_run,
            )
            if not dry_run and r.clerk_user_id:
                taken = (
                    db.query(MerchantUser.id)
                    .filter(
                        MerchantUser.clerk_user_id == r.clerk_user_id,
                        MerchantUser.id != mu.id,
                    )
                    .first()
                )
                if taken:
                    r.action = f"{r.action}+skip_dup_clerk_id"
                else:
                    mu.clerk_user_id = r.clerk_user_id
            if not dry_run and r.remapped_email:
                mu.email = r.remapped_email
            elif not dry_run and r.action.startswith("create") and not r.clerk_user_id:
                mu.clerk_user_id = pending_clerk_id(email)
            results.append(r)
            if not dry_run and len(results) % 20 == 0:
                try:
                    db.commit()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("batch_commit_failed %s — rollback", type(exc).__name__)
                    db.rollback()
            time.sleep(sleep_s)

        # Drivers
        drivers = db.query(Driver).filter(Driver.email.isnot(None)).all()
        for dr in drivers:
            email = (dr.email or "").strip()
            if not email:
                continue
            meta = {
                "user_type": "driver",
                "role": "driver",
                "porterchain_role": "driver",
                "driver_id": dr.id,
                "invitation_only": True,
            }
            redirect = f"{settings.driver_portal_url.rstrip('/')}/login"
            r = _import_one(
                client,
                db,
                settings,
                user_type="driver",
                email=email,
                role="driver",
                platform_user_id=dr.id,
                redirect_url=redirect,
                metadata=meta,
                send_invite=_should_send_invite(email, send_invites),
                dry_run=dry_run,
            )
            if not dry_run and r.clerk_user_id:
                taken = (
                    db.query(Driver.id)
                    .filter(Driver.clerk_user_id == r.clerk_user_id, Driver.id != dr.id)
                    .first()
                )
                if taken:
                    r.action = f"{r.action}+skip_dup_clerk_id"
                else:
                    dr.clerk_user_id = r.clerk_user_id
            if not dry_run and r.remapped_email:
                dr.email = r.remapped_email
            results.append(r)
            if not dry_run and len(results) % 20 == 0:
                try:
                    db.commit()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("batch_commit_failed %s — rollback", type(exc).__name__)
                    db.rollback()
            time.sleep(sleep_s)

        # Customers
        customers = db.query(Customer).filter(Customer.email.isnot(None)).all()
        for cu in customers:
            email = (cu.email or "").strip()
            if not email:
                continue
            meta = {
                "user_type": "customer",
                "role": "customer",
                "porterchain_role": "customer",
                "invitation_only": False,
            }
            redirect = f"{settings.customer_portal_url.rstrip('/')}/sign-in"
            r = _import_one(
                client,
                db,
                settings,
                user_type="customer",
                email=email,
                role="customer",
                platform_user_id=cu.id,
                redirect_url=redirect,
                metadata=meta,
                send_invite=_should_send_invite(email, send_invites),
                dry_run=dry_run,
            )
            if not dry_run and r.clerk_user_id:
                taken = (
                    db.query(Customer.id)
                    .filter(Customer.clerk_user_id == r.clerk_user_id, Customer.id != cu.id)
                    .first()
                )
                if taken:
                    r.action = f"{r.action}+skip_dup_clerk_id"
                else:
                    cu.clerk_user_id = r.clerk_user_id
            if not dry_run and r.remapped_email:
                cu.email = r.remapped_email
            results.append(r)
            if not dry_run and len(results) % 20 == 0:
                try:
                    db.commit()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("batch_commit_failed %s — rollback", type(exc).__name__)
                    db.rollback()
            time.sleep(sleep_s)

        if not dry_run:
            try:
                db.commit()
            except Exception as exc:  # noqa: BLE001
                logger.warning("final_commit_failed %s — rollback", type(exc).__name__)
                db.rollback()
                raise
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    by_action: Counter[str] = Counter()
    by_type: Counter[str] = Counter()
    errors = 0
    for r in results:
        by_action[r.action] += 1
        by_type[r.user_type] += 1
        if r.error:
            errors += 1

    summary = {
        "dry_run": dry_run,
        "send_invites": send_invites,
        "total": len(results),
        "by_type": dict(by_type),
        "by_action": dict(by_action),
        "errors": errors,
        "at": datetime.now(UTC).isoformat(),
        "rows": [asdict(r) for r in results],
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Plan only; no Clerk/DB writes")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create/link users on Platform and update local clerk_user_id",
    )
    parser.add_argument(
        "--send-invites",
        action="store_true",
        help="Also call Clerk invite_user (emails; may fail for synthetic domains)",
    )
    parser.add_argument("--sleep", type=float, default=0.15, help="Delay between Clerk calls")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path.home() / "porterchain-migration-exports" / "platform-reinvite-report.json",
        help="Write report outside the git repo",
    )
    args = parser.parse_args()
    if not args.dry_run and not args.apply:
        parser.error("pass --dry-run or --apply")

    dry_run = bool(args.dry_run) and not args.apply
    summary = run(dry_run=dry_run, send_invites=args.send_invites, sleep_s=args.sleep)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    # Console: counts only
    print(json.dumps({k: summary[k] for k in ("dry_run", "send_invites", "total", "by_type", "by_action", "errors", "at")}, indent=2))
    print(f"report={args.out}")


if __name__ == "__main__":
    main()
