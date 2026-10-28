"""Drop the dead cash-on-delivery and Stripe Connect columns.

No code has read or written these since COD was removed (see
docs/migrations/COD_COLUMNS_DEPRECATED.md); merchants pay by Interac only.

Real-data safety: before dropping, every non-default value is archived into
``legacy_external_refs`` (source='dm4_cod_columns', entity=table, entity_id=row id,
field=column). The counts are printed, and an *open* COD collection
(``cod_status`` in pending_collection / link_issued) is printed per order so finance
can settle it by hand. Downgrade re-adds the columns (same types/defaults, the
``ix_orders_cod_status`` index) and restores every archived value.

Revision ID: dm4nocod0004
Revises: dm3custody0003
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "dm4nocod0004"
down_revision = "dm3custody0003"
branch_labels = None
depends_on = None

SOURCE = "dm4_cod_columns"
# (table, column, sql type for restore, "is set" predicate)
COLUMNS = (
    ("orders", "cod_amount_cents", "integer", "cod_amount_cents IS NOT NULL"),
    ("orders", "cod_status", "varchar(32)", "cod_status IS NOT NULL"),
    ("orders", "cod_stripe_session_id", "varchar(255)", "cod_stripe_session_id IS NOT NULL"),
    ("merchants", "cod_enabled", "boolean", "cod_enabled"),
    ("merchants", "stripe_connect_account_id", "varchar(255)", "stripe_connect_account_id IS NOT NULL"),
)


def upgrade() -> None:
    bind = op.get_bind()
    open_cod = bind.execute(
        sa.text(
            "SELECT id, order_number, cod_amount_cents, cod_status FROM orders "
            "WHERE cod_status IN ('pending_collection', 'link_issued')"
        )
    ).all()
    for row in open_cod:
        print(f"[dm4nocod0004] OPEN COD to settle by hand: order {row.order_number} ({row.id}) "
              f"{row.cod_amount_cents} cents, {row.cod_status}")
    for table, column, _type, is_set in COLUMNS:
        n = bind.execute(
            sa.text(
                "INSERT INTO legacy_external_refs (source, entity, entity_id, field, value) "
                f"SELECT :s, :t, id, :c, {column}::text FROM {table} WHERE {is_set}"
            ),
            {"s": SOURCE, "t": table, "c": column},
        ).rowcount
        print(f"[dm4nocod0004] archived {n} {table}.{column} values")
    op.drop_index("ix_orders_cod_status", table_name="orders")
    for table, column, _type, _ in COLUMNS:
        op.drop_column(table, column)


def downgrade() -> None:
    bind = op.get_bind()
    for table, column, sql_type, _ in COLUMNS:
        default = " NOT NULL DEFAULT false" if column == "cod_enabled" else ""
        op.execute(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}{default}")
        bind.execute(
            sa.text(
                f"UPDATE {table} t SET {column} = r.value::{sql_type} FROM legacy_external_refs r "
                "WHERE r.source = :s AND r.entity = :t AND r.field = :c AND r.entity_id = t.id"
            ),
            {"s": SOURCE, "t": table, "c": column},
        )
    op.create_index("ix_orders_cod_status", "orders", ["cod_status"])
    bind.execute(sa.text("DELETE FROM legacy_external_refs WHERE source = :s"), {"s": SOURCE})
