"""customer fast-book: consent log + order ratings

Revision ID: cf0fastbook1a2b
Revises: nt2notifprefs1a2b (integration chain)
"""

import sqlalchemy as sa
from alembic import op

revision = "cf0fastbook1a2b"
down_revision = "nt2notifprefs1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("wording", sa.String(500), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_customer_consents_customer_id", "customer_consents", ["customer_id"])
    op.create_index("ix_customer_consents_kind", "customer_consents", ["kind"])
    op.create_table(
        "order_ratings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_order_ratings_order_id", "order_ratings", ["order_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_order_ratings_order_id", table_name="order_ratings")
    op.drop_table("order_ratings")
    op.drop_index("ix_customer_consents_kind", table_name="customer_consents")
    op.drop_index("ix_customer_consents_customer_id", table_name="customer_consents")
    op.drop_table("customer_consents")
