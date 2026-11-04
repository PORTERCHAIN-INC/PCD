"""Reconcile model/migration drift so ``alembic check`` is clean.

Revision ID: dm1driftfix0001
Revises: bf0focusauth1a2b

* ``route_center_templates``: the admin wholesale route-template API uses it but
  ``a8b9c0d1e2f3`` dropped it. Recreate it (merchant_id -> merchants ON DELETE SET NULL).
* ``blog_focus_oct2026_backup``: its rows are moved into ``legacy_external_refs``
  (source='blog_focus_oct2026_backup') and the table is dropped. Downgrade rebuilds the
  table from those rows, so ``bf0focusauth1a2b``'s downgrade still restores exactly.
* 18 timestamp/config columns the models declare NOT NULL were nullable in the DB:
  NULLs are backfilled (created_at/updated_at -> now(), pricing_fsa_rates.config -> '{}')
  and the columns become NOT NULL. The backfill count is printed per column.
* Redundant duplicate indexes are dropped (``ix_shopify_shops_shop_domain`` duplicates the
  unique index; ``ix_stripe_webhook_events_stripe_event_id`` duplicates the unique key).
* ``ix_shopify_dsr_*`` indexes are renamed to the ORM's default names.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "dm1driftfix0001"
down_revision = "bf0focusauth1a2b"
branch_labels = None
depends_on = None

NOT_NULL_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("booking_attachment_events", "created_at", "now()"),
    ("booking_attachments", "created_at", "now()"),
    ("driver_payout_runs", "created_at", "now()"),
    ("finance_reminder_drafts", "created_at", "now()"),
    ("interac_transfers", "created_at", "now()"),
    ("invoice_number_sequences", "updated_at", "now()"),
    ("merchant_alerts", "created_at", "now()"),
    ("merchant_documents", "created_at", "now()"),
    ("merchant_merges", "created_at", "now()"),
    ("pricing_fsa_rates", "config", "'{}'::json"),
    ("pricing_fsa_rates", "created_at", "now()"),
    ("pricing_fsa_rates", "updated_at", "now()"),
    ("shopify_ingress_dlq", "created_at", "now()"),
    ("shopify_ingress_dlq", "updated_at", "now()"),
    ("shopify_shops", "created_at", "now()"),
    ("shopify_shops", "updated_at", "now()"),
    ("staff_webauthn_credentials", "created_at", "now()"),
    ("stripe_payouts", "created_at", "now()"),
)
DSR_INDEX_RENAMES = tuple(
    (f"ix_shopify_dsr_{c}", f"ix_shopify_data_subject_requests_{c}")
    for c in ("merchant_id", "shop_id", "status", "topic")
)
BACKUP_TABLE = "blog_focus_oct2026_backup"


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "route_center_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("template_type", sa.String(32), nullable=False),
        sa.Column("merchant_id", sa.String(36), sa.ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("zone", sa.String(64), nullable=True),
        sa.Column("schedule", sa.JSON(), nullable=False),
        sa.Column("stops", sa.JSON(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_route_center_templates_merchant_id", "route_center_templates", ["merchant_id"])
    op.create_index("ix_route_center_templates_template_type", "route_center_templates", ["template_type"])

    if sa.inspect(bind).has_table(BACKUP_TABLE):
        moved = bind.execute(
            sa.text(
                "INSERT INTO legacy_external_refs (source, entity, entity_id, field, value) "
                f"SELECT '{BACKUP_TABLE}', kind, ref, 'payload', payload FROM {BACKUP_TABLE}"
            )
        ).rowcount
        print(f"[dm1driftfix0001] archived {moved} {BACKUP_TABLE} rows into legacy_external_refs")
        op.drop_table(BACKUP_TABLE)

    for table, column, fill in NOT_NULL_COLUMNS:
        n = bind.execute(sa.text(f"UPDATE {table} SET {column} = {fill} WHERE {column} IS NULL")).rowcount
        if n:
            print(f"[dm1driftfix0001] backfilled {n} NULL {table}.{column}")
        op.alter_column(table, column, nullable=False)

    op.drop_index("ix_shopify_shops_shop_domain", table_name="shopify_shops")
    op.drop_index("ix_stripe_webhook_events_stripe_event_id", table_name="stripe_webhook_events")
    for old, new in DSR_INDEX_RENAMES:
        op.execute(f"ALTER INDEX {old} RENAME TO {new}")


def downgrade() -> None:
    bind = op.get_bind()
    for old, new in DSR_INDEX_RENAMES:
        op.execute(f"ALTER INDEX {new} RENAME TO {old}")
    op.create_index("ix_stripe_webhook_events_stripe_event_id", "stripe_webhook_events", ["stripe_event_id"])
    op.create_index("ix_shopify_shops_shop_domain", "shopify_shops", ["shop_domain"])

    for table, column, _fill in NOT_NULL_COLUMNS:
        op.alter_column(table, column, nullable=True)

    op.create_table(
        BACKUP_TABLE,
        sa.Column("kind", sa.String(length=32), primary_key=True),
        sa.Column("ref", sa.String(length=64), primary_key=True),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    bind.execute(
        sa.text(
            f"INSERT INTO {BACKUP_TABLE} (kind, ref, payload) "
            "SELECT entity, entity_id, value FROM legacy_external_refs WHERE source = :s"
        ),
        {"s": BACKUP_TABLE},
    )
    bind.execute(sa.text("DELETE FROM legacy_external_refs WHERE source = :s"), {"s": BACKUP_TABLE})

    op.drop_index("ix_route_center_templates_template_type", table_name="route_center_templates")
    op.drop_index("ix_route_center_templates_merchant_id", table_name="route_center_templates")
    op.drop_table("route_center_templates")
