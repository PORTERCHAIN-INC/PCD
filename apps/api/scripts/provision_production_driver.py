"""Provision an approved driver in Porterchain + send Clerk driver invitation.

Intended for one-off production ops via:

    docker exec -w /app/apps/api \\
      -e PYTHONPATH=/app/apps/api/src:/app/apps/api \\
      pcd-api python scripts/provision_production_driver.py \\
        --email priya.sharma@porterchain.com \\
        --full-name "Priya Sharma"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))
sys.path.insert(0, str(API_ROOT.parent.parent / "services" / "driver-platform"))

from porterchain_api.admin_engine.driver_service import AdminDriverService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.clerk_registry import is_clerk_secret_configured
from porterchain_api.auth.invitation_service import InvitationService
from porterchain_api.config import get_settings
from porterchain_api.db import SessionLocal, init_db
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.schemas_admin import DriverCreateRequest, DriverVehicleCreateInput


def _bootstrap_admin_ctx(db) -> AdminContext | None:
    user = (
        db.query(AdminUser)
        .filter(AdminUser.is_active.is_(True))
        .order_by(AdminUser.created_at.asc())
        .first()
    )
    if not user:
        return None
    role = AdminRole(user.role) if user.role in {r.value for r in AdminRole} else AdminRole.ADMIN
    return AdminContext(user=user, role=role)


def _send_clerk_invite(db, settings, driver: Driver) -> None:
    if not is_clerk_secret_configured(settings, "driver"):
        print("Clerk driver secret not configured — skipped invite")
        return
    invitation = InvitationService().invite_driver(db, None, settings, driver)
    db.refresh(driver)
    print(f"Clerk invitation sent: status={invitation.status}")
    print(f"clerk_user_id: {driver.clerk_user_id or '(pending)'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision production driver + Clerk invite")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--phone", default="+1 416-555-0205")
    parser.add_argument("--vehicle-class", default="cargo_van")
    parser.add_argument("--plate", default="GTA-205")
    parser.add_argument("--make-model", default="Chevrolet Express")
    parser.add_argument("--resend-invite", action="store_true")
    args = parser.parse_args()

    email = args.email.strip().lower()
    settings = get_settings()
    init_db()
    db = SessionLocal()
    svc = AdminDriverService()

    try:
        existing = db.query(Driver).filter(Driver.email == email).first()
        if existing:
            print(f"Driver already exists: {existing.id} ({existing.email}) status={existing.status}")
            if args.resend_invite or not existing.clerk_user_id:
                _send_clerk_invite(db, settings, existing)
            return

        ctx = _bootstrap_admin_ctx(db)
        if not ctx:
            raise SystemExit("No active admin user found — cannot create a new driver without audit context")

        driver = svc.create_driver(
            db,
            ctx,
            DriverCreateRequest(
                full_name=args.full_name.strip(),
                email=email,
                phone=args.phone.strip(),
                vehicle=DriverVehicleCreateInput(
                    vehicle_class=args.vehicle_class,
                    plate_number=args.plate,
                    make_model=args.make_model,
                    capacity_kg=1200.0,
                ),
                auto_approve=True,
            ),
            settings,
        )
        print("=== Driver provisioned ===")
        print(f"driver_id: {driver.id}")
        print(f"email:     {driver.email}")
        print(f"status:    {driver.status}")
        print(f"clerk_id:  {driver.clerk_user_id or '(pending invite)'}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
