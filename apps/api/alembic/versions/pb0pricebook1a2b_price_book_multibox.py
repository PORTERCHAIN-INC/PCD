"""Price book, driver pay plan, pricing version; multi-box item columns on packages.

Seeds three `system_config` rows only when missing (an existing row is never
overwritten): `pricing_book` (every price-changing switch OFF, so no quote
moves), `driver_pay_plan` ($27/h, 4 h wave block) and `pricing_version`
(version 1). Adds `item_key`, `item_label`, `box_index`, `box_count` to
`packages` — all nullable, so existing packages read as single-box items.

Revision ID: pb0pricebook1a2b
Revises: sx0shoptok1a2b
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "pb0pricebook1a2b"
down_revision = "sx0shoptok1a2b"
branch_labels = None
depends_on = None

_SEEDED_KEYS = ("pricing_book", "driver_pay_plan", "pricing_version")


def _rows() -> dict[str, dict]:
    # Imported here so the seed always matches the engine's validated defaults.
    from porterchain_pricing.driver_pay import default_driver_pay_plan
    from porterchain_pricing.price_book import default_price_book

    return {
        "pricing_book": default_price_book(),
        "driver_pay_plan": default_driver_pay_plan(),
        "pricing_version": {"version": 1, "source": "migration:pb0pricebook1a2b"},
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
    op.add_column("packages", sa.Column("item_key", sa.String(length=64), nullable=True))
    op.add_column("packages", sa.Column("item_label", sa.String(length=120), nullable=True))
    op.add_column("packages", sa.Column("box_index", sa.Integer(), nullable=True))
    op.add_column("packages", sa.Column("box_count", sa.Integer(), nullable=True))
    op.create_index("ix_packages_item_key", "packages", ["item_key"])
    for key, value in _rows().items():
        _insert_missing(key, value)


def downgrade() -> None:
    op.get_bind().execute(
        sa.text("DELETE FROM system_config WHERE key IN :keys").bindparams(sa.bindparam("keys", expanding=True)),
        {"keys": list(_SEEDED_KEYS)},
    )
    op.drop_index("ix_packages_item_key", table_name="packages")
    op.drop_column("packages", "box_count")
    op.drop_column("packages", "box_index")
    op.drop_column("packages", "item_label")
    op.drop_column("packages", "item_key")
