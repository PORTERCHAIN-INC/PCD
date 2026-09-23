"""Save the customer distance card, Ontario HST, and merchant fuel.

Revision ID: tx0hstfuel1a2b
Revises: cp0parcel1a2b
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "tx0hstfuel1a2b"
down_revision = "cp0parcel1a2b"
branch_labels = None
depends_on = None

_CUSTOMER_CARD = {
    "strict_vehicles": True,
    "base_km_limit": 20.0,
    "downtown_fee_cad": 25.0,
    "upper_zone_fee_cad": 15.0,
    "weight_threshold_kg": 50,
    "weight_cents_per_kg": 0,
    "volume_threshold_cm3": 100_000,
    "cents_per_10k_cm3": 0,
    "declared_value_threshold_cents": 0,
    "declared_value_rate": 0,
    "vehicles": {
        "sedan_suv": {"base_price": 45.0, "extra_km_rate": 1.25, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
        "cargo_van": {"base_price": 65.0, "extra_km_rate": 2.0, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
        "pickup": {"base_price": 60.0, "extra_km_rate": 1.9, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
        "sprinter_van": {"base_price": 75.0, "extra_km_rate": 2.5, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
        "box_16": {"base_price": 125.0, "extra_km_rate": 3.5, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
        "box_20": {"base_price": 125.0, "extra_km_rate": 3.5, "extra_pick_fee": 20.0, "extra_drop_fee": 15.0},
    },
    "parcel_presets": [
        {"id": "small", "label": "Small", "length_in": 10, "width_in": 10, "height_in": 8, "weight_lb": 10, "manual": False},
        {"id": "medium", "label": "Medium", "length_in": 16, "width_in": 12, "height_in": 12, "weight_lb": 25, "manual": False},
        {"id": "large", "label": "Large", "length_in": 24, "width_in": 18, "height_in": 18, "weight_lb": 40, "manual": False},
        {"id": "extra_large", "label": "Extra large", "length_in": 36, "width_in": 24, "height_in": 24, "weight_lb": 70, "manual": False},
        {"id": "skid", "label": "Skid", "length_in": 48, "width_in": 40, "height_in": 48, "weight_lb": 100, "manual": False},
        {"id": "furniture", "label": "Furniture", "length_in": 80, "width_in": 36, "height_in": 30, "weight_lb": 80, "manual": False},
        {"id": "other", "label": "Other", "length_in": None, "width_in": None, "height_in": None, "weight_lb": None, "manual": True},
    ],
}

_ROWS = {
    "pricing_customer_distance": _CUSTOMER_CARD,
    "pricing_tax": {"hst_percent": 13.0, "tax_included": False, "exempt_merchant_ids": []},
    "pricing_fuel": {
        "surcharge_percent": 5.0,
        "base_fuel_price_cents": 145,
        "current_fuel_price_cents": 158,
    },
}


def _insert_missing(key: str, value: dict) -> None:
    bind = op.get_bind()
    exists = bind.execute(sa.text("SELECT 1 FROM system_config WHERE key = :key"), {"key": key}).fetchone()
    if exists:
        return
    bind.execute(
        sa.text("INSERT INTO system_config (key, value) VALUES (:key, CAST(:value AS json))"),
        {"key": key, "value": json.dumps(value)},
    )


def upgrade() -> None:
    for key, value in _ROWS.items():
        _insert_missing(key, value)


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM system_config WHERE key IN "
            "('pricing_customer_distance', 'pricing_tax', 'pricing_fuel')"
        )
    )
