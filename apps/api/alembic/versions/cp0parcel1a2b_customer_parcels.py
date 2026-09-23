"""Customer parcel quotes and the sedan/suv, 16 ft, 20 ft catalog.

Revision ID: cp0parcel1a2b
Revises: c1d2e3f4a5b6
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "cp0parcel1a2b"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None

_CLASS_MAP = {
    "sedan": "sedan_suv",
    "suv": "sedan_suv",
    "sedanSuv": "sedan_suv",
    "sedan_suv": "sedan_suv",
    "cargoVan": "cargo_van",
    "box16": "box_16",
    "box_truck": "box_16",
    "boxTruck": "box_16",
    "box20": "box_20",
    "highRoof": "sprinter_van",
    "high_roof": "sprinter_van",
}


def _map_class(value: str | None) -> str | None:
    if not value:
        return value
    return _CLASS_MAP.get(value, value)


def upgrade() -> None:
    op.add_column("quotes", sa.Column("parcels", sa.JSON(), nullable=True))
    bind = op.get_bind()
    for table, column in (
        ("vehicles", "vehicle_class"),
        ("quotes", "vehicle_class"),
    ):
        rows = bind.execute(sa.text(f"SELECT id, {column} FROM {table}")).fetchall()
        for row_id, current in rows:
            mapped = _map_class(current)
            if mapped and mapped != current:
                bind.execute(
                    sa.text(f"UPDATE {table} SET {column} = :mapped WHERE id = :id"),
                    {"mapped": mapped, "id": row_id},
                )

    config = bind.execute(
        sa.text("SELECT value FROM system_config WHERE key = 'vehicle_types'")
    ).fetchone()
    if config and config[0]:
        raw = config[0]
        catalog = raw if isinstance(raw, list) else json.loads(raw)
        changed = False
        seen: set[str] = set()
        kept = []
        for row in catalog:
            if not isinstance(row, dict):
                kept.append(row)
                continue
            mapped = _map_class(str(row.get("id") or ""))
            if mapped in seen:
                changed = True
                continue
            if mapped != row.get("id"):
                row = dict(row)
                row["id"] = mapped
                if mapped == "sedan_suv":
                    row["label"] = "Sedan / SUV"
                    row["allowed_presets"] = ["small", "medium", "large", "other"]
                if mapped == "box_16":
                    row["label"] = row.get("label") or "16 ft box"
                changed = True
            row.setdefault("whole_vehicle_enabled", mapped != "sprinter_van")
            seen.add(mapped or "")
            kept.append(row)
        if "box_20" not in seen:
            kept.append(
                {
                    "id": "box_20",
                    "label": "20 ft box",
                    "capacity_kg": 4500,
                    "max_length_cm": 600,
                    "max_width_cm": 240,
                    "max_height_cm": 240,
                    "booking_enabled": True,
                    "retail_enabled": True,
                    "merchant_enabled": True,
                    "whole_vehicle_enabled": True,
                    "allowed_presets": ["small", "medium", "large", "extra_large", "skid", "furniture", "other"],
                    "sort_order": 6,
                }
            )
            changed = True
        if changed:
            bind.execute(
                sa.text("UPDATE system_config SET value = :value WHERE key = 'vehicle_types'"),
                {"value": json.dumps(kept)},
            )


def downgrade() -> None:
    op.drop_column("quotes", "parcels")
