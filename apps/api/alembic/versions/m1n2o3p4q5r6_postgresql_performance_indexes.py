"""PostgreSQL performance indexes and JSONB columns for CRM search."""

from alembic import op
import sqlalchemy as sa

revision = "m1n2o3p4q5r6"
down_revision = "l3m4n5o6p7q8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE crm_companies ALTER COLUMN address TYPE jsonb "
        "USING COALESCE(address, '{}')::jsonb"
    )
    op.execute(
        "ALTER TABLE crm_companies ALTER COLUMN custom_fields TYPE jsonb "
        "USING COALESCE(custom_fields, '{}')::jsonb"
    )
    op.execute(
        "ALTER TABLE crm_leads ALTER COLUMN address TYPE jsonb "
        "USING COALESCE(address, '{}')::jsonb"
    )
    op.execute(
        "ALTER TABLE crm_leads ALTER COLUMN custom_fields TYPE jsonb "
        "USING COALESCE(custom_fields, '{}')::jsonb"
    )

    op.create_index(
        "ix_crm_companies_address_gin",
        "crm_companies",
        ["address"],
        postgresql_using="gin",
        postgresql_ops={"address": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_crm_leads_address_gin",
        "crm_leads",
        ["address"],
        postgresql_using="gin",
        postgresql_ops={"address": "jsonb_path_ops"},
    )
    op.create_index(
        "ix_crm_leads_custom_fields_gin",
        "crm_leads",
        ["custom_fields"],
        postgresql_using="gin",
        postgresql_ops={"custom_fields": "jsonb_path_ops"},
    )

    op.create_index("ix_orders_state_created_at", "orders", ["state", sa.text("created_at DESC")])
    op.create_index("ix_orders_merchant_state", "orders", ["merchant_id", "state"])
    op.create_index("ix_domain_events_type_occurred", "domain_events", ["event_type", sa.text("occurred_at DESC")])
    op.create_index(
        "ix_fleetbase_sync_jobs_pending",
        "fleetbase_sync_jobs",
        ["status", "next_attempt_at"],
        postgresql_where=sa.text("status IN ('pending', 'retrying')"),
    )


def downgrade() -> None:
    op.drop_index("ix_fleetbase_sync_jobs_pending", table_name="fleetbase_sync_jobs")
    op.drop_index("ix_domain_events_type_occurred", table_name="domain_events")
    op.drop_index("ix_orders_merchant_state", table_name="orders")
    op.drop_index("ix_orders_state_created_at", table_name="orders")
    op.drop_index("ix_crm_leads_custom_fields_gin", table_name="crm_leads")
    op.drop_index("ix_crm_leads_address_gin", table_name="crm_leads")
    op.drop_index("ix_crm_companies_address_gin", table_name="crm_companies")

    op.execute("ALTER TABLE crm_leads ALTER COLUMN custom_fields TYPE json USING custom_fields::json")
    op.execute("ALTER TABLE crm_leads ALTER COLUMN address TYPE json USING address::json")
    op.execute(
        "ALTER TABLE crm_companies ALTER COLUMN custom_fields TYPE json USING custom_fields::json"
    )
    op.execute("ALTER TABLE crm_companies ALTER COLUMN address TYPE json USING address::json")
