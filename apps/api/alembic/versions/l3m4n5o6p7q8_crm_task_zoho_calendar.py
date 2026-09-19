"""Add Zoho Calendar linkage to CRM sales tasks."""

from alembic import op
import sqlalchemy as sa

revision = "l3m4n5o6p7q8"
down_revision = "k2l3m4n5o6p7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("crm_sales_tasks", sa.Column("zoho_event_uid", sa.String(length=128), nullable=True))
    op.create_index("ix_crm_sales_tasks_zoho_event_uid", "crm_sales_tasks", ["zoho_event_uid"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_crm_sales_tasks_zoho_event_uid", table_name="crm_sales_tasks")
    op.drop_column("crm_sales_tasks", "zoho_event_uid")
