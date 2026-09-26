"""Align pricing_gta_rate keys with the retail vehicle catalog.

Revision ID: pg0gtacatalog1a2b
Revises: au0clerknull1a2b, bg0schedauth1a2b

Live still stored sedan/suv/box_truck after cp0parcel renamed vehicle_types to
sedan_suv/box_16/box_20. Settings validate then warned. Collapse legacy keys.
"""

from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pg0gtacatalog1a2b"
down_revision: Union[str, tuple[str, ...], None] = ("au0clerknull1a2b", "bg0schedauth1a2b")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LEGACY = {
    "sedan": "sedan_suv",
    "suv": "sedan_suv",
    "box_truck": "box_16",
    "small_van": "cargo_van",
    "large_van": "sprinter_van",
}


def _collapse_vehicles(raw: dict) -> dict:
    out: dict = {}
    claimed: set[str] = set()
    for key, rates in raw.items():
        if not isinstance(rates, dict):
            continue
        target = _LEGACY.get(str(key), str(key))
        if str(key) != target and target in claimed:
            continue
        if target not in out:
            out[target] = dict(rates)
        if str(key) != target:
            claimed.add(target)
    if "box_16" in out and "box_20" not in out:
        out["box_20"] = dict(out["box_16"])
    return out


def upgrade() -> None:
    bind = op.get_bind()
    row = bind.execute(
        sa.text("SELECT value FROM system_config WHERE key = 'pricing_gta_rate'")
    ).fetchone()
    if not row or row[0] is None:
        return
    raw = row[0]
    payload = raw if isinstance(raw, dict) else json.loads(raw)
    if not isinstance(payload, dict):
        return
    vehicles = payload.get("vehicles")
    if not isinstance(vehicles, dict):
        return
    collapsed = _collapse_vehicles(vehicles)
    if collapsed == vehicles:
        return
    payload = dict(payload)
    payload["vehicles"] = collapsed
    bind.execute(
        sa.text(
            "UPDATE system_config SET value = CAST(:value AS json) WHERE key = 'pricing_gta_rate'"
        ),
        {"value": json.dumps(payload)},
    )

    booking = bind.execute(
        sa.text("SELECT value FROM system_config WHERE key = 'settings_booking'")
    ).fetchone()
    if booking and booking[0] is not None:
        braw = booking[0]
        bpayload = braw if isinstance(braw, dict) else json.loads(braw)
        if isinstance(bpayload, dict):
            default = bpayload.get("default_vehicle_class")
            mapped = _LEGACY.get(str(default), default) if default else default
            if mapped and mapped != default:
                bpayload = dict(bpayload)
                bpayload["default_vehicle_class"] = mapped
                bind.execute(
                    sa.text(
                        "UPDATE system_config SET value = CAST(:value AS json) "
                        "WHERE key = 'settings_booking'"
                    ),
                    {"value": json.dumps(bpayload)},
                )


def downgrade() -> None:
    # One-way: catalog ids are the SSOT; do not re-split sedan_suv / box_16.
    pass
