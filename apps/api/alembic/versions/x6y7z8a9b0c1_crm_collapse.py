"""P2 — CRM/ops pointers, task/note collapse, merchant profile columns."""

from alembic import op
import sqlalchemy as sa

revision = "x6y7z8a9b0c1"
down_revision = "w5x6y7z8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("crm_invoices", sa.Column("operational_invoice_id", sa.String(length=36), nullable=True))
    op.create_index("ix_crm_invoices_operational_invoice_id", "crm_invoices", ["operational_invoice_id"])
    op.create_foreign_key(
        "fk_crm_invoices_operational_invoice_id",
        "crm_invoices",
        "invoices",
        ["operational_invoice_id"],
        ["id"],
    )

    op.add_column("merchant_contracts", sa.Column("crm_contract_id", sa.String(length=36), nullable=True))
    op.create_index("ix_merchant_contracts_crm_contract_id", "merchant_contracts", ["crm_contract_id"])

    op.add_column("leads", sa.Column("crm_lead_id", sa.String(length=36), nullable=True))
    op.create_index("ix_leads_crm_lead_id", "leads", ["crm_lead_id"])
    op.execute(
        sa.text(
            """
            UPDATE leads SET crm_lead_id = NULL
            WHERE crm_lead_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM crm_leads c WHERE c.id = leads.crm_lead_id)
            """
        )
    )
    op.create_foreign_key(
        "fk_leads_crm_lead_id",
        "leads",
        "crm_leads",
        ["crm_lead_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute(
        sa.text(
            """
            INSERT INTO crm_sales_tasks (
                id, title, task_type, status, priority, entity_type, entity_id,
                assigned_to, due_at, is_recurring, created_by, created_at, updated_at
            )
            SELECT
                t.id,
                t.title,
                'todo',
                t.status,
                'medium',
                CASE WHEN t.lead_id IS NOT NULL THEN 'lead'
                     WHEN t.merchant_id IS NOT NULL THEN 'merchant'
                     ELSE NULL END,
                COALESCE(t.lead_id, t.merchant_id),
                t.assigned_to,
                t.due_at,
                false,
                t.assigned_to,
                t.created_at,
                t.created_at
            FROM crm_tasks t
            WHERE NOT EXISTS (SELECT 1 FROM crm_sales_tasks s WHERE s.id = t.id)
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO crm_activities (
                id, entity_type, entity_id, activity_type, body, actor_id, occurred_at, created_at, metadata_json
            )
            SELECT
                n.id,
                n.entity_type,
                n.entity_id,
                'note',
                n.body,
                n.author_id,
                n.created_at,
                n.created_at,
                '{}'::json
            FROM crm_notes n
            WHERE NOT EXISTS (SELECT 1 FROM crm_activities a WHERE a.id = n.id)
            """
        )
    )
    op.drop_index(op.f("ix_crm_tasks_lead_id"), table_name="crm_tasks")
    op.drop_index(op.f("ix_crm_tasks_merchant_id"), table_name="crm_tasks")
    op.drop_index(op.f("ix_crm_tasks_status"), table_name="crm_tasks")
    op.drop_table("crm_tasks")
    op.drop_index(op.f("ix_crm_notes_entity_id"), table_name="crm_notes")
    op.drop_table("crm_notes")

    op.add_column("merchants", sa.Column("website", sa.String(length=512), nullable=True))
    op.add_column("merchants", sa.Column("industry", sa.String(length=128), nullable=True))
    op.add_column(
        "merchants",
        sa.Column("stripe_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute(
        sa.text(
            """
            UPDATE merchants SET
                website = COALESCE(website, NULLIF(profile->>'website', '')),
                industry = COALESCE(industry, NULLIF(profile->>'industry', '')),
                stripe_enabled = CASE
                    WHEN lower(coalesce(profile->>'stripe_enabled', '')) IN ('true', 't', '1') THEN true
                    ELSE stripe_enabled
                END
            WHERE profile IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE merchants
            SET profile = (
                profile::jsonb
                - 'website' - 'industry' - 'stripe_enabled' - 'stripe_checkout'
                - 'hst_number' - 'business_number' - 'legal_name' - 'tax_number'
            )::json
            WHERE profile IS NOT NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE bookings b
            SET state = o.state
            FROM orders o
            WHERE b.order_id = o.id AND b.state IS DISTINCT FROM o.state
            """
        )
    )


def downgrade() -> None:
    op.drop_column("merchants", "stripe_enabled")
    op.drop_column("merchants", "industry")
    op.drop_column("merchants", "website")
    op.create_table(
        "crm_notes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("author_id", sa.String(length=36), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_crm_notes_entity_id", "crm_notes", ["entity_id"])
    op.create_table(
        "crm_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column("merchant_id", sa.String(length=36), nullable=True),
        sa.Column("assigned_to", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_crm_tasks_lead_id", "crm_tasks", ["lead_id"])
    op.create_index("ix_crm_tasks_merchant_id", "crm_tasks", ["merchant_id"])
    op.create_index("ix_crm_tasks_status", "crm_tasks", ["status"])
    op.drop_constraint("fk_leads_crm_lead_id", "leads", type_="foreignkey")
    op.drop_index("ix_leads_crm_lead_id", table_name="leads")
    op.drop_column("leads", "crm_lead_id")
    op.drop_index("ix_merchant_contracts_crm_contract_id", table_name="merchant_contracts")
    op.drop_column("merchant_contracts", "crm_contract_id")
    op.drop_constraint("fk_crm_invoices_operational_invoice_id", "crm_invoices", type_="foreignkey")
    op.drop_index("ix_crm_invoices_operational_invoice_id", table_name="crm_invoices")
    op.drop_column("crm_invoices", "operational_invoice_id")
