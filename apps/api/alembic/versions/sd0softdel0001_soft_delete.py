"""Soft delete: deleted_at/by/reason/batch on admin-managed tables + deleted_batches.

Revision ID: sd0softdel0001
Revises: f0r3n51c0001
"""

import sqlalchemy as sa
from alembic import op

revision = "sd0softdel0001"
down_revision = "f0r3n51c0001"
branch_labels = None
depends_on = None

TABLES = (
    "booking_drafts", "crm_leads", "crm_companies", "crm_contacts", "crm_deals", "crm_quotations",
    "orders", "packages", "customers", "customer_addresses", "customer_notes",
    "merchants", "merchant_recipients", "merchant_booking_templates", "standing_orders",
    "drivers", "vehicles", "claims", "support_tickets", "promotions", "pricing_zones", "pricing_tariffs",
    "route_center_templates", "dispatch_routes", "dispatch_plans", "blog_posts",
)


def upgrade() -> None:
    for t in TABLES:
        op.add_column(t, sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(t, sa.Column("deleted_by", sa.String(64), nullable=True))
        op.add_column(t, sa.Column("delete_reason", sa.String(500), nullable=True))
        op.add_column(t, sa.Column("delete_batch_id", sa.String(36), nullable=True))
        op.create_index(f"ix_{t}_deleted_at", t, ["deleted_at"])
        op.create_index(f"ix_{t}_delete_batch_id", t, ["delete_batch_id"])
    op.create_table(
        "deleted_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity", sa.String(48), nullable=False),
        sa.Column("root_id", sa.String(36), nullable=False),
        sa.Column("label", sa.String(255), nullable=False, server_default=""),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("deleted_by", sa.String(64), nullable=True),
        sa.Column("deleted_by_email", sa.String(320), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("children", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("side_effects", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("state", sa.String(16), nullable=False, server_default="deleted"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(64), nullable=True),
        sa.Column("outcome", sa.JSON(), nullable=False, server_default="{}"),
    )
    for c in ("entity", "root_id", "deleted_at", "purge_after", "state"):
        op.create_index(f"ix_deleted_batches_{c}", "deleted_batches", [c])


def downgrade() -> None:
    op.drop_table("deleted_batches")
    for t in TABLES:
        op.drop_index(f"ix_{t}_delete_batch_id", table_name=t)
        op.drop_index(f"ix_{t}_deleted_at", table_name=t)
        for c in ("delete_batch_id", "delete_reason", "deleted_by", "deleted_at"):
            op.drop_column(t, c)
