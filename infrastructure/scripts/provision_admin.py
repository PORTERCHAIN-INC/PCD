#!/usr/bin/env python3
"""Provision a Porterchain admin via Staff IdP (no Clerk).

Admin Clerk login is retired. This mints an enrollment / magic-link token
(Redis) and emails an activate link when SMTP/Mailpit is available.

Usage:
  cd apps/api && source .venv/bin/activate
  PYTHONPATH=src python ../../infrastructure/scripts/provision_admin.py \\
    you@porterchain.com --role super_admin --name "Your Name"

Local: open the printed activate URL (or Mailpit http://localhost:8025).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[2] / "apps" / "api"
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(API_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "shared" / "python"))
sys.path.insert(0, str(REPO_ROOT / "services" / "python"))
sys.path.insert(0, str(REPO_ROOT / "services" / "event-bus"))
sys.path.insert(0, str(REPO_ROOT / "services" / "pricing-engine"))
sys.path.insert(0, str(REPO_ROOT / "services" / "driver-platform"))

from porterchain_api.admin_engine.rbac import AdminContext  # noqa: E402
from porterchain_api.admin_engine.staff_idp_service import StaffIdpService  # noqa: E402
from porterchain_api.admin_models import AdminUser  # noqa: E402
from porterchain_api.auth.invitation_service import INVITABLE_ADMIN_ROLES  # noqa: E402
from porterchain_api.config import get_settings  # noqa: E402
from porterchain_api.db import SessionLocal, init_db  # noqa: E402
from porterchain_api.domain.admin_states import AdminRole  # noqa: E402


def load_env() -> None:
    env_path = API_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _actor_context(db) -> AdminContext:
    """Use an existing super_admin as audit actor, else a bootstrap system actor."""
    actor = (
        db.query(AdminUser)
        .filter(AdminUser.is_active.is_(True), AdminUser.role == AdminRole.SUPER_ADMIN.value)
        .order_by(AdminUser.created_at.asc())
        .first()
    )
    if actor is None:
        actor = (
            db.query(AdminUser)
            .filter(AdminUser.is_active.is_(True))
            .order_by(AdminUser.created_at.asc())
            .first()
        )
    if actor is None:
        # First staff ever — enroll will create the row; audit ctx uses a ephemeral shell.
        actor = AdminUser(
            clerk_user_id="pending:bootstrap@porterchain.local",
            email="bootstrap@porterchain.local",
            name="Bootstrap",
            role=AdminRole.SUPER_ADMIN.value,
            is_active=True,
        )
        db.add(actor)
        db.flush()
    role = AdminRole(actor.role) if actor.role in {r.value for r in AdminRole} else AdminRole.SUPER_ADMIN
    return AdminContext(user=actor, role=role)


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision Porterchain staff via Staff IdP")
    parser.add_argument("email", type=str)
    parser.add_argument("--role", default=AdminRole.SUPER_ADMIN.value)
    parser.add_argument("--name", default="Admin User")
    parser.add_argument(
        "--reissue",
        action="store_true",
        help="Reissue enrollment for an existing staff email instead of enroll",
    )
    args = parser.parse_args()

    email = args.email.lower().strip()
    role = args.role.strip().lower()
    if role not in INVITABLE_ADMIN_ROLES:
        raise SystemExit(
            f"invalid role {role!r}; allowed: {', '.join(sorted(INVITABLE_ADMIN_ROLES))}"
        )

    load_env()
    settings = get_settings()
    init_db()
    db = SessionLocal()
    svc = StaffIdpService()

    try:
        ctx = _actor_context(db)
        if args.reissue:
            existing = db.query(AdminUser).filter(AdminUser.email == email).first()
            if not existing:
                raise SystemExit(f"no staff user for {email} — run without --reissue first")
            result = svc.reissue(db, ctx, settings, existing.id)
        else:
            result = svc.enroll(
                db,
                ctx,
                settings,
                email=email,
                role=role,
                name=args.name.strip() or None,
            )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    finally:
        db.close()

    portal = (os.environ.get("ADMIN_PORTAL_URL") or "http://localhost:3002").rstrip("/")
    token = result.get("enrollment_token")
    activate_url = f"{portal}/activate-staff?token={token}" if token else None

    print(
        json.dumps(
            {
                "email": result.get("email"),
                "role": result.get("role"),
                "admin_user_id": result.get("admin_user_id"),
                "email_sent": result.get("email_sent"),
                "expires_at": result.get("expires_at"),
                "activate_url": activate_url,
                "sign_in": f"{portal}/sign-in",
                "mailpit": "http://localhost:8025",
                "next_step": (
                    "Open activate_url (or the Mailpit email), then use /sign-in for later logins."
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
