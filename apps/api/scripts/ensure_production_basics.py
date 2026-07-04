#!/usr/bin/env python3
"""Idempotent production bootstrap: retail pricing tariffs required for quotes."""

from __future__ import annotations

from porterchain_api.admin_models import PricingTariff
from porterchain_api.db import SessionLocal


def ensure_pricing_tariffs(db) -> int:
    if db.query(PricingTariff).filter(PricingTariff.is_active.is_(True)).first():
        return 0
    db.add_all(
        [
            PricingTariff(
                name="GTA Standard Cargo Van",
                tariff_type="retail",
                vehicle_class="cargo_van",
                zone="gta",
                base_cents=1200,
                per_km_cents=95,
                fuel_surcharge_percent=5.0,
                is_active=True,
                config={"seed": "production_basics"},
            ),
            PricingTariff(
                name="GTA Standard Sprinter",
                tariff_type="retail",
                vehicle_class="sprinter",
                zone="gta",
                base_cents=1800,
                per_km_cents=110,
                fuel_surcharge_percent=5.0,
                is_active=True,
                config={"seed": "production_basics"},
            ),
        ]
    )
    db.commit()
    return 2


def ensure_production_basics() -> None:
    with SessionLocal() as db:
        added = ensure_pricing_tariffs(db)
        if added:
            print(f"ensure_production_basics: seeded {added} pricing tariff(s)")


if __name__ == "__main__":
    ensure_production_basics()
