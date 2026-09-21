"""Seed 5 approved drivers — online with GTA location pings.

Idempotent on driver email. Safe to re-run.

Usage:
    cd apps/api && PYTHONPATH=src uv run python scripts/seed_online_drivers.py
"""

from __future__ import annotations

import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT / "src"))
sys.path.insert(0, str(API_ROOT.parent.parent / "services" / "driver-platform"))

from porterchain_api.admin_models import Driver, Vehicle
from porterchain_api.db import SessionLocal, init_db
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_driver import DriverPlatform

MARKER = "online-drivers-batch-v1"

DRIVERS = [
    {
        "email": "jordan.patel@porterchain.com",
        "full_name": "Jordan Patel",
        "phone": "+1 416-555-0201",
        "vehicle_class": "cargo_van",
        "plate": "GTA-201",
        "make_model": "Ram ProMaster",
        "lat": 43.6532,
        "lng": -79.3832,
        "area": "Downtown Toronto",
    },
    {
        "email": "sam.nguyen@porterchain.com",
        "full_name": "Sam Nguyen",
        "phone": "+1 416-555-0202",
        "vehicle_class": "cargo_van",
        "plate": "GTA-202",
        "make_model": "Ford Transit",
        "lat": 43.7615,
        "lng": -79.4111,
        "area": "North York",
    },
    {
        "email": "elena.vasquez@porterchain.com",
        "full_name": "Elena Vasquez",
        "phone": "+1 416-555-0203",
        "vehicle_class": "cargo_van",
        "plate": "GTA-203",
        "make_model": "Mercedes Sprinter",
        "lat": 43.7764,
        "lng": -79.2315,
        "area": "Scarborough",
    },
    {
        "email": "devon.clark@porterchain.com",
        "full_name": "Devon Clark",
        "phone": "+1 416-555-0204",
        "vehicle_class": "box_truck",
        "plate": "GTA-204",
        "make_model": "Isuzu NPR",
        "lat": 43.6205,
        "lng": -79.5132,
        "area": "Etobicoke",
    },
    {
        "email": "priya.sharma@porterchain.com",
        "full_name": "Priya Sharma",
        "phone": "+1 416-555-0205",
        "vehicle_class": "cargo_van",
        "plate": "GTA-205",
        "make_model": "Chevrolet Express",
        "lat": 43.5890,
        "lng": -79.6441,
        "area": "Mississauga",
    },
]


def _ensure_driver(db, spec: dict) -> Driver:
    email = spec["email"].strip().lower()
    driver = db.query(Driver).filter(Driver.email == email).first()
    if not driver:
        driver = Driver(
            email=email,
            full_name=spec["full_name"],
            phone=spec["phone"],
            status=DriverStatus.APPROVED.value,
            license_verified=True,
            insurance_verified=True,
            vehicle_verified=True,
            background_check_status="cleared",
            rating=4.7,
            wallet_balance_cents=0,
            performance={"score": 90, "on_time_pct": 94, "seed": MARKER},
        )
        db.add(driver)
        db.flush()
    else:
        driver.status = DriverStatus.APPROVED.value
        driver.license_verified = True
        driver.insurance_verified = True
        driver.vehicle_verified = True
        driver.background_check_status = "cleared"
        perf = dict(driver.performance or {})
        perf["seed"] = MARKER
        driver.performance = perf
        if not driver.documents:
            driver.documents = {
                "files": [
                    {
                        "doc_type": "driver_license",
                        "label": "Driver license",
                        "file_url": "https://storage.porterchain.local/seed/license.pdf",
                    },
                    {
                        "doc_type": "insurance",
                        "label": "Insurance certificate",
                        "file_url": "https://storage.porterchain.local/seed/insurance.pdf",
                    },
                    {
                        "doc_type": "vehicle_registration",
                        "label": "Vehicle registration",
                        "file_url": "https://storage.porterchain.local/seed/registration.pdf",
                    },
                ],
                "abstract": {
                    "verified": True,
                    "status": "complete",
                    "license_class": "G",
                    "demerits": 0,
                },
            }
        else:
            docs = dict(driver.documents or {})
            abstract = dict(docs.get("abstract") or {})
            abstract.update({"verified": True, "status": "complete"})
            driver.documents = {**docs, "abstract": abstract}

    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.driver_id == driver.id, Vehicle.plate_number == spec["plate"])
        .first()
    )
    if not vehicle:
        db.add(
            Vehicle(
                driver_id=driver.id,
                vehicle_class=spec["vehicle_class"],
                plate_number=spec["plate"],
                make_model=spec["make_model"],
                capacity_kg=1200.0 if spec["vehicle_class"] == "cargo_van" else 4000.0,
                is_active=True,
            )
        )
    db.commit()
    db.refresh(driver)
    return driver


def _go_online_with_location(db, driver: Driver, spec: dict) -> None:
    from porterchain_driver.shift import PRETRIP_ITEMS

    platform = DriverPlatform()
    pretrip = {key: True for key, _label in PRETRIP_ITEMS}
    try:
        platform.shift.start_shift(db, driver, pretrip=pretrip)
    except PermissionError:
        platform.availability.set_online(db, driver, online=True)
    platform.location.record_ping(
        db,
        driver,
        lat=spec["lat"],
        lng=spec["lng"],
        accuracy_m=6.0,
        heading=45.0,
        speed_mps=0.0,
    )
    db.commit()
    db.refresh(driver)


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        print(f"=== Seeding 5 online drivers ({MARKER}) ===\n")
        for spec in DRIVERS:
            driver = _ensure_driver(db, spec)
            _go_online_with_location(db, driver, spec)
            print(
                f"  ✓ {driver.full_name} | {driver.email}\n"
                f"    online={driver.is_online} | availability={driver.availability}\n"
                f"    location={spec['area']} ({spec['lat']}, {spec['lng']})\n"
                f"    driver_id={driver.id}\n"
            )

        online = db.query(Driver).filter(Driver.is_online.is_(True)).count()
        total = db.query(Driver).count()
        print(f"Done — {online} drivers online / {total} total in system.")
        print("View on Admin → Live Map or Operations → Dispatch Queue (driver dropdown).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
