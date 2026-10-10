"""Retire Fleetbase: move its ids into legacy_external_refs, drop the columns, rename old event types.

PorterChain no longer uses Fleetbase. Historical ids are kept (one row per non-null
value) so nothing is lost; the domain tables stop carrying vendor columns.

Revision ID: fx0retirefleet5e6f
Revises: ds0stopevents3c4d
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "fx0retirefleet5e6f"
down_revision = "ds0stopevents3c4d"
branch_labels = None
depends_on = None

# (table, column, type, indexed)
COLUMNS = [
    ("orders", "fleetbase_order_id", sa.String(128), True),
    ("packages", "fleetbase_entity_id", sa.String(128), True),
    ("packages", "fleetbase_proof_id", sa.String(128), False),
    ("stops", "fleetbase_stop_id", sa.String(128), False),
    ("drivers", "fleetbase_driver_id", sa.String(128), True),
    ("vehicles", "fleetbase_vehicle_id", sa.String(128), False),
    ("admin_users", "fleetbase_user_uuid", sa.String(128), True),
    ("identity_links", "fleetbase_user_uuid", sa.String(128), True),
    ("identity_links", "fleetbase_roles", sa.JSON(), False),
    ("identity_links", "fleetbase_permissions", sa.JSON(), False),
]
EVENT_TABLES = ("domain_events", "order_events")


def upgrade() -> None:
    op.create_table(
        "legacy_external_refs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("entity", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("field", sa.String(64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_legacy_external_refs_entity", "legacy_external_refs", ["entity", "entity_id"])
    for table, col, _type, indexed in COLUMNS:
        op.execute(
            f"INSERT INTO legacy_external_refs (source, entity, entity_id, field, value) "
            f"SELECT 'fleetbase', '{table}', CAST(id AS VARCHAR), '{col}', CAST({col} AS TEXT) "
            f"FROM {table} WHERE {col} IS NOT NULL"
        )
        if indexed:
            op.drop_index(f"ix_{table}_{col}", table_name=table)
        op.drop_column(table, col)
    for t in EVENT_TABLES:
        op.execute(f"UPDATE {t} SET event_type = 'legacy_dispatch.' || substr(event_type, 11) WHERE event_type LIKE 'fleetbase.%'")


def downgrade() -> None:
    for t in EVENT_TABLES:
        op.execute(f"UPDATE {t} SET event_type = 'fleetbase.' || substr(event_type, 17) WHERE event_type LIKE 'legacy_dispatch.%'")
    for table, col, typ, indexed in COLUMNS:
        op.add_column(table, sa.Column(col, typ, nullable=True))
        if indexed:
            op.create_index(f"ix_{table}_{col}", table, [col])
        cast = "JSON" if isinstance(typ, sa.JSON) else "VARCHAR"
        op.execute(
            f"UPDATE {table} SET {col} = CAST(r.value AS {cast}) FROM legacy_external_refs r "
            f"WHERE r.source = 'fleetbase' AND r.entity = '{table}' AND r.field = '{col}' "
            f"AND r.entity_id = CAST({table}.id AS VARCHAR)"
        )
    op.drop_index("ix_legacy_external_refs_entity", table_name="legacy_external_refs")
    op.drop_table("legacy_external_refs")
