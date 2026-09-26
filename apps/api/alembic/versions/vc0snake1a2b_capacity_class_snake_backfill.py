"""Backfill leftover camel / bare-sprinter capacity classes to SoT1 snake ids.

Revision ID: vc0snake1a2b
Revises: pg0gtacatalog1a2b

cp0parcel remapped vehicles + quotes + vehicle_types catalog. This pass covers
compliance denorm, merchant preferences, Shopify shop defaults, FSA rates, and
any stragglers still on camel or bare ``sprinter``.
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "vc0snake1a2b"
down_revision = "pg0gtacatalog1a2b"
branch_labels = None
depends_on = None

_CLASS_MAP = {
    "sedan": "sedan_suv",
    "suv": "sedan_suv",
    "sedanSuv": "sedan_suv",
    "sedan_suv": "sedan_suv",
    "cargoVan": "cargo_van",
    "cargo_van": "cargo_van",
    "pickup": "pickup",
    "highRoof": "sprinter_van",
    "high_roof": "sprinter_van",
    "sprinter": "sprinter_van",
    "sprinterVan": "sprinter_van",
    "sprinter_van": "sprinter_van",
    "box16": "box_16",
    "box_truck": "box_16",
    "boxTruck": "box_16",
    "box_16": "box_16",
    "box20": "box_20",
    "box_20": "box_20",
}


def _map_class(value: str | None) -> str | None:
    if not value:
        return value
    raw = str(value).strip()
    if not raw:
        return value
    if raw in _CLASS_MAP:
        return _CLASS_MAP[raw]
    key = raw.lower().replace("-", "_").replace(" ", "_")
    compact = key.replace("_", "")
    return _CLASS_MAP.get(key) or _CLASS_MAP.get(compact) or raw


def _rewrite_column(bind, table: str, column: str) -> None:
    rows = bind.execute(sa.text(f"SELECT id, {column} FROM {table}")).fetchall()
    for row_id, current in rows:
        mapped = _map_class(current)
        if mapped and mapped != current:
            bind.execute(
                sa.text(f"UPDATE {table} SET {column} = :mapped WHERE id = :id"),
                {"mapped": mapped, "id": row_id},
            )


def upgrade() -> None:
    bind = op.get_bind()

    for table, column in (
        ("vehicles", "vehicle_class"),
        ("quotes", "vehicle_class"),
        ("shopify_shops", "default_vehicle_class"),
        ("pricing_fsa_rates", "vehicle_class"),
    ):
        _rewrite_column(bind, table, column)

    # Order compliance denorm — SoT3b
    order_rows = bind.execute(
        sa.text("SELECT id, compliance_metadata FROM orders WHERE compliance_metadata IS NOT NULL")
    ).fetchall()
    for row_id, meta in order_rows:
        if meta is None:
            continue
        data = meta if isinstance(meta, dict) else json.loads(meta)
        if not isinstance(data, dict):
            continue
        current = data.get("vehicle_class")
        mapped = _map_class(current if isinstance(current, str) else None)
        if mapped and mapped != current:
            data = dict(data)
            data["vehicle_class"] = mapped
            bind.execute(
                sa.text(
                    "UPDATE orders SET compliance_metadata = CAST(:meta AS json) WHERE id = :id"
                ),
                {"meta": json.dumps(data), "id": row_id},
            )

    # Merchant preferred_vehicles JSON list
    merchant_rows = bind.execute(
        sa.text("SELECT id, preferred_vehicles FROM merchants WHERE preferred_vehicles IS NOT NULL")
    ).fetchall()
    for row_id, preferred in merchant_rows:
        if not isinstance(preferred, list):
            try:
                preferred = json.loads(preferred) if preferred else []
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        if not isinstance(preferred, list):
            continue
        cleaned: list[str] = []
        changed = False
        for raw in preferred:
            mapped = _map_class(str(raw) if raw is not None else None)
            if not mapped:
                changed = True
                continue
            if mapped != raw:
                changed = True
            if mapped not in cleaned:
                cleaned.append(mapped)
        if changed or cleaned != preferred:
            bind.execute(
                sa.text(
                    "UPDATE merchants SET preferred_vehicles = CAST(:value AS json) WHERE id = :id"
                ),
                {"value": json.dumps(cleaned), "id": row_id},
            )


def downgrade() -> None:
    # One-way data normalize — no restore of camel dialects.
    pass
