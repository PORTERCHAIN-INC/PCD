#!/usr/bin/env python3
"""
Apply Kaylulu commercial schedule + A3 handling tiers + FSA tier tags (data only).

Usage (from repo root, API venv + DATABASE_URL):

  cd apps/api && PYTHONPATH=src python scripts/apply_kaylulu_schedule.py

Optional: MERCHANT_ID=… (defaults to prod Kaylulu id).

Maps van flats to tiers: $30→T1, $45→T2, $60→T3 (PDF bands).
"""

from __future__ import annotations

import os
import sys

from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from porterchain_api.db import SessionLocal  # noqa: E402
from porterchain_api.admin_models import PricingFsaRate  # noqa: E402
from porterchain_api.merchant_engine.kaylulu_template import (  # noqa: E402
    DEFAULT_KAYLULU_MERCHANT_ID,
    FLAT_TO_TIER,
    kaylulu_pricing_config,
)
from porterchain_api.merchant_models import Merchant  # noqa: E402


def apply(db: Session, merchant_id: str) -> dict:
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant:
        raise SystemExit(f"merchant_not_found: {merchant_id}")

    merchant.pricing_config = kaylulu_pricing_config(existing=merchant.pricing_config)
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
        "size_tiers": len((merchant.pricing_config or {}).get("size_tiers") or []),
        "fsa_tiers_tagged": tagged,
        "fsa_rows_seen": len(rows),
    }


def main() -> None:
    merchant_id = os.environ.get("MERCHANT_ID") or DEFAULT_KAYLULU_MERCHANT_ID
    db = SessionLocal()
    try:
        result = apply(db, merchant_id)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
