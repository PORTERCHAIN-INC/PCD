#!/usr/bin/env python3
"""Bootstrap real-world admin Staff IdP roles + driver Clerk invites (local/prod ops).

Creates/updates staff for each ops role with enrollment magic links, ensures seed
drivers are APPROVED, and sends Clerk driver invitations when CLERK_DRIVER_* is set.

Usage:
  cd apps/api && source .venv/bin/activate
  PYTHONPATH=src python scripts/bootstrap_auth_login.py
  PYTHONPATH=src python scripts/bootstrap_auth_login.py --disable-admin-bypass
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parent.parent
sys.path.insert(0, str(API_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "shared" / "python"))
sys.path.insert(0, str(REPO_ROOT / "services" / "python"))
sys.path.insert(0, str(REPO_ROOT / "services" / "event-bus"))
sys.path.insert(0, str(REPO_ROOT / "services" / "pricing-engine"))
sys.path.insert(0, str(REPO_ROOT / "services" / "driver-platform"))

from porterchain_api.admin_engine.rbac import AdminContext  # noqa: E402
from porterchain_api.admin_engine.staff_idp_service import StaffIdpService, ensure_staff_identity  # noqa: E402
from porterchain_api.admin_models import AdminUser, Driver  # noqa: E402
from porterchain_api.auth.clerk_registry import is_clerk_secret_configured  # noqa: E402
from porterchain_api.auth.invitation_service import InvitationService  # noqa: E402
from porterchain_api.config import get_settings  # noqa: E402
from porterchain_api.db import SessionLocal, init_db  # noqa: E402
from porterchain_api.domain.admin_states import AdminRole, DriverStatus  # noqa: E402

# Real-world role matrix — one demo mailbox per role (local + staging).
STAFF_ROSTER: list[tuple[str, str, str]] = [
    ("super_admin@porterchain.com", AdminRole.SUPER_ADMIN.value, "Super Admin"),
    ("admin@porterchain.com", AdminRole.ADMIN.value, "Platform Admin"),
    ("dispatcher@porterchain.com", AdminRole.DISPATCHER.value, "Dispatcher"),
    ("support@porterchain.com", AdminRole.SUPPORT.value, "Support Agent"),
    ("support.lead@porterchain.com", AdminRole.SUPPORT_LEAD.value, "Support Lead"),
    ("finance@porterchain.com", AdminRole.FINANCE.value, "Finance"),
    ("fleet@porterchain.com", AdminRole.FLEET_MANAGER.value, "Fleet Manager"),
    ("sales@porterchain.com", AdminRole.SALES.value, "Sales"),
    ("sales.manager@porterchain.com", AdminRole.SALES_MANAGER.value, "Sales Manager"),
    ("compliance@porterchain.com", AdminRole.COMPLIANCE.value, "Compliance"),
    ("developer@porterchain.com", AdminRole.DEVELOPER.value, "Developer"),
    ("marketing@porterchain.com", AdminRole.MARKETING.value, "Marketing"),
    ("readonly@porterchain.com", AdminRole.READ_ONLY.value, "Read Only"),
]

SEED_DRIVERS = (
    "marco@porterchain.com",
    "aisha@porterchain.com",
    "liam@porterchain.com",
)


def load_env() -> None:
    env_path = API_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _actor(db) -> AdminContext:
    user = (
        db.query(AdminUser)
        .filter(AdminUser.is_active.is_(True), AdminUser.role == AdminRole.SUPER_ADMIN.value)
        .order_by(AdminUser.created_at.asc())
        .first()
    )
    if user is None:
        user = AdminUser(
            clerk_user_id="pending:bootstrap@porterchain.local",
            email="bootstrap@porterchain.local",
            name="Bootstrap",
            role=AdminRole.SUPER_ADMIN.value,
            is_active=True,
        )
        db.add(user)
        db.flush()
        ensure_staff_identity(db, user)
        db.refresh(user)
    return AdminContext(user=user, role=AdminRole.SUPER_ADMIN)


def _set_admin_bypass(enabled: bool) -> None:
    path = REPO_ROOT / "apps" / "admin" / ".env.local"
    if not path.exists():
        return
    text = path.read_text()
    value = "true" if enabled else "false"
    if re.search(r"^NEXT_PUBLIC_CLERK_DEV_BYPASS=.*$", text, re.M):
        text = re.sub(
            r"^NEXT_PUBLIC_CLERK_DEV_BYPASS=.*$",
            f"NEXT_PUBLIC_CLERK_DEV_BYPASS={value}",
            text,
            count=1,
            flags=re.M,
        )
    else:
        text = text.rstrip() + f"\nNEXT_PUBLIC_CLERK_DEV_BYPASS={value}\n"
    # Keep APP_ENV local so Mailpit + token echo stay available.
    if not re.search(r"^NEXT_PUBLIC_APP_ENV=.*$", text, re.M):
        text = text.rstrip() + "\nNEXT_PUBLIC_APP_ENV=local\n"
    path.write_text(text)


def _set_driver_dev_login(enabled: bool) -> None:
    path = REPO_ROOT / "apps" / "driver-portal" / ".env.local"
    if not path.exists():
        return
    text = path.read_text()
    value = "true" if enabled else "false"
    if re.search(r"^NEXT_PUBLIC_DRIVER_DEV_LOGIN=.*$", text, re.M):
        text = re.sub(
            r"^NEXT_PUBLIC_DRIVER_DEV_LOGIN=.*$",
            f"NEXT_PUBLIC_DRIVER_DEV_LOGIN={value}",
            text,
            count=1,
            flags=re.M,
        )
    else:
        text = text.rstrip() + f"\nNEXT_PUBLIC_DRIVER_DEV_LOGIN={value}\n"
    if not re.search(r"^NEXT_PUBLIC_APP_ENV=.*$", text, re.M):
        text = text.rstrip() + "\nNEXT_PUBLIC_APP_ENV=local\n"
    path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap admin Staff IdP + driver login")
    parser.add_argument(
        "--disable-admin-bypass",
        action="store_true",
        help="Set apps/admin NEXT_PUBLIC_CLERK_DEV_BYPASS=false (force Staff IdP UI)",
    )
    parser.add_argument(
        "--enable-driver-dev-login",
        action="store_true",
        default=True,
        help="Enable local email-picker driver login (default true)",
    )
    parser.add_argument("--skip-drivers", action="store_true")
    args = parser.parse_args()

    load_env()
    settings = get_settings()
    init_db()
    db = SessionLocal()
    svc = StaffIdpService()
    portal = (os.environ.get("ADMIN_PORTAL_URL") or "http://localhost:3002").rstrip("/")
    driver_portal = (os.environ.get("DRIVER_PORTAL_URL") or "http://localhost:3003").rstrip("/")

    staff_rows: list[dict] = []
    driver_rows: list[dict] = []

    try:
        ctx = _actor(db)
        for email, role, name in STAFF_ROSTER:
            try:
                result = svc.enroll(db, ctx, settings, email=email, role=role, name=name)
            except ValueError as exc:
                staff_rows.append({"email": email, "role": role, "error": str(exc)})
                continue
            token = result.get("enrollment_token")
            staff_rows.append(
                {
                    "email": email,
                    "role": role,
                    "admin_user_id": result.get("admin_user_id"),
                    "email_sent": result.get("email_sent"),
                    "activate_url": f"{portal}/activate-staff?token={token}" if token else None,
                }
            )

        # Ensure founder + seed-admin have staff:{id} identity even without re-enroll.
        for email in ("porterchaininc@gmail.com", "seed-admin@porterchain.com"):
            user = db.query(AdminUser).filter(AdminUser.email == email).first()
            if user:
                ensure_staff_identity(db, user)
                db.commit()

        if not args.skip_drivers:
            for email in SEED_DRIVERS:
                driver = db.query(Driver).filter(Driver.email == email).first()
                if not driver:
                    driver_rows.append({"email": email, "status": "missing_seed_run_pnpm_db_seed"})
                    continue
                driver.status = DriverStatus.APPROVED.value
                db.commit()
                row: dict = {
                    "email": email,
                    "driver_id": driver.id,
                    "status": driver.status,
                    "clerk_user_id": driver.clerk_user_id,
                    "invite": None,
                }
                if is_clerk_secret_configured(settings, "driver"):
                    try:
                        invitation = InvitationService().invite_driver(db, ctx, settings, driver)
                        db.refresh(driver)
                        row["invite"] = invitation.status
                        row["clerk_user_id"] = driver.clerk_user_id
                    except Exception as exc:  # noqa: BLE001
                        row["invite"] = f"error:{exc}"
                else:
                    row["invite"] = "skipped_no_clerk_driver_secret"
                driver_rows.append(row)
    finally:
        db.close()

    if args.disable_admin_bypass:
        _set_admin_bypass(False)
    if args.enable_driver_dev_login:
        _set_driver_dev_login(True)

    report = {
        "admin_portal": f"{portal}/sign-in",
        "activate_base": f"{portal}/activate-staff?token=…",
        "mailpit": "http://localhost:8025",
        "driver_portal": f"{driver_portal}/login",
        "admin_bypass_disabled": bool(args.disable_admin_bypass),
        "driver_dev_login_enabled": bool(args.enable_driver_dev_login),
        "staff": staff_rows,
        "drivers": driver_rows,
        "how_to_admin": [
            "1. Ensure Redis + Mailpit are up (pnpm docker:up).",
            "2. Open an activate_url below (or Mailpit email).",
            "3. Later logins: /sign-in → enter email → magic link / passkey.",
            "4. With --disable-admin-bypass, dashboard requires real staff session.",
        ],
        "how_to_driver": [
            "1. Clerk path: accept invite email → http://localhost:3003/login.",
            "2. Local path: email picker on /login when NEXT_PUBLIC_DRIVER_DEV_LOGIN=true.",
            "3. Seed drivers: marco@ / aisha@ / liam@porterchain.com.",
        ],
    }

    out_dir = REPO_ROOT / ".logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "auth-bootstrap.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
