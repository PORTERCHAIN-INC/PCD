"""Seed dev merchant + driver accounts for local portal testing.

Idempotent — safe to re-run.

Usage:
    cd apps/api && PYTHONPATH=src python scripts/seed_dev_portal_users.py
"""

from __future__ import annotations

from datetime import UTC, datetime

from porterchain_api.admin_models import Driver, Vehicle
from porterchain_api.db import SessionLocal, init_db
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.user_models import PorterchainUser as _PorterchainUser  # noqa: F401

DEV_ORG = "dev_merchant_org"
DEV_CLERK_USER = "dev_clerk_user"

DRIVERS = [
    {
        "email": "marco@porterchain.com",
        "full_name": "Marco Rossi",
        "phone": "+1 416-555-0101",
        "vehicle_class": "cargo_van",
        "plate": "CARGO1",
        "make_model": "Ford Transit",
        "wallet_cents": 125_50,
    },
    {
        "email": "aisha@porterchain.com",
        "full_name": "Aisha Khan",
        "phone": "+1 416-555-0102",
        "vehicle_class": "cargo_van",
        "plate": "VAN42",
        "make_model": "Mercedes Sprinter",
        "wallet_cents": 89_25,
    },
    {
        "email": "liam@porterchain.com",
        "full_name": "Liam Tremblay",
        "phone": "+1 416-555-0103",
        "vehicle_class": "box_truck",
        "plate": "BOX99",
        "make_model": "Isuzu NPR",
        "wallet_cents": 210_00,
    },
]


def _ensure_dev_merchant(db) -> Merchant:
    merchant = db.query(Merchant).filter(Merchant.clerk_org_id == DEV_ORG).first()
    if merchant:
        merchant.status = MerchantStatus.ACTIVE.value
        merchant.company_name = merchant.company_name or "Dev Merchant Co."
        merchant.email = merchant.email or "merchant@porterchain.com"
        db.commit()
        db.refresh(merchant)
        return merchant

    merchant = Merchant(
        clerk_org_id=DEV_ORG,
        status=MerchantStatus.ACTIVE.value,
        company_name="Dev Merchant Co.",
        email="merchant@porterchain.com",
        payment_terms="NET_30",
        activated_at=datetime.now(UTC),
    )
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant


def _ensure_merchant_user(db, merchant: Merchant) -> MerchantUser:
    user = db.query(MerchantUser).filter(MerchantUser.clerk_user_id == DEV_CLERK_USER).first()
    if user:
        # Keep local Bearer-dev claims (admin@porterchain.com) aligned.
        user.email = "admin@porterchain.com"
        user.merchant_id = merchant.id
        user.role = "merchant_owner"
        user.is_active = True
        db.commit()
        db.refresh(user)
        return user
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=DEV_CLERK_USER,
        email="admin@porterchain.com",
        role="merchant_owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _ensure_driver(db, spec: dict) -> Driver:
    driver = db.query(Driver).filter(Driver.email == spec["email"]).first()
    if not driver:
        driver = Driver(
            email=spec["email"],
            full_name=spec["full_name"],
            phone=spec["phone"],
            status=DriverStatus.APPROVED.value,
            license_verified=True,
            insurance_verified=True,
            vehicle_verified=True,
            background_check_status="cleared",
            rating=4.8,
            wallet_balance_cents=spec["wallet_cents"],
            performance={"score": 92, "on_time_pct": 96},
        )
        db.add(driver)
        db.commit()
        db.refresh(driver)
    else:
        driver.status = DriverStatus.APPROVED.value
        driver.wallet_balance_cents = spec["wallet_cents"]
        db.commit()
        db.refresh(driver)

    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.driver_id == driver.id, Vehicle.plate_number == spec["plate"])
        .first()
    )
    if not vehicle:
        vehicle = Vehicle(
            driver_id=driver.id,
            vehicle_class=spec["vehicle_class"],
            plate_number=spec["plate"],
            make_model=spec["make_model"],
            capacity_kg=1200.0 if spec["vehicle_class"] == "cargo_van" else 4000.0,
            is_active=True,
        )
        db.add(vehicle)
        db.commit()

    return driver


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        merchant = _ensure_dev_merchant(db)
        user = _ensure_merchant_user(db, merchant)
        drivers = [_ensure_driver(db, spec) for spec in DRIVERS]

        print("=== Dev portal accounts ready ===")
        print()
        print("MERCHANT PORTAL (http://localhost:3001)")
        print("  Dev mode: open /dashboard directly — no password")
        print("  Clerk mode: sign in at /sign-in, org auto: dev_merchant_org")
        print(f"  Merchant ID: {merchant.id}")
        print(f"  Org ID:      {DEV_ORG}")
        print(f"  User email:  {user.email}")
        print()
        print("DRIVER PORTAL (http://localhost:3003/login)")
        print("  Dev login: email only (no password) — set CLERK_DEV_BYPASS=true on API")
        for spec, driver in zip(DRIVERS, drivers, strict=True):
            print(f"  • {spec['email']}  (driver_id: {driver.id})")
        print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
