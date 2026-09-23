#!/usr/bin/env python3
"""
Apply Kaylulu commercial schedule + FSA tier tags (data only — no hardcode in engine).

Usage (from repo root, API venv + DATABASE_URL):

  cd apps/api && PYTHONPATH=src python scripts/apply_kaylulu_schedule.py

Optional: MERCHANT_ID=… (defaults to prod Kaylulu id).

Maps van flats to tiers: $30→T1, $45→T2, $60→T3 (PDF bands).
"""

from __future__ import annotations

import os
import sys

from sqlalchemy.orm import Session

# Ensure API package is importable when run as a script.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from porterchain_api.db import SessionLocal  # noqa: E402
from porterchain_api.admin_models import PricingFsaRate  # noqa: E402
from porterchain_api.merchant_models import Merchant  # noqa: E402

DEFAULT_MERCHANT_ID = "8a1704f3-eaa1-46bb-a848-0ccb5d38f870"

KAYLULU_SCHEDULE = {
    "fuel_surcharge_percent": 0,
    "fsa_miss": "refuse",
    "origin_pickup_cents": 4000,
    "origin_pickup_vehicle_classes": ["cargo_van"],
    "route_minimums_cents": {"T1": 12000, "T2": 20000, "T3": 25000},
    "compact": {
        "enabled": True,
        "vehicle_classes": ["sedan_suv", "sedan", "suv"],
        "max_packed_inches": [10, 10],
        "parcels_per_stop": 3,
        "stop_rates_cents": [
            {"max_stops": 4, "cents": 1000},
            {"max_stops": None, "cents": 600},
        ],
        "route_minimum_cents": 5000,
    },
    "size_match": "any",
}

# PDF van flats → tier
FLAT_TO_TIER = {
    3000: "T1",
    4500: "T2",
    6000: "T3",
}


def apply(db: Session, merchant_id: str) -> dict:
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise SystemExit(f"merchant_not_found: {merchant_id}")

    cfg = dict(merchant.pricing_config or {})
    cfg["schedule"] = dict(KAYLULU_SCHEDULE)
    merchant.pricing_config = cfg
    merchant.pricing_model = "fsa"

    tagged = 0
    rows = (
        db.query(PricingFsaRate)
        .filter(
            PricingFsaRate.merchant_id == merchant_id,
            PricingFsaRate.is_active.is_(True),
        )
        .all()
    )
    for row in rows:
        tier = FLAT_TO_TIER.get(int(row.flat_cents))
        if not tier:
            continue
        # Only tag cargo_van / blank vehicle (compact aliases keep their own flats).
        vc = (row.vehicle_class or "").lower()
        if vc and vc not in ("cargo_van", "cargovan", "van"):
            continue
        config = dict(row.config or {})
        if config.get("tier") == tier:
            continue
        config["tier"] = tier
        row.config = config
        tagged += 1

    db.commit()
    return {
        "merchant_id": merchant_id,
        "company": merchant.company_name,
        "schedule": True,
        "fsa_tiers_tagged": tagged,
        "fsa_rows_seen": len(rows),
    }


def main() -> None:
    merchant_id = os.environ.get("MERCHANT_ID") or DEFAULT_MERCHANT_ID
    db = SessionLocal()
    try:
        result = apply(db, merchant_id)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
